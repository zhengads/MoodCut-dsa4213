"""CLI integration with local fixtures; no paid requests or model inference."""

from contextlib import contextmanager
import csv
import io
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from moodcut.__main__ import main
from moodcut import client as client_module
from moodcut.pipeline import CONDITIONS, make_mock_client, read_json


ROOT = Path(__file__).resolve().parents[1]


def run_cli(*arguments):
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run([sys.executable, "-m", "moodcut", *arguments],
                          capture_output=True, text=True, timeout=15, env=environment)


@pytest.mark.parametrize("arguments,expected", [((), "usage:"), (("--help",), "MoodCut"),
    (("--version",), "MoodCut 0.0.0"), (("plan", "--help"), "--allow-paid")])
def test_help_and_version(arguments, expected):
    result = run_cli(*arguments)
    assert result.returncode == 0 and expected in result.stdout


def test_unknown_command_rejected():
    result = run_cli("unknown")
    assert result.returncode != 0 and "invalid choice" in result.stderr


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("CLI tests must never use network")
    monkeypatch.setattr("urllib.request.OpenerDirector.open", fail)


def input_args():
    return ["--project-root", str(ROOT), "--scene", "tests/fixtures/scene.json",
            "--assets", "tests/fixtures/assets.json"]


def test_plan_and_review_outputs_match_public_contract(tmp_path):
    initial, revised = tmp_path / "initial.json", tmp_path / "review.json"
    assert main(["plan", *input_args(), "--mock", "--output", str(initial)]) == 0
    plan = read_json(initial)
    assert plan["shots"]
    assert set(read_json(initial.with_suffix(".trace.json"))["raw_responses"]) == {"director", "scene", "shot"}
    assert read_json(initial.with_suffix(".calls.json"))["real_http_calls"] == 0
    assert main(["review", *input_args(), "--plan", str(initial), "--mode", "moodcut",
                 "--output", str(revised)]) == 0
    result = read_json(revised)
    assert result["status"] == "applied" and result["plan"] != plan
    assert set(result) == {"plan", "report", "patch", "verification", "status", "errors"}
    assert len(read_json(revised.with_suffix(".calls.json"))["call_records"]) == 3
    assert revised.with_suffix(".trace.jsonl").is_file()


def test_smoke_is_offline_complete_and_keeps_shared_initial(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    output = tmp_path / "smoke"
    assert main(["smoke", "--project-root", str(ROOT), "--output", str(output)]) == 0
    block = read_json(output / "block.json")
    assert block["mock"] and block["source_kind"] == "synthetic"
    assert {r["condition"] for r in block["runs"]} == set(CONDITIONS)
    assert len({r["initial_plan_sha256"] for r in block["runs"]}) == 1
    assert all(r["render_status"] == "skipped" for r in block["runs"])


def test_no_render_run_and_cache_reuse(tmp_path):
    common = ["run", "--project-root", str(ROOT), "--no-render", "--cache-dir", str(tmp_path / "cache")]
    assert main([*common, "--output", str(tmp_path / "first")]) == 0
    assert main([*common, "--output", str(tmp_path / "second")]) == 0
    block = read_json(tmp_path / "second/block.json")
    assert block["planning"]["cache_hit"] and block["planning"]["calls"] == 0
    assert all(r["run_status"] == "completed" for r in block["runs"])


def test_existing_output_rejected_without_replacement(tmp_path):
    output = tmp_path / "existing.json"
    output.write_text("original", encoding="utf-8")
    assert main(["plan", *input_args(), "--output", str(output)]) == 1
    assert output.read_text(encoding="utf-8") == "original"
    assert not output.with_suffix(".calls.json").exists()


def test_plan_failure_keeps_raw_diagnostics(tmp_path):
    responses = tmp_path / "responses.json"
    responses.write_text(json.dumps([{"bad": "schema"}]), encoding="utf-8")
    output = tmp_path / "bad.json"
    assert main(["plan", *input_args(), "--responses", str(responses), "--output", str(output)]) == 1
    error = read_json(output.with_suffix(".error.json"))
    assert error["stage"] == "director" and error["raw_responses"]["director"] == {"bad": "schema"}
    assert not output.exists() and len(read_json(output.with_suffix(".calls.json"))["call_records"]) == 1


def test_missing_live_budget_fails_before_transport(tmp_path):
    assert main(["plan", *input_args(), "--allow-paid", "--output", str(tmp_path / "x.json")]) == 1
    assert not list(tmp_path.glob("*.json"))


def test_live_and_mock_are_mutually_exclusive(tmp_path):
    with pytest.raises(SystemExit) as error:
        main(["plan", *input_args(), "--allow-paid", "--mock", "--output", str(tmp_path / "x.json")])
    assert error.value.code == 2


def test_render_dependency_failure_happens_before_live_client(tmp_path, monkeypatch):
    invoked = []
    def no_dependencies(**kwargs):
        raise ValueError("Missing FFmpeg/font")
    monkeypatch.setattr("moodcut.pipeline.resolve_render_dependencies", no_dependencies)
    monkeypatch.setattr(client_module.OpenRouterClient, "from_env", lambda *a, **k: invoked.append(True))
    assert main(["run", "--project-root", str(ROOT), "--allow-paid", "--max-cost-usd", "0.1",
                 "--output", str(tmp_path / "run")]) == 1
    assert invoked == [] and not (tmp_path / "run").exists()


def test_plan_openrouter_transport_stub_records_usage_without_network(tmp_path, monkeypatch):
    scene, manifest = [read_json(ROOT / "tests/fixtures" / f) for f in ("scene.json", "assets.json")]
    queued = make_mock_client(scene, manifest, include_planning=True, conditions=())
    bodies = [queued.complete_json(stage="test", system="", user="", max_output_tokens=1) for _ in range(3)]
    requests = []
    class Opener:
        @contextmanager
        def open(self, request, timeout):
            requests.append(json.loads(request.data))
            body = bodies[len(requests) - 1]
            yield io.BytesIO(json.dumps({"id": "fixture", "model": "test/model",
                "choices": [{"message": {"content": json.dumps(body)}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 20, "cost": 0.0001}}).encode())
    monkeypatch.setattr(client_module, "build_opener", lambda *args: Opener())
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-only-never-real")
    config = tmp_path / "model.json"
    config.write_text(json.dumps({"model": "test/model", "input_price_per_million": 1,
                                  "output_price_per_million": 1}), encoding="utf-8")
    output = tmp_path / "live-fixture.json"
    assert main(["plan", *input_args(), "--allow-paid", "--max-cost-usd", "0.2",
                 "--model-config", str(config), "--output", str(output)]) == 0
    calls = read_json(output.with_suffix(".calls.json"))
    assert len(requests) == 3 and calls["calls"] == 3
    assert calls["provider_cost_usd"] == pytest.approx(0.0003)
    assert all(request["model"] == "test/model" for request in requests)
    assert "test-only-never-real" not in "".join(p.read_text(encoding="utf-8") for p in tmp_path.glob("*.json"))


def test_import_synopsis_command(tmp_path):
    source, output = tmp_path / "source.json", tmp_path / "imported.json"
    source.write_text(json.dumps({"MovieScript": "A greets B.", "Character": ["A", "B"]}), encoding="utf-8")
    assert main(["import-synopsis", "--input", str(source), "--output", str(output)]) == 0
    assert read_json(output) == {"story": "A greets B.", "character_names": ["A", "B"]}


def test_evaluate_dry_run_only_enumerates_and_retains_status(tmp_path):
    config, output = tmp_path / "experiment.json", tmp_path / "assignments.json"
    config.write_text(json.dumps({"status": "not_formally_approved", "scenes": [str(ROOT / "tests/fixtures/scene.json")],
        "replicates": 1, "tones": ["suspicious"], "conditions": list(CONDITIONS)}), encoding="utf-8")
    assert main(["evaluate", "--config", str(config), "--dry-run", "--output", str(output)]) == 0
    result = read_json(output)
    assert result["paid_calls"] == 0 and result["planned_runs"] == 3
    assert result["config_status"] == "not_formally_approved"


def test_evaluate_no_ratings_reports_missing_coverage(tmp_path):
    block = tmp_path / "smoke"
    assert main(["smoke", "--project-root", str(ROOT), "--output", str(block)]) == 0
    output = tmp_path / "summary.json"
    assert main(["evaluate", "--records", str(block / "block.json"), "--output", str(output)]) == 0
    summary = read_json(output)
    assert summary["overall"]["coverage"]["planned_runs"] == 3
    assert summary["overall"]["coverage"]["rated_clips"] == 0
    assert summary["overall"]["equal_clip_means"]["tone_accuracy"] is None
    ledger = summary["block_ledger_accounting"]
    assert ledger["complete"] and ledger["shared_planning"]["calls"] == 3
    assert ledger["all_phases"]["calls"] == 9
    assert ledger["all_phases"]["real_http_calls"] == 0
    assert ledger["all_phases"]["provider_cost_usd"] == 0
    assert main(["evaluate", "--records", str(block / "baseline/run.json"),
                 "--output", str(tmp_path / "partial.json")]) == 0
    assert read_json(tmp_path / "partial.json")["block_ledger_accounting"]["all_phases"] is None


def test_evaluate_blind_export_then_ratings_with_private_key(tmp_path):
    records = []
    for index, condition in enumerate(CONDITIONS):
        video = tmp_path / f"video{index}.mp4"
        video.write_bytes(b"unit-test-export-bytes-not-a-decoded-film")
        records.append({"schema_version": "1.0", "run_id": f"r{index}", "block_id": "b1",
            "scene_id": "scene1", "tone": "suspicious", "replicate": 1, "condition": condition,
            "initial_plan_sha256": "a" * 64, "source_kind": "synthetic", "render_status": "rendered",
            "video_path": str(video), "calls": 0})
    record_file = tmp_path / "records.json"
    record_file.write_text(json.dumps(records), encoding="utf-8")
    exported = tmp_path / "blind"
    assert main(["evaluate", "--records", str(record_file), "--blind-output", str(exported)]) == 0
    ratings = exported / "public/ratings.csv"
    with ratings.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row.update(rater_id="test-rater", perceived_tone="suspicious", confidence="3",
                   naturalness="3", story_clarity="3", overstatement="3")
    with ratings.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    summary = tmp_path / "summary.json"
    assert main(["evaluate", "--records", str(record_file), "--ratings", str(ratings),
                 "--private-key", str(exported / "PRIVATE/private_key.csv"), "--output", str(summary)]) == 0
    assert read_json(summary)["overall"]["equal_clip_means"]["tone_accuracy"] == 1
    # Stable assignment IDs must not silently join ratings to a replaced video.
    original_video = Path(records[0]["video_path"]).read_bytes()
    Path(records[0]["video_path"]).write_bytes(b"different-render-of-the-same-plan")
    assert main(["evaluate", "--records", str(record_file), "--ratings", str(ratings),
                 "--private-key", str(exported / "PRIVATE/private_key.csv")]) == 1
    Path(records[0]["video_path"]).write_bytes(original_video)
    # Assignment IDs alone do not identify a model/prompt/initial-plan version.
    records[0]["initial_plan_sha256"] = "b" * 64
    record_file.write_text(json.dumps(records), encoding="utf-8")
    assert main(["evaluate", "--records", str(record_file), "--ratings", str(ratings),
                 "--private-key", str(exported / "PRIVATE/private_key.csv")]) == 1


def test_ratings_without_private_key_rejected(tmp_path):
    assert main(["evaluate", "--records", "missing.json", "--ratings", "ratings.csv"]) == 1


@pytest.fixture
def generated_source(tmp_path, monkeypatch):
    """Persist real pipeline records using explicitly labeled P2/P3 doubles."""
    from copy import deepcopy
    from moodcut import pipeline
    data = read_json(ROOT / "tests/fixtures/generated_contract.json")
    manifest = read_json(ROOT / "tests/fixtures/assets.json")
    data["settings"]["model"] = "alibaba/wan-2.7"
    def plan(scene, assets, client, *, project_root, output_mode):
        return {"plan": deepcopy(data["initial_plan"]), "raw_responses": {"software_double": True}}
    def review(scene, initial, assets, client, *, mode, project_root, output_mode):
        return {"plan": deepcopy(data["condition_plans"][mode]), "status": "applied", "errors": [],
                "software_double": "P3 test dependency, not model output"}
    monkeypatch.setattr(pipeline, "make_plan_with_trace", plan)
    monkeypatch.setattr(pipeline, "review_and_revise", review)
    source = tmp_path / "source"
    block = pipeline.run_experiment(data["scene"], manifest, pipeline.FakeClient([]), out_dir=source,
                                    project_root=ROOT, output_mode="generated", generation_settings=data["settings"],
                                    template_sha256=data["template_sha256"])
    assert block["status"] == "prepared"
    monkeypatch.setattr(pipeline, "make_plan_with_trace", lambda *a, **k: pytest.fail("Do not replan saved scripts"))
    monkeypatch.setattr(pipeline, "review_and_revise", lambda *a, **k: pytest.fail("Do not review saved scripts again"))
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr("socket.socket.connect", lambda *a, **k: pytest.fail("No real network"))
    return source, block


def software_compiler(monkeypatch):
    """P4 protocol double only; does not implement or validate film generation."""
    from moodcut import video_generation
    from moodcut.contracts import json_hash, shared_generation_sha256
    from moodcut.video_client import estimate_video_cost
    calls = []
    def compile(scene, initial, plans, manifest, settings, *, project_root, template_sha256, pricing_config):
        calls.append((scene, initial, plans, manifest, settings))
        conditions = []
        for condition in CONDITIONS:
            jobs = []
            for index, shot in enumerate(plans[condition]["shots"]):
                request = {"model": settings["model"], "resolution": settings["resolution"],
                           "aspect_ratio": settings["aspect_ratio"], "generate_audio": True,
                           "seed": settings["seed"] + index, "duration": shot["duration_s"],
                           "input_references": [{"type": "image_url", "image_url": {"url": "https://example.invalid/software.png"}}],
                           "prompt": json.dumps({"software_double": True, "dialogue": shot["dialogue"]})}
                jobs.append({"shot_id": shot["shot_id"], "request": request,
                             "request_sha256": json_hash(request),
                             "quoted_cost_usd": str(estimate_video_cost(pricing_config, request))})
            conditions.append({"condition": condition, "final_plan_sha256": json_hash(plans[condition]), "jobs": jobs})
        return {"schema_version": "1.1", "output_mode": "generated", "kind": "generated_three_condition_bundle",
                "initial_plan_sha256": json_hash(initial), "shared_generation_sha256": shared_generation_sha256(
                    scene, initial, manifest, settings, template_sha256=template_sha256),
                "settings": settings, "conditions": conditions}
    monkeypatch.setattr(video_generation, "build_generated_video_bundle", compile, raising=False)
    return calls


def generated_args(source, output, *extra):
    return ["run", "--project-root", str(ROOT), "--output-mode", "generated",
            "--source-block", str(source / "block.json"), "--pricing-config", "configs/video.json",
            "--output", str(output), *extra]


def test_generated_cli_single_shot_keeps_original_index_seed_and_hash(generated_source, tmp_path, monkeypatch):
    source, block = generated_source
    calls = software_compiler(monkeypatch)
    output = tmp_path / "one-shot"
    assert main(generated_args(source, output, "--shot-id", "s2")) == 0
    prepared = read_json(output / "preparation.json")
    bundle = read_json(output / "bundle.json")
    assert prepared["preparation_stage"] == "requests" and prepared["status"] == "prepared_offline"
    assert prepared["selected_shot_ids"] == ["s2"] and len(calls) == 1
    assert prepared["shared_generation_sha256"] == block["shared_generation_sha256"]
    assert prepared["generation_posts"] == prepared["video_get_calls"] == prepared["real_http_calls"] == 0
    assert prepared["provider_cost_usd"] == 0.0 and prepared["quoted_cost_usd"] == "1.80"
    assert prepared["comparison_status"] == "not_checked" and prepared["video_path"] is None
    for condition in bundle["conditions"]:
        assert len(condition["jobs"]) == 1
        job = condition["jobs"][0]
        assert job["shot_id"] == "s2" and job["shot_index"] == 1 and job["request"]["seed"] == 4214
    # Full source plans remain unchanged; do not truncate before compiler input.
    assert all(len(plan["shots"]) == 3 for plan in calls[0][2].values())
    assert read_json(source / "block.json") == block


def rewrite_generated_block(source, block, *, sync_runs=True):
    (source / "block.json").write_text(json.dumps(block, ensure_ascii=False), encoding="utf-8")
    if sync_runs:
        for row in block["runs"]:
            path = source / row["condition"] / "run.json"
            if path.parent.exists():
                path.write_text(json.dumps(row, ensure_ascii=False), encoding="utf-8")


def test_generated_cli_all_shots_directory_source_no_clients_and_preserves_ledger(generated_source, tmp_path, monkeypatch):
    from moodcut import pipeline, video_client
    source, block = generated_source
    calls = software_compiler(monkeypatch)
    for module, name in ((client_module.OpenRouterClient, "from_env"), (video_client, "OpenRouterVideoClient"),
                         (video_client, "fetch_video_models"), (pipeline, "resolve_render_dependencies")):
        monkeypatch.setattr(module, name, lambda *a, **k: pytest.fail("Preparation must not create clients or fetch/render"))
    # Software ledger with unknown historical expense; preparation cannot erase it.
    block["planning"]["provider_cost_usd"] = None
    (source / "planning.json").write_text(json.dumps(block["planning"]), encoding="utf-8")
    rewrite_generated_block(source, block)
    before = {p.relative_to(source): p.read_bytes() for p in source.rglob("*.json")}
    output = tmp_path / "all-shots"
    args = generated_args(source, output)
    args[args.index("--source-block") + 1] = str(source)
    monkeypatch.chdir(tmp_path)
    assert main(args) == 0
    assert len(calls) == 1
    prep = read_json(output / "preparation.json")
    assert prep["selected_shot_ids"] == ["s1", "s2", "s3"] and prep["quoted_cost_usd"] == "5.40"
    assert prep["calls"] == 0 and prep["provider_cost_usd"] == prep["estimated_cost_usd"] == 0.0
    assert read_json(output / "source_block.json")["planning"]["provider_cost_usd"] is None
    assert {p.relative_to(source): p.read_bytes() for p in source.rglob("*.json")} == before
    bundle = read_json(output / "bundle.json")
    for condition in bundle["conditions"]:
        assert [j["request"]["seed"] for j in condition["jobs"]] == [4213, 4214, 4215]
        assert [j["shot_index"] for j in condition["jobs"]] == [0, 1, 2]
    snapshot = read_json(output / "source_inputs.json")
    assert len(snapshot["initial"]["shots"]) == 3 and len(snapshot["plans"]) == 3


def test_generated_missing_compiler_is_explicit_and_never_uses_old_pair(generated_source, tmp_path, monkeypatch, capsys):
    from moodcut import video_generation
    source, _ = generated_source
    monkeypatch.delattr(video_generation, "build_generated_video_bundle", raising=False)
    monkeypatch.setattr(video_generation, "build_video_bundle", lambda *a, **k: pytest.fail("No legacy fallback"))
    output = tmp_path / "missing-compiler"
    assert main(generated_args(source, output)) == 1
    assert "#24" in capsys.readouterr().err and not output.exists()


@pytest.mark.parametrize("shot_id", ["unknown", "", "s0"])
def test_generated_unknown_shot_fails_before_compiling(generated_source, tmp_path, monkeypatch, shot_id):
    source, _ = generated_source
    calls = software_compiler(monkeypatch)
    output = tmp_path / "bad-shot"
    assert main(generated_args(source, output, "--shot-id", shot_id)) == 1
    assert calls == [] and not output.exists()


@pytest.mark.parametrize("kind", ["version", "mode", "block_failed", "missing_condition", "old_condition", "disk_run",
    "scene", "model", "seed", "template", "initial", "non_dialogue", "final_hash", "unchanged_changed",
    "rejected", "review_failed", "no_changes", "condition_input", "prompt_hashes", "submitted", "planning",
    "review_source", "review_plan", "boolean_attempts"])
def test_generated_source_tampering_rejected_before_compiler(generated_source, tmp_path, monkeypatch, kind):
    from moodcut.contracts import json_hash
    source, block = generated_source
    calls = software_compiler(monkeypatch)
    sync_runs = True
    if kind == "version":
        block["schema_version"] = "1.0"
    elif kind == "mode":
        block["output_mode"] = "animatic"
    elif kind == "block_failed":
        block["status"] = "failed"
    elif kind == "missing_condition":
        block["runs"].pop()
    elif kind == "old_condition":
        block["runs"][2]["condition"] = "dialogue_revision"
    elif kind == "disk_run":
        record = read_json(source / "generic_review/run.json")
        record["calls"] += 1
        (source / "generic_review/run.json").write_text(json.dumps(record), encoding="utf-8")
        sync_runs = False
    elif kind in ("scene", "model", "seed", "initial"):
        name = {"scene": "scene.json", "model": "generation_settings.json", "seed": "generation_settings.json",
                "initial": "initial.json"}[kind]
        data = read_json(source / name)
        if kind == "scene":
            data["story"] += " altered"
        elif kind == "model":
            data["model"] += "-altered"
        elif kind == "seed":
            data["seed"] += 1
        else:
            data["shots"][0]["dialogue"][0]["text"] += " altered"
        (source / name).write_text(json.dumps(data), encoding="utf-8")
    elif kind == "template":
        block["template_sha256"] = "a" * 64
    elif kind in ("non_dialogue", "final_hash", "unchanged_changed"):
        final = read_json(source / "generic_review/final.json")
        if kind == "non_dialogue":
            final["shots"][0]["direction"] += " altered"
        else:
            final["shots"][0]["dialogue"][0]["text"] += " altered"
        (source / "generic_review/final.json").write_text(json.dumps(final), encoding="utf-8")
        if kind != "final_hash":
            block["runs"][1]["final_plan_sha256"] = json_hash(final)
        if kind == "unchanged_changed":
            block["runs"][1]["review_status"] = "unchanged"
    elif kind in ("rejected", "review_failed", "no_changes"):
        block["runs"][1]["review_status"] = kind
    elif kind == "condition_input":
        (source / "moodcut/initial.json").write_text("{}", encoding="utf-8")
    elif kind == "prompt_hashes":
        block["runs"][1]["prompt_hashes"] = []
    elif kind in ("review_source", "review_plan"):
        review = read_json(source / "generic_review/review.json")
        if kind == "review_source":
            review["status"] = "rejected"
        else:
            review["plan"]["shots"][0]["dialogue"][0]["text"] += " inconsistent review candidate"
        (source / "generic_review/review.json").write_text(json.dumps(review), encoding="utf-8")
    elif kind == "boolean_attempts":
        block["runs"][1]["generation_posts"] = False
    elif kind == "submitted":
        block["runs"][1]["generation_posts"] = 1
    else:
        block["planning"]["calls"] += 1  # Disk planning.json remains unchanged.
    rewrite_generated_block(source, block, sync_runs=sync_runs)
    output = tmp_path / "rejected"
    assert main(generated_args(source, output)) == 1
    assert calls == [] and not output.exists()


@pytest.mark.parametrize("kind", ["version", "kind", "initial", "shared", "settings", "conditions", "final",
    "shots", "shot_order", "request_hash", "seed", "seed_type", "duration", "audio", "frame_images",
    "references", "prompt", "quote", "nonfinite_quote", "quote_type", "mutated_inputs"])
def test_generated_rejects_invalid_compiler_protocol(generated_source, tmp_path, monkeypatch, kind):
    from moodcut import video_generation
    from moodcut.contracts import json_hash
    source, _ = generated_source
    software_compiler(monkeypatch)
    original = video_generation.build_generated_video_bundle
    def faulty(*args, **kwargs):
        bundle = original(*args, **kwargs)
        condition, job = bundle["conditions"][0], bundle["conditions"][0]["jobs"][0]
        request = job["request"]
        if kind == "version":
            bundle["schema_version"] = "1.0"
        elif kind == "kind":
            bundle["kind"] = "derived_development_video_pair"
        elif kind in ("initial", "shared"):
            bundle["initial_plan_sha256" if kind == "initial" else "shared_generation_sha256"] = "a" * 64
        elif kind == "settings":
            bundle["settings"] = dict(bundle["settings"], seed=1)
        elif kind == "conditions":
            bundle["conditions"].pop()
        elif kind == "final":
            condition["final_plan_sha256"] = "a" * 64
        elif kind == "shots":
            condition["jobs"].pop()
        elif kind == "shot_order":
            condition["jobs"].reverse()
        elif kind == "request_hash":
            job["request_sha256"] = "a" * 64
        elif kind == "seed":
            request["seed"] = 1
        elif kind == "seed_type":
            request["seed"] = float(request["seed"])
        elif kind == "duration":
            request["duration"] += 1
        elif kind == "audio":
            request["generate_audio"] = False
        elif kind == "frame_images":
            request["frame_images"] = ["software frame"]
        elif kind == "references":
            request["input_references"] = []
        elif kind == "prompt":
            request["prompt"] = " "
        elif kind == "quote":
            job["quoted_cost_usd"] = "100.00"
        elif kind == "nonfinite_quote":
            job["quoted_cost_usd"] = "NaN"
        elif kind == "quote_type":
            job["quoted_cost_usd"] = 0.60
        else:
            args[1]["shots"][0]["direction"] += " tampered by compiler"
        if kind != "request_hash":
            job["request_sha256"] = json_hash(request)
        return bundle
    monkeypatch.setattr(video_generation, "build_generated_video_bundle", faulty)
    output = tmp_path / "bad-compiler"
    assert main(generated_args(source, output)) == 1
    assert not output.exists()


def test_generated_existing_output_kept_before_compiler(generated_source, tmp_path, monkeypatch):
    source, _ = generated_source
    calls = software_compiler(monkeypatch)
    output = tmp_path / "existing"
    output.mkdir()
    marker = output / "original.txt"
    marker.write_text("preserve", encoding="utf-8")
    assert main(generated_args(source, output)) == 1
    assert calls == [] and marker.read_text(encoding="utf-8") == "preserve"


@pytest.mark.parametrize("extra", [("--allow-paid",), ("--max-cost-usd", "0.1"), ("--responses", "missing.json"),
    ("--cache-dir", "cache"), ("--scene", "other.json"), ("--assets", "other.json"), ("--no-render",),
    ("--font", "font.ttf"), ("--replicate", "2"), ("--source-kind", "formal"), ("--model-config", "other.json")])
def test_generated_rejects_live_and_planning_overrides_before_clients(generated_source, tmp_path, monkeypatch, extra):
    source, _ = generated_source
    monkeypatch.setattr(client_module.OpenRouterClient, "from_env", lambda *a, **k: pytest.fail("No client permitted"))
    assert main(generated_args(source, tmp_path / "bad-options", *extra)) == 1
    assert not (tmp_path / "bad-options").exists()


def test_generated_mode_is_explicit_and_source_is_required(generated_source, tmp_path):
    source, _ = generated_source
    args = generated_args(source, tmp_path / "implicit")
    args[args.index("--output-mode") + 1] = "animatic"
    assert main(args) == 1
    assert main(["run", "--output-mode", "generated", "--output", str(tmp_path / "no-source")]) == 1
    with pytest.raises(SystemExit) as exc:
        main(["run", "--output-mode", "unknown", "--output", str(tmp_path / "unknown")])
    assert exc.value.code == 2


def test_generated_valid_unchanged_source_is_accepted(generated_source, tmp_path, monkeypatch):
    from moodcut.contracts import json_hash
    source, block = generated_source
    software_compiler(monkeypatch)
    initial = read_json(source / "initial.json")
    for row in block["runs"][1:]:
        row["review_status"] = "unchanged"
        row["final_plan_sha256"] = json_hash(initial)
        (source / row["condition"] / "final.json").write_text(json.dumps(initial), encoding="utf-8")
        review = read_json(source / row["condition"] / "review.json")
        review.update(plan=initial, status="unchanged")
        (source / row["condition"] / "review.json").write_text(json.dumps(review), encoding="utf-8")
    rewrite_generated_block(source, block)
    output = tmp_path / "unchanged"
    assert main(generated_args(source, output, "--shot-id", "s3")) == 0
    prepared = read_json(output / "preparation.json")
    assert prepared["selected_shot_ids"] == ["s3"] and prepared["calls"] == 0
    assert {j["request"]["seed"] for c in read_json(output / "bundle.json")["conditions"] for j in c["jobs"]} == {4215}


@pytest.mark.parametrize("change", ["source", "output_race"])
def test_generated_changes_during_compilation_are_not_overwritten(generated_source, tmp_path, monkeypatch, change):
    from moodcut import video_generation
    source, block = generated_source
    software_compiler(monkeypatch)
    original = video_generation.build_generated_video_bundle
    output = tmp_path / "concurrent"
    def concurrent(*args, **kwargs):
        bundle = original(*args, **kwargs)
        if change == "source":
            block["planning"]["provider_cost_usd"] = None
            (source / "planning.json").write_text(json.dumps(block["planning"]), encoding="utf-8")
            rewrite_generated_block(source, block)
        else:
            output.mkdir()
            (output / "other-result.txt").write_text("keep", encoding="utf-8")
        return bundle
    monkeypatch.setattr(video_generation, "build_generated_video_bundle", concurrent)
    assert main(generated_args(source, output)) == 1
    if change == "source":
        assert not output.exists()
        assert read_json(source / "planning.json")["provider_cost_usd"] is None
    else:
        assert (output / "other-result.txt").read_text(encoding="utf-8") == "keep"
        assert not (output / "bundle.json").exists()
