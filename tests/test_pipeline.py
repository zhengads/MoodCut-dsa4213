"""Pipeline integration exercises synthetic fixtures and mocked HTTP/video only."""
from copy import deepcopy
import io
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from moodcut import pipeline
from moodcut.client import FakeClient, OpenRouterClient


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def inputs():
    return tuple(json.loads((ROOT / "tests/fixtures" / name).read_text(encoding="utf-8"))
                 for name in ("scene.json", "assets.json", "plan.json"))


def experiment(scene, assets, output, **kwargs):
    return pipeline.run_experiment(scene, assets, out_dir=output, project_root=ROOT,
                                   render=False, **kwargs)


def test_one_planning_three_conditions_share_initial_without_mutating_inputs(inputs, tmp_path):
    scene, assets, _ = inputs
    before = deepcopy((scene, assets))
    block = experiment(scene, assets, tmp_path / "run")
    assert block["status"] == "completed"
    assert block["planning"]["calls"] == 3
    assert [call["stage"] for call in block["planning"]["call_records"]] == ["director", "scene", "shot"]
    assert [run["calls"] for run in block["runs"]] == [0, 3, 3]
    assert len({run["initial_plan_sha256"] for run in block["runs"]}) == 1
    assert block["initial_plan_sha256"] == block["runs"][0]["initial_plan_sha256"]
    assert len({run["run_id"] for run in block["runs"]}) == 3
    assert len({run["block_id"] for run in block["runs"]}) == 1
    assert (scene, assets) == before
    baseline, generic, moodcut = block["runs"]
    assert baseline["initial_plan_sha256"] == baseline["final_plan_sha256"]
    assert generic["final_plan_sha256"] == moodcut["final_plan_sha256"]
    assert generic["initial_plan_sha256"] != generic["final_plan_sha256"]
    # Equal mock edits deliberately do not constitute a claimed treatment benefit.
    assert all(run["mock"] and run["source_kind"] == "synthetic" for run in block["runs"])


def test_raw_responses_review_traces_and_independent_run_artifacts(inputs, tmp_path):
    scene, assets, _ = inputs
    output = tmp_path / "run"
    block = experiment(scene, assets, output)
    saved = pipeline.read_json(output / "planning.json")
    assert set(saved["raw_responses"]) == {"director", "scene", "shot"}
    assert saved == block["planning"]
    for condition in pipeline.CONDITIONS:
        directory = output / condition
        record = pipeline.read_json(directory / "run.json")
        assert record["condition"] == condition
        assert pipeline.read_json(directory / "initial.json") == saved["raw_responses"]["shot"]
        assert (directory / "final.json").is_file()
        if condition == "baseline":
            assert not (directory / "review.json").exists()
        else:
            assert pipeline.read_json(directory / "review.json")["status"] == "applied"
            events = [json.loads(line) for line in (directory / "review_trace.jsonl")
                      .read_text(encoding="utf-8").splitlines()]
            assert [e["stage"] for e in events if e["event"] == "request"] == ["critique", "revise", "verify"]
            assert len([e for e in events if e["event"] == "response"]) == 3


def test_verified_cache_reuse_plans_zero_times_and_review_six_times(inputs, tmp_path):
    scene, assets, _ = inputs
    cache = tmp_path / "cache"
    first = experiment(scene, assets, tmp_path / "first", cache_dir=cache)
    original = next(cache.glob("*.json")).read_bytes()
    second = experiment(scene, assets, tmp_path / "second", cache_dir=cache)
    assert second["status"] == "completed"
    assert second["planning"]["cache_hit"] is True
    assert second["planning"]["calls"] == 0
    assert sum(row["calls"] for row in second["runs"]) == 6
    assert first["initial_plan_sha256"] == second["initial_plan_sha256"]
    assert next(cache.glob("*.json")).read_bytes() == original
    assert not list(cache.glob("*.lock"))


def test_corrupt_cache_retained_and_no_fresh_client_created(inputs, tmp_path, monkeypatch):
    scene, assets, _ = inputs
    cache = tmp_path / "cache"
    experiment(scene, assets, tmp_path / "first", cache_dir=cache)
    cache_file = next(cache.glob("*.json"))
    corrupted = json.loads(cache_file.read_text(encoding="utf-8"))
    corrupted["plan"]["shots"][0]["narration"] = "tampered fixture"
    cache_file.write_text(json.dumps(corrupted), encoding="utf-8")
    retained = cache_file.read_bytes()
    create_client = Mock(side_effect=AssertionError("Corrupt cache must not replan"))
    monkeypatch.setattr(pipeline, "make_mock_client", create_client)
    block = experiment(scene, assets, tmp_path / "second", cache_dir=cache)
    assert block["status"] == "failed"
    assert block["planning"]["status"] == "failed"
    assert block["planning"]["calls"] == 0
    assert all(row["run_status"] == "failed" for row in block["runs"])
    assert cache_file.read_bytes() == retained
    create_client.assert_not_called()


@pytest.mark.parametrize("dimension", ["replicate", "tone", "prompt", "model"])
def test_cache_identity_changes_require_new_plan(inputs, tmp_path, monkeypatch, dimension):
    scene, assets, _ = inputs
    cache = tmp_path / "cache"
    kwargs = {}
    first = experiment(scene, assets, tmp_path / "first", cache_dir=cache)
    if dimension == "replicate":
        kwargs["replicate"] = 2
    elif dimension == "tone":
        scene["tone"] = "hostile" if scene["tone"] != "hostile" else "suspicious"
    elif dimension == "prompt":
        hashes = pipeline.get_planning_prompt_hashes() | {"director": "f" * 64}
        monkeypatch.setattr(pipeline, "get_planning_prompt_hashes", lambda: hashes)
    else:
        original = pipeline._model_settings
        monkeypatch.setattr(pipeline, "_model_settings", lambda client: original(client) | {"model_id": "fake/changed"})
    second = experiment(scene, assets, tmp_path / "second", cache_dir=cache, **kwargs)
    assert second["planning"]["cache_key"] != first["planning"]["cache_key"]
    assert second["planning"]["cache_hit"] is False
    assert second["planning"]["calls"] == 3
    assert second["status"] == "completed"
    assert len(list(cache.glob("*.json"))) == 2


def test_existing_cache_lock_not_removed_and_no_planning_call(inputs, tmp_path):
    scene, assets, _ = inputs
    cache = tmp_path / "cache"
    first = experiment(scene, assets, tmp_path / "first", cache_dir=cache)
    next(cache.glob("*.json")).unlink()
    lock = cache / f'{first["planning"]["cache_key"]}.lock'
    lock.write_text("another-worker", encoding="utf-8")
    client = pipeline.make_mock_client(scene, assets, include_planning=True)
    block = experiment(scene, assets, tmp_path / "second", cache_dir=cache, client=client)
    assert block["status"] == "failed"
    assert block["planning"]["status"] == "failed"
    assert client.calls == []
    assert lock.read_text(encoding="utf-8") == "another-worker"
    assert not list(cache.glob("*.json"))


def test_planning_failure_saves_three_failed_records_not_success(inputs, tmp_path):
    scene, assets, _ = inputs
    client = FakeClient([{"scene_id": "wrong"}])
    block = experiment(scene, assets, tmp_path / "failed", client=client)
    assert block["status"] == "failed"
    assert block["planning"]["status"] == "failed"
    assert block["planning"]["calls"] == 1
    assert block["planning"]["raw_responses"] == {"director": {"scene_id": "wrong"}}
    for row in block["runs"]:
        assert row["run_status"] == "failed"
        assert row["validation_status"] == "failed"
        assert row["initial_plan_sha256"] is None
        assert row["calls"] == 0
        assert row["render_status"] != "rendered"
        assert row["errors"]
        assert pipeline.read_json(tmp_path / "failed" / row["condition"] / "run.json") == row


def fake_render(plan, manifest, *, project_root, out_dir, font_path):
    path = Path(out_dir)
    path.mkdir(parents=True, exist_ok=False)
    video = path / "fixture.mp4"
    video.write_bytes(b"synthetic mock video; not a playable MP4")
    return dict(status="rendered", video_path=str(video), contact_sheet_path=None,
                timeline_path=None, duration_s=60, errors=[])


def test_review_failure_still_renders_original_with_distinct_failure_metadata(inputs, tmp_path, monkeypatch):
    scene, assets, plan = inputs
    monkeypatch.setattr(pipeline, "render_plan", fake_render)
    row = pipeline.run_condition(scene, plan, assets, FakeClient([]), condition="moodcut",
                                  out_dir=tmp_path / "review_failed", project_root=ROOT,
                                  font_path="unused-font.ttf")
    assert row["render_status"] == "rendered"
    assert row["review_status"] == "review_failed"
    assert row["run_status"] == "failed"
    assert row["validation_status"] == "passed"
    assert row["final_plan_sha256"] == row["initial_plan_sha256"]
    assert row["errors"]
    assert pipeline.read_json(tmp_path / "review_failed" / "final.json") == plan


def test_render_failure_keeps_valid_plan_and_review_status(inputs, tmp_path, monkeypatch):
    scene, assets, plan = inputs
    def fail_render(*args, **kwargs):
        return dict(status="render_failed", video_path=None, errors=["synthetic ffmpeg failure"])
    monkeypatch.setattr(pipeline, "render_plan", fail_render)
    row = pipeline.run_condition(scene, plan, assets, FakeClient([]), condition="baseline",
                                  out_dir=tmp_path / "render_failed", project_root=ROOT, font_path=None)
    assert row["run_status"] == "failed"
    assert row["render_status"] == "render_failed"
    assert row["validation_status"] == "passed"
    assert row["review_status"] == "not_applicable"
    assert row["calls"] == 0 and row["video_path"] is None
    assert row["errors"] == ["synthetic ffmpeg failure"]


def test_existing_output_preserved_before_any_client_call(inputs, tmp_path):
    scene, assets, plan = inputs
    output = tmp_path / "existing"
    output.mkdir()
    marker = output / "existing.json"
    marker.write_bytes(b"original-result")
    client = pipeline.make_mock_client(scene, assets, include_planning=True)
    with pytest.raises(FileExistsError):
        experiment(scene, assets, output, client=client)
    assert client.calls == []
    assert marker.read_bytes() == b"original-result"
    with pytest.raises(FileExistsError):
        pipeline.run_condition(scene, plan, assets, client, condition="baseline", out_dir=output,
                               project_root=ROOT, font_path=None, render=False)
    assert marker.read_bytes() == b"original-result"


def test_project_root_resolution_does_not_depend_on_current_directory(inputs, tmp_path, monkeypatch):
    scene, assets, _ = inputs
    monkeypatch.chdir(tmp_path)
    block = experiment(scene, assets, tmp_path / "outside-cwd")
    assert block["status"] == "completed"
    assert all(row["validation_status"] == "passed" for row in block["runs"])


def http_envelope(response, *, cost=0.001):
    usage = {"prompt_tokens": 100, "completion_tokens": 20}
    if cost is not None:
        usage["cost"] = cost
    return io.BytesIO(json.dumps({"id": "synthetic-generation", "model": "test/offline-model",
        "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(response)}}],
        "usage": usage}).encode("utf-8"))


def openrouter_fixture(monkeypatch, responses):
    send = Mock(side_effect=responses)
    monkeypatch.setattr("moodcut.client.build_opener", Mock(return_value=Mock(open=send)))
    client = OpenRouterClient(api_key="synthetic-test-key", model="test/offline-model",
                               input_price_per_million=1, output_price_per_million=2,
                               allow_paid=True, max_cost_usd=10)
    return client, send


def test_openrouter_mocked_nine_http_envelopes_account_once_per_phase(inputs, tmp_path, monkeypatch):
    scene, assets, _ = inputs
    fake = pipeline.make_mock_client(scene, assets, include_planning=True)
    envelopes = [http_envelope(response) for response in list(fake._responses)]
    client, send = openrouter_fixture(monkeypatch, envelopes)
    block = experiment(scene, assets, tmp_path / "http-fixture", client=client)
    assert block["status"] == "completed"
    assert send.call_count == 9
    assert block["planning"]["calls"] == 3
    assert block["planning"]["provider_cost_usd"] == pytest.approx(0.003)
    assert [row["calls"] for row in block["runs"]] == [0, 3, 3]
    assert [row["provider_cost_usd"] for row in block["runs"]] == pytest.approx([0, 0.003, 0.003])
    assert block["planning"]["input_tokens"] == 300
    assert sum(row["input_tokens"] for row in block["runs"]) == 600
    assert client.spent_usd == pytest.approx(0.009)
    assert block["mock"] is False  # Client mode only; fixture provenance remains development.
    assert block["source_kind"] == "development"


def test_unknown_http_charge_blocks_later_calls_and_is_not_zeroed(inputs, tmp_path, monkeypatch):
    scene, assets, plan = inputs
    client, send = openrouter_fixture(monkeypatch, [http_envelope({"unexpected": "critique"}, cost=None)])
    first = pipeline.run_condition(scene, plan, assets, client, condition="moodcut", render=False,
                                    out_dir=tmp_path / "first", project_root=ROOT, font_path=None)
    assert first["review_status"] == "review_failed"
    assert first["calls"] == 1 and first["provider_cost_usd"] is None
    assert first["input_tokens"] == 100 and first["output_tokens"] == 20
    second = pipeline.run_condition(scene, plan, assets, client, condition="generic_review", render=False,
                                     out_dir=tmp_path / "second", project_root=ROOT, font_path=None)
    assert second["review_status"] == "review_failed"
    assert second["failure_kind"] == "budget"
    assert second["calls"] == 0
    assert send.call_count == 1
    assert client.spent_usd is None


def test_invalid_http_completion_preserves_known_failed_attempt_fee(inputs, tmp_path, monkeypatch):
    scene, assets, plan = inputs
    invalid = io.BytesIO(json.dumps({"choices": [], "usage": {
        "prompt_tokens": 25, "completion_tokens": 5, "cost": 0.002}}).encode())
    client, send = openrouter_fixture(monkeypatch, [invalid])
    row = pipeline.run_condition(scene, plan, assets, client, condition="moodcut", render=False,
                                  out_dir=tmp_path / "failed", project_root=ROOT, font_path=None)
    assert row["run_status"] == "failed"
    assert row["calls"] == 1
    assert row["provider_cost_usd"] == pytest.approx(0.002)
    assert row["estimated_cost_usd"] == pytest.approx(0.000035)
    assert row["call_records"][0]["status"] == "invalid_response"
    assert send.call_count == 1
