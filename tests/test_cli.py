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
