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
