"""Shared initial plans, condition runs and disclosed offline software fixtures."""

from copy import deepcopy
import hashlib
from importlib.resources import files
import json
import logging
import os
from pathlib import Path
import shutil
from time import monotonic

from .client import BudgetError, FakeClient, _strict_json
from .contracts import (CONDITIONS, CONTRACT_VERSION, OUTPUT_MODES, json_hash,
                        assert_dialogue_only_revision, shared_generation_sha256)
from .evaluation import build_assignments
from .planner import MAX_OUTPUT_TOKENS, PlanningError, get_planning_prompt_hashes, make_plan_with_trace
from .renderer import render_plan
from .reviewer import review_and_revise
from .validation import validate_plan, validate_scene

def resolve_render_dependencies(*, project_root=".", font_path=None, config_path="configs/render.json"):
    """Verify local rendering dependencies before planning can incur any cost."""
    from .renderer import _load_font

    missing = [tool for tool in ("ffmpeg", "ffprobe") if shutil.which(tool) is None]
    if missing:
        raise ValueError("Missing local rendering dependencies on PATH: " + ", ".join(missing))
    root = Path(project_root).resolve()
    config_file = root / config_path if config_path is not None else None
    config = read_json(config_file) if config_file is not None and config_file.exists() else {}
    if not isinstance(config, dict):
        raise ValueError("Render configuration must be a JSON object")
    explicit = font_path or os.environ.get("MOODCUT_FONT") or config.get("font_path")
    if explicit is not None and not isinstance(explicit, str):
        raise ValueError("font_path must be a path string or null")
    windows = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts/msyh.ttc"
    candidates = [explicit] if explicit else [
        str(windows), "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/System/Library/Fonts/PingFang.ttc"]
    for candidate in candidates:
        path = Path(candidate)
        path = path if path.is_absolute() else root / path
        if path.is_file():
            _load_font(str(path))
            return str(path.resolve())
    raise ValueError("No usable local font; provide --font, MOODCUT_FONT or configs/render.json")


def read_json(path):
    return _strict_json(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, data):
    """Create an artifact exclusively, never replacing an existing result."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)


def _mock_plan(scene, manifest):
    """Deterministic test plan; not a claim of narrative quality."""
    beats = scene["beats"]
    count = min(6, scene["max_shots"], len(beats))
    chunks = [beats[i * len(beats) // count:(i + 1) * len(beats) // count] for i in range(count)]
    duration = max(60, scene["min_duration_s"])
    selected = [a for a in manifest["assets"] if a["asset_id"] in scene["asset_ids"]][:2]
    shots = [{"shot_id": f"s{i+1}", "beat_ids": [b["id"] for b in chunk],
              "duration_s": duration / count,
              "visuals": [{"asset_id": a["asset_id"], "crop": a["allowed_crops"][0]} for a in selected],
              "dialogue": [], "narration": " ".join(b["description"] for b in chunk)}
             for i, chunk in enumerate(chunks)]
    return {"schema_version": "1.0", "scene_id": scene["scene_id"], "tone": scene["tone"], "shots": shots}


def make_mock_client(scene, manifest, *, include_planning=False, initial_plan=None, conditions=CONDITIONS):
    """Build labeled test responses; both review conditions use equal edits."""
    plan = deepcopy(initial_plan) if initial_plan is not None else _mock_plan(scene, manifest)
    responses = []
    if include_planning:
        responses.extend([
            {"scene_id": scene["scene_id"], "tone": scene["tone"],
             "beat_order": [b["id"] for b in scene["beats"]], "approach": "Offline software fixture"},
            {"scene_id": scene["scene_id"], "segments": [
                {"beat_ids": [b["id"] for b in scene["beats"]], "description": "Offline fixture segment"}]},
            deepcopy(plan)])
    for condition in conditions:
        if condition == "baseline":
            continue
        shot = plan["shots"][0]
        responses.extend([
            {"schema_version": "1.0", "scene_id": scene["scene_id"], "mode": condition,
             "issues": [{"issue_id": "fixture-1", "shot_id": shot["shot_id"],
                         "dimension": "renderability", "severity": "minor",
                         "evidence": "Synthetic feedback to exercise the pipeline.",
                         "suggestion": "Append a visible offline-revision marker to the caption."}]},
            {"schema_version": "1.0", "scene_id": scene["scene_id"], "edits": [
                {"issue_id": "fixture-1", "shot_id": shot["shot_id"],
                 "set": {"narration": shot["narration"] + " [offline revision fixture]"}}]},
            {"scene_id": scene["scene_id"], "resolved_issue_ids": ["fixture-1"],
             "unresolved_issue_ids": [], "new_concerns": []}])
    return FakeClient(responses)


def usage_totals(records, *, mock=False):
    def total(field):
        return None if any(r.get(field) is None for r in records) else sum(r[field] for r in records)
    return {"calls": len(records), "real_http_calls": 0 if mock else len(records),
            "input_tokens": total("input_tokens"), "output_tokens": total("output_tokens"),
            "estimated_cost_usd": 0.0 if mock else total("estimated_cost_usd"),
            "provider_cost_usd": 0.0 if mock else total("provider_cost_usd")}


def _model_settings(client):
    if client is None or isinstance(client, FakeClient):
        return {"model_id": "fake/offline", "temperature": 0, "fixture_version": "1"}
    return {"model_id": getattr(client, "model", type(client).__name__),
            "temperature": getattr(client, "temperature", None)}


def _review_hashes():
    return {name: hashlib.sha256(files("moodcut").joinpath("prompts", f"review_{name}.txt").read_bytes()).hexdigest()
            for name in ("generic", "moodcut", "revise", "verify")}


def _assignment(scene, replicate, condition):
    rows = build_assignments([scene], replicates=replicate, tones=[scene["tone"]], conditions=[condition])
    return next(r for r in rows if r["replicate"] == replicate)


def _mode_options(output_mode, generation_settings, template_sha256):
    """Never infer generated mode or downgrade an unsupported dependency."""
    if not isinstance(output_mode, str) or output_mode not in OUTPUT_MODES:
        raise ValueError("output_mode must be animatic or generated")
    if output_mode == "animatic":
        if generation_settings is not None or template_sha256 is not None:
            raise ValueError("Generation settings/template require explicit generated mode")
        return {}
    if not isinstance(generation_settings, dict) or not isinstance(template_sha256, str):
        raise ValueError("Generated mode requires generation_settings and template_sha256")
    return {"output_mode": "generated"}


def run_condition(scene: dict, initial_plan: dict, manifest: dict, client, *,
                  condition: str, out_dir: str, project_root: str, font_path: str | None,
                  render=True, replicate=1, source_kind="development", output_mode="animatic",
                  generation_settings=None, template_sha256=None,
                  expected_initial_plan_sha256=None, expected_shared_generation_sha256=None) -> dict:
    """Save each condition; generated mode only prepares scripts, never video jobs.

    Its two expected identities bind every condition to the block's frozen input.
    Planning/review dependencies must implement the explicit generated interface.
    """
    if condition not in CONDITIONS or type(replicate) is not int or replicate < 1:
        raise ValueError("Invalid condition or replicate")
    mode_options = _mode_options(output_mode, generation_settings, template_sha256)
    generated = output_mode == "generated"
    if not generated and (expected_initial_plan_sha256 is not None or expected_shared_generation_sha256 is not None):
        raise ValueError("Expected generation identities require explicit generated mode")
    if generated:
        scene, initial_plan, manifest, generation_settings = deepcopy(
            (scene, initial_plan, manifest, generation_settings))
    output = Path(out_dir).resolve()
    output.mkdir(parents=True, exist_ok=False)
    mock = isinstance(client, FakeClient)
    start = monotonic()
    before = len(getattr(client, "calls", []))
    record = {**_assignment(scene, replicate, condition), "schema_version": "1.0",
              "model_id": _model_settings(client)["model_id"],
              "source_kind": "synthetic" if mock else source_kind, "mock": mock,
              "provenance": deepcopy(scene.get("provenance", {})),
              "initial_plan_sha256": json_hash(initial_plan) if initial_plan is not None and not generated else None,
              "final_plan_sha256": None, "prompt_hashes": _review_hashes(),
              "review_status": "not_applicable" if condition == "baseline" else "not_started",
              "validation_status": "not_started", "render_status": "not_started",
              "run_status": "failed", "failure_kind": None, "video_path": None, "errors": []}
    if generated:
        record.update(schema_version=CONTRACT_VERSION, output_mode="generated",
                      shared_generation_sha256=None, video_model_id=generation_settings.get("model"),
                      generation_status="not_started", generation_jobs=[],
                      comparison_status="not_checked", comparison_errors=[],
                      review_calls=0, generation_posts=0, video_get_calls=0)
        record["prompt_hashes"]["video_template"] = template_sha256
    try:
        write_json(output / "scene.json", scene)
        write_json(output / "assets.json", manifest)
        write_json(output / "initial.json", initial_plan)
        if generated:
            write_json(output / "generation_settings.json", generation_settings)
            if initial_plan is not None:
                record["initial_plan_sha256"] = json_hash(initial_plan)
        errors = validate_plan(scene, initial_plan, manifest, project_root=project_root, **mode_options)
        if errors:
            record["validation_status"] = "failed"
            if generated:
                record["failure_kind"] = "validation"
            record["errors"].extend(errors)
            return record
        if generated:
            record["validation_status"] = "passed"
            record["failure_kind"] = "shared_inputs"
            shared = shared_generation_sha256(scene, initial_plan, manifest, generation_settings,
                                               template_sha256=template_sha256)
            record["shared_generation_sha256"] = shared
            if (record["initial_plan_sha256"] != expected_initial_plan_sha256
                    or shared != expected_shared_generation_sha256):
                raise ValueError("Generated initial/shared identity does not match frozen block inputs")
            record["failure_kind"] = None
        final = deepcopy(initial_plan)
        if condition != "baseline":
            logger = logging.getLogger("moodcut.review.trace")
            old_level = logger.level
            handler = logging.FileHandler(output / "review_trace.jsonl", mode="x", encoding="utf-8")
            handler.setFormatter(logging.Formatter("%(message)s"))
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
            try:
                reviewed = review_and_revise(deepcopy(scene), deepcopy(initial_plan), deepcopy(manifest),
                                             client, mode=condition, project_root=project_root, **mode_options)
            finally:
                logger.removeHandler(handler)
                handler.close()
                logger.setLevel(old_level)
            write_json(output / "review.json", reviewed)
            final = reviewed["plan"]
            record["review_status"] = reviewed["status"]
            record["errors"].extend(reviewed["errors"])
            if any("BudgetError:" in error for error in reviewed["errors"]):
                record["failure_kind"] = "budget"
        if generated:
            # Persist the actual candidate for auditing even when it is rejected.
            write_json(output / "final.json", final)
            record["final_plan_sha256"] = json_hash(final)
            record["final_plan_path"] = str(output / "final.json")
        errors = validate_plan(scene, final, manifest, project_root=project_root, **mode_options)
        record["validation_status"] = "failed" if errors else "passed"
        record["errors"].extend(errors)
        if errors:
            if generated and record["failure_kind"] is None:
                record["failure_kind"] = "validation"
            return record
        if generated:
            if record["failure_kind"] is None:
                record["failure_kind"] = "shared_inputs"
            assert_dialogue_only_revision(initial_plan, final)
            actual_shared = shared_generation_sha256(scene, final, manifest, generation_settings,
                                                      template_sha256=template_sha256)
            record["shared_generation_sha256"] = actual_shared
            if actual_shared != expected_shared_generation_sha256:
                raise ValueError("Generated final shared identity does not match frozen block inputs")
            if condition == "baseline" or record["review_status"] == "unchanged":
                if record["final_plan_sha256"] != expected_initial_plan_sha256:
                    raise ValueError("Baseline/unchanged must retain the exact initial plan")
            if record["failure_kind"] == "shared_inputs":
                record["failure_kind"] = None
            if condition != "baseline" and record["review_status"] not in ("applied", "unchanged"):
                record["failure_kind"] = record["failure_kind"] or "review"
                raise ValueError("Generated source review must be applied or unchanged; failed fallback is invalid")
            record.update(run_status="prepared", failure_kind=None)
            return record
        write_json(output / "final.json", final)
        record["final_plan_sha256"] = json_hash(final)
        record["final_plan_path"] = str(output / "final.json")
        if render:
            rendered = render_plan(final, manifest, project_root=project_root,
                                   out_dir=str(output / "render"), font_path=font_path)
            write_json(output / "render.json", rendered)
            record["render_status"] = rendered["status"]
            record["video_path"] = rendered["video_path"]
            record["errors"].extend(rendered["errors"])
        else:
            record["render_status"] = "skipped"
        if (record["review_status"] not in ("review_failed", "rejected")
                and record["render_status"] in ("rendered", "skipped")):
            record["run_status"] = "completed"
        return record
    except Exception as exc:
        record["errors"].append(f"{type(exc).__name__}: {exc}")
        if isinstance(exc, BudgetError):
            record["failure_kind"] = "budget"
        elif record["failure_kind"] is None:
            record["failure_kind"] = "execution"
        return record
    finally:
        records = deepcopy(getattr(client, "calls", [])[before:])
        record.update(usage_totals(records, mock=mock))
        if generated:
            record["review_calls"] = len(records)
            if record["run_status"] == "failed":
                record["comparison_status"] = "ineligible"
                record["comparison_errors"] = list(record["errors"])
        record["call_records"] = records
        record["elapsed_s"] = monotonic() - start
        write_json(output / "run.json", record)


def run_experiment(scene, manifest, client=None, *, out_dir, project_root=".",
                   font_path=None, render=True, replicate=1, cache_dir=None, source_kind="development",
                   output_mode="animatic", generation_settings=None, template_sha256=None):
    """Plan once; generated mode freezes shared identity and prepares script records.

    No generated request compilation, video transport or animatic rendering occurs
    in generated mode. Its planner/reviewer integrations remain owned by P2/P3.
    """
    if type(replicate) is not int or replicate < 1:
        raise ValueError("replicate must be a positive integer")
    if source_kind not in ("synthetic", "development", "formal"):
        raise ValueError("Invalid source_kind")
    mode_options = _mode_options(output_mode, generation_settings, template_sha256)
    generated = output_mode == "generated"
    if generated:
        scene, manifest, generation_settings = deepcopy((scene, manifest, generation_settings))
    root = Path(project_root).resolve()
    errors = validate_scene(scene, manifest, project_root=root, **mode_options)
    if errors:
        raise ValueError("; ".join(errors))
    output = Path(out_dir).resolve()
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "scene.json", scene)
    write_json(output / "assets.json", manifest)
    if generated:
        write_json(output / "generation_settings.json", generation_settings)
    settings = _model_settings(client)
    identity = {"schema_version": "1.0", "scene": scene, "manifest": manifest,
                "replicate": replicate, "settings": settings,
                "planning_prompt_hashes": get_planning_prompt_hashes(),
                "planning_token_limits": MAX_OUTPUT_TOKENS,
                "planner_code_sha256": hashlib.sha256(files("moodcut").joinpath("planner.py").read_bytes()).hexdigest()}
    if generated:
        identity.update(schema_version=CONTRACT_VERSION, output_mode="generated",
                        generation_settings=deepcopy(generation_settings), template_sha256=template_sha256)
    cache_key = json_hash(identity)
    cache = Path(cache_dir).resolve() / f"{cache_key}.json" if cache_dir else None
    initial = None
    shared = None
    planning = {"status": "not_started", "cache_hit": False, "cache_key": cache_key,
                "prompt_hashes": identity["planning_prompt_hashes"], "raw_responses": {}, "errors": []}
    lock = None
    own_lock = False
    before = len(getattr(client, "calls", [])) if client is not None else 0
    began = monotonic()

    def load_cached_plan():
        saved = read_json(cache)
        plan = saved["plan"]
        if (saved["identity"] != identity or saved["plan_sha256"] != json_hash(plan)
                or validate_plan(scene, plan, manifest, project_root=root, **mode_options)):
            raise ValueError("Cached plan identity/hash/validation mismatch; cache preserved")
        if generated and saved.get("shared_generation_sha256") != shared_generation_sha256(
                scene, plan, manifest, generation_settings, template_sha256=template_sha256):
            raise ValueError("Cached shared generation identity mismatch; cache preserved")
        planning.update(status="completed", cache_hit=True, raw_responses=saved["raw_responses"])
        return plan

    try:
        if cache is not None and cache.exists():
            initial = load_cached_plan()
        elif cache is not None:
            cache.parent.mkdir(parents=True, exist_ok=True)
            lock = cache.with_suffix(".lock")
            with lock.open("x", encoding="utf-8") as stream:
                stream.write(str(output))
            own_lock = True
            # A different process may have finished after the first exists() check.
            # Recheck under our exclusive lock before making a potentially paid call.
            if cache.exists():
                initial = load_cached_plan()
        if client is None:
            client = (FakeClient([]) if generated else make_mock_client(
                scene, manifest, include_planning=initial is None, initial_plan=initial))
        before = len(getattr(client, "calls", []))
        if initial is None:
            traced = make_plan_with_trace(deepcopy(scene), deepcopy(manifest), client,
                                          project_root=root, **mode_options)
            planning["raw_responses"] = deepcopy(traced["raw_responses"])
            initial = deepcopy(traced["plan"])
            errors = validate_plan(scene, initial, manifest, project_root=root, **mode_options)
            if errors:
                raise ValueError("; ".join(errors))
            if generated:
                shared = shared_generation_sha256(scene, initial, manifest, generation_settings,
                                                   template_sha256=template_sha256)
            planning.update(status="completed", raw_responses=traced["raw_responses"])
            if cache is not None:
                saved = {"identity": identity, "plan": initial,
                         "plan_sha256": json_hash(initial), "raw_responses": traced["raw_responses"]}
                if generated:
                    saved["shared_generation_sha256"] = shared
                write_json(cache, saved)
        if generated:
            shared = shared_generation_sha256(scene, initial, manifest, generation_settings,
                                               template_sha256=template_sha256)
            write_json(output / "initial.json", initial)
    except Exception as exc:
        planning.update(status="failed", errors=[f"{type(exc).__name__}: {exc}"])
        initial = None
        shared = None
        if isinstance(exc, PlanningError):
            planning["raw_responses"] = exc.raw_responses
    finally:
        if own_lock:
            lock.unlink()
        mock = client is None or isinstance(client, FakeClient)
        records = deepcopy(getattr(client, "calls", [])[before:]) if client is not None else []
        planning.update(usage_totals(records, mock=mock))
        planning["call_records"] = records
        planning["elapsed_s"] = monotonic() - began
        write_json(output / "planning.json", planning)
    if client is None:
        client = FakeClient([])
    condition_options = {}
    if generated:
        condition_options = dict(output_mode="generated", generation_settings=generation_settings,
                                 template_sha256=template_sha256,
                                 expected_initial_plan_sha256=json_hash(initial) if initial is not None else None,
                                 expected_shared_generation_sha256=shared)
    runs = [run_condition(deepcopy(scene), deepcopy(initial), deepcopy(manifest), client, condition=condition,
                          out_dir=str(output / condition), project_root=str(root), font_path=font_path,
                          render=render, replicate=replicate, source_kind=source_kind, **condition_options)
            for condition in CONDITIONS]
    block = {"block_id": runs[0]["block_id"], "scene_id": scene["scene_id"], "tone": scene["tone"],
             "replicate": replicate, "initial_plan_sha256": json_hash(initial) if initial is not None else None,
             "source_kind": "synthetic" if mock else source_kind, "mock": mock,
             "model_id": settings["model_id"], "planning": planning, "runs": runs,
             "status": ("prepared" if generated else "completed") if planning["status"] == "completed"
             and all(r["run_status"] == ("prepared" if generated else "completed") for r in runs) else "failed"}
    if generated:
        block.update(schema_version=CONTRACT_VERSION, output_mode="generated",
                     shared_generation_sha256=shared, generation_settings=generation_settings,
                     template_sha256=template_sha256)
    write_json(output / "block.json", block)
    return block


def _require_generated(condition, message):
    if not condition:
        raise ValueError("Generated preparation: " + message)


def _load_generated_block(path, project_root):
    """Recompute saved script identities; never follow final_plan_path pointers."""
    path = Path(path).resolve(strict=True)
    path = path / "block.json" if path.is_dir() else path
    block = read_json(path)
    need = _require_generated
    need(isinstance(block, dict) and block.get("schema_version") == CONTRACT_VERSION
         and block.get("output_mode") == "generated" and block.get("status") == "prepared",
         "source must be a prepared 1.1/generated script block")
    folder = path.parent
    scene, manifest, initial, settings = [read_json(folder / name) for name in
        ("scene.json", "assets.json", "initial.json", "generation_settings.json")]
    template = block.get("template_sha256")
    errors = validate_plan(scene, initial, manifest, project_root=project_root, output_mode="generated")
    need(not errors, "; ".join(errors))
    shared = shared_generation_sha256(scene, initial, manifest, settings, template_sha256=template)
    need(block.get("shared_generation_sha256") == shared
         and block.get("initial_plan_sha256") == json_hash(initial)
         and json_hash(block.get("generation_settings")) == json_hash(settings), "block shared/initial/settings identity mismatch")
    need(block.get("scene_id") == scene["scene_id"] and block.get("tone") == scene["tone"], "block scene/tone mismatch")
    planning = read_json(folder / "planning.json")
    need(isinstance(planning, dict) and planning.get("status") == "completed"
         and json_hash(planning) == json_hash(block.get("planning")), "source planning record mismatch")
    rows = block.get("runs")
    need(isinstance(rows, list) and len(rows) == 3 and all(isinstance(r, dict) for r in rows)
         and [r.get("condition") for r in rows] == list(CONDITIONS), "exactly three ordered conditions are required")
    plans, run_ids = {}, set()
    for row in rows:
        condition = row["condition"]
        directory = folder / condition
        need(json_hash(read_json(directory / "run.json")) == json_hash(row), "embedded/disk run mismatch: " + condition)
        need(row.get("schema_version") == CONTRACT_VERSION and row.get("output_mode") == "generated"
             and row.get("run_status") == "prepared" and row.get("validation_status") == "passed"
             and row.get("comparison_status") == "not_checked", "invalid script source state: " + condition)
        for field in ("block_id", "scene_id", "tone", "replicate", "initial_plan_sha256", "shared_generation_sha256",
                      "model_id", "source_kind", "mock"):
            need(field in row and field in block and json_hash(row[field]) == json_hash(block[field]),
                 "run/block mismatch: " + field)
        run_id = row.get("run_id")
        need(isinstance(run_id, str) and bool(run_id.strip()) and run_id not in run_ids, "run IDs must be nonempty and unique")
        run_ids.add(run_id)
        need(row.get("video_model_id") == settings["model"] and isinstance(row.get("prompt_hashes"), dict)
             and row["prompt_hashes"].get("video_template") == template, "run model/template mismatch")
        need(row.get("generation_status") == row.get("render_status") == "not_started"
             and row.get("generation_jobs") == [] and row.get("video_path") is None
             and all(type(row.get(k)) is int and row[k] == 0 for k in ("generation_posts", "video_get_calls")),
             "source is not an unsubmitted script")
        for name, expected in (("scene.json", scene), ("assets.json", manifest),
                               ("initial.json", initial), ("generation_settings.json", settings)):
            need(json_hash(read_json(directory / name)) == json_hash(expected), "condition input mismatch: " + name)
        final = read_json(directory / "final.json")
        errors = validate_plan(scene, final, manifest, project_root=project_root, output_mode="generated")
        need(not errors, "; ".join(errors))
        assert_dialogue_only_revision(initial, final)
        need(row.get("final_plan_sha256") == json_hash(final), "final plan hash mismatch")
        need(shared_generation_sha256(scene, final, manifest, settings, template_sha256=template) == shared,
             "condition shared identity mismatch")
        status = row.get("review_status")
        need(status == "not_applicable" if condition == "baseline" else status in ("applied", "unchanged"),
             "invalid review source: " + condition)
        if condition == "baseline" or status == "unchanged":
            need(json_hash(final) == json_hash(initial), "baseline/unchanged must retain the initial plan")
        if condition != "baseline":
            reviewed = read_json(directory / "review.json")
            need(isinstance(reviewed, dict) and reviewed.get("status") == status
                 and json_hash(reviewed.get("plan")) == json_hash(final), "saved review/final script mismatch")
        plans[condition] = final
    return path, block, dict(scene=scene, initial=initial, plans=plans, manifest=manifest,
                            settings=settings, template_sha256=template)


def _validate_generated_bundle(bundle, source, block, pricing):
    """Check the compiler protocol and identities without recreating its prompts."""
    from .contracts import _json_copy
    from .video_client import _money, estimate_video_cost
    need = _require_generated
    bundle = _json_copy(bundle)
    need(isinstance(bundle, dict) and bundle.get("schema_version") == CONTRACT_VERSION
         and bundle.get("output_mode") == "generated" and bundle.get("kind") == "generated_three_condition_bundle",
         "compiler must return the generated three-condition contract")
    for name in ("initial_plan_sha256", "shared_generation_sha256"):
        need(bundle.get(name) == block[name], "compiler identity mismatch: " + name)
    settings, initial = source["settings"], source["initial"]
    need(json_hash(bundle.get("settings")) == json_hash(settings), "compiler settings mismatch")
    conditions = bundle.get("conditions")
    need(isinstance(conditions, list) and len(conditions) == 3 and all(isinstance(c, dict) for c in conditions)
         and [c.get("condition") for c in conditions] == list(CONDITIONS), "compiler conditions mismatch")
    shot_ids = [s["shot_id"] for s in initial["shots"]]
    for condition in conditions:
        need(condition.get("final_plan_sha256") == json_hash(source["plans"][condition["condition"]]),
             "compiler final plan identity mismatch")
        jobs = condition.get("jobs")
        need(isinstance(jobs, list) and all(isinstance(j, dict) for j in jobs)
             and [j.get("shot_id") for j in jobs] == shot_ids, "compiler must preserve all original shots and their order")
        for index, job in enumerate(jobs):
            request = job.get("request")
            need(isinstance(request, dict) and job.get("request_sha256") == json_hash(request), "request hash mismatch")
            need(all(request.get(k) == settings[k] for k in ("model", "resolution", "aspect_ratio"))
                 and request.get("generate_audio") is True, "request generation settings mismatch")
            need(type(request.get("seed")) is int and request["seed"] == settings["seed"] + index,
                 "request seed must use the original shot index")
            need(type(request.get("duration")) is int and request["duration"] == initial["shots"][index]["duration_s"],
                 "request duration mismatch")
            refs = request.get("input_references")
            need(isinstance(refs, list) and bool(refs) and "frame_images" not in request,
                 "request requires character references, not card frames")
            need(isinstance(request.get("prompt"), str) and bool(request["prompt"].strip()), "request prompt is empty")
            quote = job.get("quoted_cost_usd")
            need(isinstance(quote, str) and _money(quote) == estimate_video_cost(pricing, request),
                 "compiler quote must match the configured local price")
    return bundle


def prepare_generated_run(source_block, *, out_dir, project_root=".", shot_id=None, pricing_config):
    """Prepare requests from saved scripts only; no client, key, lookup or POST.

    P4's pure compiler is an explicit dependency, never replaced by the old pair
    compiler. Compile full plans first, then select jobs without reindexing seeds.
    """
    from decimal import Decimal
    from . import video_generation
    output = Path(out_dir).resolve()
    if output.exists() or output.is_symlink():
        raise FileExistsError("Output already exists; choose a new path: " + str(output))
    root = Path(project_root).resolve()
    path, block, source = _load_generated_block(source_block, root)
    shot_ids = [shot["shot_id"] for shot in source["initial"]["shots"]]
    _require_generated(shot_id is None or isinstance(shot_id, str) and shot_id in shot_ids, "unknown shot_id")
    selected = shot_ids if shot_id is None else [shot_id]
    compiler = getattr(video_generation, "build_generated_video_bundle", None)
    if not callable(compiler):
        raise RuntimeError("Missing generated request compiler (#24): build_generated_video_bundle is not implemented; no fallback or submission")
    pricing = read_json(pricing_config)
    _require_generated(isinstance(pricing, dict), "pricing config must be an object")
    compiler_inputs = deepcopy(source)
    before = json_hash(compiler_inputs)
    bundle = compiler(compiler_inputs["scene"], compiler_inputs["initial"], compiler_inputs["plans"],
                      compiler_inputs["manifest"], compiler_inputs["settings"], project_root=root,
                      template_sha256=compiler_inputs["template_sha256"], pricing_config=deepcopy(pricing))
    _require_generated(json_hash(compiler_inputs) == before, "compiler mutated its shared inputs")
    bundle = _validate_generated_bundle(bundle, source, block, pricing)
    # A local editor/compiler must not silently replace inputs during preparation.
    _, current_block, current_source = _load_generated_block(path, root)
    _require_generated(json_hash(current_block) == json_hash(block) and json_hash(current_source) == json_hash(source),
                       "saved source changed while compiling requests")
    total = Decimal(0)
    for condition in bundle["conditions"]:
        condition["jobs"] = [dict(job, shot_index=index) for index, job in enumerate(condition["jobs"])
                             if job["shot_id"] in selected]
        total += sum((Decimal(job["quoted_cost_usd"]) for job in condition["jobs"]), Decimal(0))
    bundle.update(selected_shot_ids=selected, full_plan_shot_ids=shot_ids)
    prepared = {"schema_version": CONTRACT_VERSION, "output_mode": "generated",
                "kind": "generated_request_preparation", "preparation_stage": "requests", "status": "prepared_offline",
                "source_block_path": str(path), "source_block_sha256": json_hash(block),
                "initial_plan_sha256": block["initial_plan_sha256"],
                "shared_generation_sha256": block["shared_generation_sha256"],
                "selected_shot_ids": selected, "quoted_cost_usd": str(total), "pricing_config_sha256": json_hash(pricing),
                "quote_scope": "selected jobs before any future request reuse; not actual spending or live pricing",
                "calls": 0, "real_http_calls": 0, "generation_posts": 0, "video_get_calls": 0,
                "estimated_cost_usd": 0.0, "provider_cost_usd": 0.0, "video_path": None,
                "comparison_status": "not_checked", "source_kind": block["source_kind"], "mock": block["mock"]}
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "source_block.json", block)  # Prior fees retained here, never counted as new attempts.
    write_json(output / "source_inputs.json", source)  # Keep full plans for identity/seed provenance.
    write_json(output / "bundle.json", bundle)
    write_json(output / "preparation.json", prepared)
    return prepared
