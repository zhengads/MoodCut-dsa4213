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


@pytest.fixture
def generated_inputs(monkeypatch):
    """Existing hand-written contract fixture, not generated media or a dataset."""
    def no_network(*args, **kwargs):
        pytest.fail("Generated pipeline tests must not access the network")
    monkeypatch.setattr("socket.socket.connect", no_network)
    monkeypatch.setattr("socket.create_connection", no_network)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    data = pipeline.read_json(ROOT / "tests/fixtures/generated_contract.json")
    return data, pipeline.read_json(ROOT / "tests/fixtures/assets.json")


def generated_experiment(data, manifest, output, client, **kwargs):
    return experiment(data["scene"], manifest, output, client=client,
                      output_mode="generated", generation_settings=data["settings"],
                      template_sha256=data["template_sha256"], **kwargs)


def generated_dependencies(monkeypatch, data, *, revise=None):
    """Explicit P2/P3 doubles until their generated-mode APIs are implemented.

    The pipeline, validators, identity helpers, persistence and accounting run
    normally. FakeClient supplies labeled software responses without networking.
    """
    initial = deepcopy(data["initial_plan"])
    plan_calls = []
    review_calls = []

    def plan(scene, manifest, client, *, project_root, output_mode):
        assert output_mode == "generated"
        plan_calls.append((scene, manifest))
        response = client.complete_json(stage="fixture_planning", system="P2 software double",
                                        user="{}", max_output_tokens=100)
        return {"plan": deepcopy(initial), "raw_responses": {"software_double": response}}

    def review(scene, plan, manifest, client, *, mode, project_root, output_mode):
        assert output_mode == "generated"
        review_calls.append((mode, scene, plan, manifest))
        response = client.complete_json(stage="fixture_review", system="P3 software double",
                                        user="{}", max_output_tokens=100)
        final = deepcopy(data["condition_plans"][mode])
        status = "applied"
        if revise is not None:
            final, status = revise(mode, scene, plan, manifest, final)
        return {"plan": final, "status": status, "errors": [], "software_double": response}

    monkeypatch.setattr(pipeline, "make_plan_with_trace", plan)
    monkeypatch.setattr(pipeline, "review_and_revise", review)
    return plan_calls, review_calls


def test_generated_one_plan_shared_hash_and_prepared_records(generated_inputs, tmp_path, monkeypatch):
    data, manifest = generated_inputs
    original = deepcopy((data, manifest))
    plan_calls, review_calls = generated_dependencies(monkeypatch, data)
    client = FakeClient([{}, {}, {}])
    block = generated_experiment(data, manifest, tmp_path / "generated", client)
    assert block["status"] == "prepared"
    assert len(plan_calls) == 1 and len(review_calls) == 2
    assert block["planning"]["calls"] == 1
    assert [r["review_calls"] for r in block["runs"]] == [0, 1, 1]
    assert block["shared_generation_sha256"] == data["shared_generation_sha256"]
    assert len({r["initial_plan_sha256"] for r in block["runs"]}) == 1
    assert {r["shared_generation_sha256"] for r in block["runs"]} == {data["shared_generation_sha256"]}
    assert len({r["final_plan_sha256"] for r in block["runs"]}) == 3
    for record in block["runs"]:
        assert record["schema_version"] == "1.1" and record["output_mode"] == "generated"
        assert record["run_status"] == "prepared"
        assert record["render_status"] == "not_started" and record["video_path"] is None
        assert record["generation_status"] == "not_started" and record["generation_jobs"] == []
        assert record["generation_posts"] == record["video_get_calls"] == record["real_http_calls"] == 0
        assert record["comparison_status"] == "not_checked"
        assert record["video_model_id"] == data["settings"]["model"]
        directory = tmp_path / "generated" / record["condition"]
        assert pipeline.read_json(directory / "run.json") == record
        assert pipeline.read_json(directory / "generation_settings.json") == data["settings"]
        assert pipeline.json_hash(pipeline.read_json(directory / "initial.json")) == record["initial_plan_sha256"]
        assert pipeline.json_hash(pipeline.read_json(directory / "final.json")) == record["final_plan_sha256"]
        assert pipeline.shared_generation_sha256(
            pipeline.read_json(directory / "scene.json"), pipeline.read_json(directory / "final.json"),
            pipeline.read_json(directory / "assets.json"), pipeline.read_json(directory / "generation_settings.json"),
            template_sha256=record["prompt_hashes"]["video_template"]) == record["shared_generation_sha256"]
    assert (data, manifest) == original


def generated_condition(data, manifest, output, client=None, **overrides):
    kwargs = dict(condition="moodcut", out_dir=output, project_root=ROOT, font_path=None,
                  output_mode="generated", generation_settings=data["settings"],
                  template_sha256=data["template_sha256"],
                  expected_initial_plan_sha256=pipeline.json_hash(data["initial_plan"]),
                  expected_shared_generation_sha256=data["shared_generation_sha256"])
    kwargs.update(overrides)
    return pipeline.run_condition(data["scene"], data["initial_plan"], manifest,
                                  client if client is not None else FakeClient([]), **kwargs)


@pytest.mark.parametrize("field", ["scene_direction", "direction", "narration", "duration_s",
                                 "visuals", "shot_order", "shot_count", "plan_extension", "shot_extension"])
def test_generated_rejects_all_non_dialogue_changes(generated_inputs, tmp_path, monkeypatch, field):
    data, manifest = generated_inputs
    def revise(mode, scene, initial, assets, final):
        if mode == "generic_review":
            if field == "scene_direction":
                final[field] += " altered"
            elif field in ("direction", "narration"):
                final["shots"][0][field] += " altered"
            elif field == "duration_s":
                final["shots"][0][field] = 7  # Structurally valid but forbidden.
            elif field == "visuals":
                final["shots"][0][field].reverse()
            elif field == "shot_order":
                final["shots"].reverse()
            elif field == "shot_count":
                extra = deepcopy(final["shots"][0])
                extra["shot_id"] = "s4"
                final["shots"].append(extra)
            elif field == "plan_extension":
                final["future_control"] = {"camera": "altered"}
            else:
                final["shots"][0]["future_control"] = {"camera": "altered"}
        return final, "applied"
    generated_dependencies(monkeypatch, data, revise=revise)
    block = generated_experiment(data, manifest, tmp_path / field, FakeClient([{}, {}, {}]))
    baseline, rejected, moodcut = block["runs"]
    assert block["status"] == "failed"
    assert baseline["run_status"] == moodcut["run_status"] == "prepared"
    assert rejected["run_status"] == "failed" and rejected["comparison_status"] == "ineligible"
    assert rejected["validation_status"] == "passed"  # Structural validity is not permission.
    assert rejected["failure_kind"] == "shared_inputs"
    assert any("non-dialogue" in error for error in rejected["comparison_errors"])
    assert rejected["final_plan_sha256"] != baseline["final_plan_sha256"]
    assert pipeline.read_json(tmp_path / field / "generic_review/final.json") != data["initial_plan"]
    assert rejected["review_calls"] == 1 and rejected["generation_posts"] == 0


@pytest.mark.parametrize("kind", ["model", "seed", "style", "sound", "voice", "resolution", "template",
                                "source_url", "asset_sha256", "scene", "initial_dialogue",
                                "expected_initial", "expected_shared", "missing_expected"])
def test_generated_frozen_input_tampering_fails_before_review(generated_inputs, tmp_path, monkeypatch, kind):
    data, manifest = generated_inputs
    changed = deepcopy(data)
    settings = changed["settings"]
    kwargs = {"generation_settings": settings}
    if kind in ("model", "style", "sound", "resolution"):
        settings[kind] += "-changed"
    elif kind == "seed":
        settings["seed"] += 1
    elif kind == "voice":
        settings["characters"][0]["voice"] += "-changed"
    elif kind == "template":
        kwargs["template_sha256"] = "a" * 64
    elif kind == "source_url":
        manifest["assets"][0]["source_url"] = "https://example.invalid/changed.png"
    elif kind == "asset_sha256":
        manifest["assets"][0]["sha256"] = "a" * 64
    elif kind == "scene":
        changed["scene"]["story"] += " changed"
    elif kind == "initial_dialogue":
        changed["initial_plan"]["shots"][0]["dialogue"][0]["text"] += " changed"
    elif kind == "expected_initial":
        kwargs["expected_initial_plan_sha256"] = "a" * 64
    elif kind == "expected_shared":
        kwargs["expected_shared_generation_sha256"] = "a" * 64
    else:
        kwargs["expected_shared_generation_sha256"] = None
    # Bind to the original block identity, including when only initial dialogue changes.
    kwargs.setdefault("expected_initial_plan_sha256", pipeline.json_hash(data["initial_plan"]))
    generated_dependencies(monkeypatch, data)
    client = FakeClient([{}])
    row = generated_condition(changed, manifest, tmp_path / kind, client, **kwargs)
    assert row["run_status"] == "failed" and row["comparison_status"] == "ineligible"
    assert row["review_calls"] == row["calls"] == row["real_http_calls"] == 0
    assert row["comparison_errors"] and client.calls == []


def test_generated_reviews_receive_independent_snapshots(generated_inputs, tmp_path, monkeypatch):
    data, manifest = generated_inputs
    original = deepcopy((data, manifest))
    def revise(mode, scene, plan, assets, final):
        if mode == "generic_review":
            scene["story"] = "attempt to contaminate later condition"
            assets["assets"][0]["path"] = "missing.png"
            plan["shots"][0]["direction"] = "attempt to contaminate baseline"
            return plan, "applied"
        assert scene == data["scene"] and assets == manifest and plan == data["initial_plan"]
        return final, "applied"
    _, seen = generated_dependencies(monkeypatch, data, revise=revise)
    block = generated_experiment(data, manifest, tmp_path / "isolated", FakeClient([{}, {}, {}]))
    assert block["runs"][1]["run_status"] == "failed"
    assert block["runs"][2]["run_status"] == "prepared"
    assert all(seen[0][i] is not seen[1][i] for i in (1, 2, 3))
    for condition in pipeline.CONDITIONS:
        assert pipeline.read_json(tmp_path / "isolated" / condition / "initial.json") == data["initial_plan"]
    assert (data, manifest) == original


@pytest.mark.parametrize("status,changed,prepared", [
    ("unchanged", False, True), ("unchanged", True, False),
    ("rejected", False, False), ("review_failed", False, False),
    ("no_changes", False, False), ("not_started", False, False),
])
def test_generated_unchanged_requires_exact_plan_and_valid_status(generated_inputs, tmp_path, monkeypatch,
                                                                 status, changed, prepared):
    data, manifest = generated_inputs
    def revise(mode, scene, initial, assets, final):
        return (final if changed else initial), status
    generated_dependencies(monkeypatch, data, revise=revise)
    row = generated_condition(data, manifest, tmp_path / "status", FakeClient([{}]))
    assert row["run_status"] == ("prepared" if prepared else "failed")
    assert row["review_status"] == status
    assert row["comparison_status"] == ("not_checked" if prepared else "ineligible")
    assert row["review_calls"] == 1
    assert row["render_status"] == "not_started"


def test_generated_never_uses_animatic_renderer_even_when_render_true(generated_inputs, tmp_path, monkeypatch):
    data, manifest = generated_inputs
    monkeypatch.setattr(pipeline, "render_plan", lambda *a, **k: pytest.fail("No animatic rendering"))
    row = generated_condition(data, manifest, tmp_path / "no-render", condition="baseline", render=True)
    assert row["run_status"] == "prepared" and row["generation_status"] == "not_started"
    assert row["render_status"] == "not_started" and row["video_path"] is None


def test_generated_unsupported_planner_signature_fails_without_downgrade(generated_inputs, tmp_path, monkeypatch):
    data, manifest = generated_inputs
    def legacy_only(scene, manifest, client, *, project_root):
        pytest.fail("Must not retry a legacy-only planner without output_mode")
    monkeypatch.setattr(pipeline, "make_plan_with_trace", legacy_only)
    client = FakeClient([])
    block = generated_experiment(data, manifest, tmp_path / "dependency", client)
    assert block["status"] == "failed" and block["planning"]["status"] == "failed"
    assert any("output_mode" in error for error in block["planning"]["errors"])
    assert client.calls == []
    assert block["shared_generation_sha256"] is None
    for row in block["runs"]:
        assert row["run_status"] == "failed" and row["comparison_status"] == "ineligible"
        assert row["initial_plan_sha256"] is None and row["calls"] == 0
        assert pipeline.read_json(tmp_path / "dependency" / row["condition"] / "run.json") == row


def test_generated_unsupported_reviewer_signature_fails_without_legacy_fallback(generated_inputs, tmp_path, monkeypatch):
    data, manifest = generated_inputs
    generated_dependencies(monkeypatch, data)
    def legacy_only(scene, initial, manifest, client, *, mode, project_root):
        pytest.fail("Must not retry a legacy-only reviewer without output_mode")
    monkeypatch.setattr(pipeline, "review_and_revise", legacy_only)
    block = generated_experiment(data, manifest, tmp_path / "review-dependency", FakeClient([{}]))
    assert block["runs"][0]["run_status"] == "prepared"
    assert all(r["run_status"] == "failed" and r["review_calls"] == 0 for r in block["runs"][1:])
    assert all(any("output_mode" in e for e in r["errors"]) for r in block["runs"][1:])


def test_generated_cache_reuse_preserves_identity_without_replanning(generated_inputs, tmp_path, monkeypatch):
    data, manifest = generated_inputs
    plans, _ = generated_dependencies(monkeypatch, data)
    cache = tmp_path / "cache"
    first = generated_experiment(data, manifest, tmp_path / "first", FakeClient([{}, {}, {}]), cache_dir=cache)
    stored = next(cache.glob("*.json")).read_bytes()
    second = generated_experiment(data, manifest, tmp_path / "second", FakeClient([{}, {}]), cache_dir=cache)
    assert len(plans) == 1
    assert first["status"] == second["status"] == "prepared"
    assert second["planning"]["cache_hit"] and second["planning"]["calls"] == 0
    assert first["initial_plan_sha256"] == second["initial_plan_sha256"]
    assert first["shared_generation_sha256"] == second["shared_generation_sha256"]
    assert next(cache.glob("*.json")).read_bytes() == stored
    assert not list(cache.glob("*.lock"))


def test_generated_corrupt_shared_cache_retained_without_replanning(generated_inputs, tmp_path, monkeypatch):
    data, manifest = generated_inputs
    plans, _ = generated_dependencies(monkeypatch, data)
    cache = tmp_path / "cache"
    generated_experiment(data, manifest, tmp_path / "first", FakeClient([{}, {}, {}]), cache_dir=cache)
    path = next(cache.glob("*.json"))
    saved = pipeline.read_json(path)
    saved["shared_generation_sha256"] = "a" * 64
    path.write_text(json.dumps(saved), encoding="utf-8")
    corrupted = path.read_bytes()
    client = FakeClient([])
    block = generated_experiment(data, manifest, tmp_path / "corrupt", client, cache_dir=cache)
    assert len(plans) == 1 and client.calls == []
    assert block["status"] == "failed" and not block["planning"]["cache_hit"]
    assert any("Cached shared" in e for e in block["planning"]["errors"])
    assert all(r["run_status"] == "failed" and r["comparison_status"] == "ineligible" for r in block["runs"])
    assert path.read_bytes() == corrupted and not list(cache.glob("*.lock"))


@pytest.mark.parametrize("dimension", ["model", "seed", "template", "replicate"])
def test_generated_cache_identity_binds_settings_and_template(generated_inputs, tmp_path, monkeypatch, dimension):
    data, manifest = generated_inputs
    plans, _ = generated_dependencies(monkeypatch, data)
    cache = tmp_path / "cache"
    first = generated_experiment(data, manifest, tmp_path / "first", FakeClient([{}, {}, {}]), cache_dir=cache)
    options = {}
    if dimension == "replicate":
        options["replicate"] = 2
    elif dimension == "template":
        data["template_sha256"] = "a" * 64
    elif dimension == "seed":
        data["settings"]["seed"] += 1
    else:
        data["settings"]["model"] += "-changed"
    second = generated_experiment(data, manifest, tmp_path / "second", FakeClient([{}, {}, {}]),
                                  cache_dir=cache, **options)
    assert len(plans) == 2 and second["status"] == "prepared"
    assert first["planning"]["cache_key"] != second["planning"]["cache_key"]
    assert not second["planning"]["cache_hit"]
    assert len(list(cache.glob("*.json"))) == 2


def test_generated_snapshot_includes_settings_before_review(generated_inputs, tmp_path, monkeypatch):
    data, manifest = generated_inputs
    settings = deepcopy(data["settings"])
    def revise(mode, scene, initial, assets, final):
        # A caller mutating its own object cannot change another condition's input.
        if mode == "generic_review":
            data["settings"]["model"] = "caller/mutated"
        return final, "applied"
    generated_dependencies(monkeypatch, data, revise=revise)
    block = generated_experiment(data, manifest, tmp_path / "settings-snapshot", FakeClient([{}, {}, {}]))
    assert block["status"] == "prepared" and block["generation_settings"] == settings
    assert {r["shared_generation_sha256"] for r in block["runs"]} == {data["shared_generation_sha256"]}
    assert all(r["video_model_id"] == settings["model"] for r in block["runs"])


@pytest.mark.parametrize("failure", ["exception", "invalid_plan"])
def test_generated_planning_failure_preserves_attempt_and_three_failed_records(generated_inputs, tmp_path,
                                                                               monkeypatch, failure):
    data, manifest = generated_inputs
    def failed_plan(scene, manifest, client, *, project_root, output_mode):
        client.complete_json(stage="fixture_planning", system="P2 software double", user="{}", max_output_tokens=100)
        if failure == "exception":
            raise ValueError("Software planning failure")
        candidate = deepcopy(data["initial_plan"])
        candidate["shots"][0]["duration_s"] = 100
        return {"plan": candidate, "raw_responses": {"invalid_plan": candidate}}
    monkeypatch.setattr(pipeline, "make_plan_with_trace", failed_plan)
    client = FakeClient([{}])
    block = generated_experiment(data, manifest, tmp_path / failure, client)
    assert block["status"] == "failed" and block["planning"]["calls"] == 1
    assert block["shared_generation_sha256"] is None
    assert len(client.calls) == 1 and all(r["review_calls"] == 0 for r in block["runs"])
    assert all(r["run_status"] == "failed" and r["comparison_status"] == "ineligible" for r in block["runs"])
    if failure == "invalid_plan":
        assert block["planning"]["raw_responses"]["invalid_plan"]["shots"][0]["duration_s"] == 100


@pytest.mark.parametrize("charge", [0.002, None])
def test_generated_failed_review_preserves_costs_and_unknown_charge_stops_later_calls(
        generated_inputs, tmp_path, monkeypatch, charge):
    data, manifest = generated_inputs
    def revise(mode, scene, initial, assets, final):
        return initial, "review_failed"
    generated_dependencies(monkeypatch, data, revise=revise)
    envelopes = [http_envelope({}, cost=0.001), http_envelope({}, cost=charge)]
    if charge is not None:
        envelopes.append(http_envelope({}, cost=charge))
    client, send = openrouter_fixture(monkeypatch, envelopes)
    block = generated_experiment(data, manifest, tmp_path / "accounting", client)
    baseline, generic, moodcut = block["runs"]
    assert block["status"] == "failed" and baseline["run_status"] == "prepared"
    assert block["planning"]["calls"] == 1 and block["planning"]["provider_cost_usd"] == 0.001
    assert generic["review_calls"] == 1 and generic["run_status"] == "failed"
    assert generic["provider_cost_usd"] == charge
    assert generic["estimated_cost_usd"] == pytest.approx(0.00014)
    assert generic["comparison_status"] == moodcut["comparison_status"] == "ineligible"
    assert generic["input_tokens"] == 100
    assert all(r["generation_posts"] == r["video_get_calls"] == 0 for r in block["runs"])
    if charge is None:
        assert send.call_count == 2 and client.spent_usd is None
        assert moodcut["review_calls"] == 0 and moodcut["failure_kind"] == "budget"
    else:
        assert send.call_count == 3 and moodcut["provider_cost_usd"] == charge
    assert pipeline.read_json(tmp_path / "accounting/block.json") == block


@pytest.mark.parametrize("mode", ["unknown", None, [], {}])
def test_pipeline_rejects_unknown_mode_before_output_or_calls(inputs, tmp_path, mode):
    scene, manifest, plan = inputs
    client = FakeClient([])
    with pytest.raises(ValueError, match="output_mode"):
        experiment(scene, manifest, tmp_path / "mode", client=client, output_mode=mode)
    assert not (tmp_path / "mode").exists() and client.calls == []


def test_generated_configuration_requires_explicit_mode_and_settings(inputs, generated_inputs, tmp_path):
    scene, manifest, plan = inputs
    data, _ = generated_inputs
    client = FakeClient([])
    with pytest.raises(ValueError, match="explicit generated"):
        experiment(scene, manifest, tmp_path / "implicit", client=client, generation_settings=data["settings"])
    with pytest.raises(ValueError, match="requires generation_settings"):
        experiment(data["scene"], manifest, tmp_path / "missing", client=client, output_mode="generated")
    with pytest.raises(ValueError, match="explicit generated"):
        pipeline.run_condition(scene, plan, manifest, client, condition="baseline", out_dir=tmp_path / "identity",
                               project_root=ROOT, font_path=None, expected_shared_generation_sha256="a" * 64)
    assert client.calls == [] and not any(tmp_path.iterdir())


def test_generated_caught_review_budget_error_keeps_budget_failure_kind(generated_inputs, tmp_path, monkeypatch):
    data, manifest = generated_inputs
    def review(scene, initial, assets, client, *, mode, project_root, output_mode):
        return {"plan": initial, "status": "review_failed", "errors": ["BudgetError: software fixture"]}
    monkeypatch.setattr(pipeline, "review_and_revise", review)
    row = generated_condition(data, manifest, tmp_path / "budget")
    assert row["failure_kind"] == "budget" and row["run_status"] == "failed"
    assert row["review_calls"] == row["real_http_calls"] == 0
    assert row["comparison_status"] == "ineligible"


def test_generated_rechecks_actual_asset_bytes_after_review(generated_inputs, tmp_path, monkeypatch):
    import shutil
    data, manifest = generated_inputs
    shutil.copytree(ROOT / "tests/fixtures", tmp_path / "tests/fixtures")
    asset_path = tmp_path / manifest["assets"][0]["path"]
    def revise(mode, scene, initial, assets, final):
        with asset_path.open("ab") as stream:
            stream.write(b"software tamper fixture")
        return final, "applied"
    generated_dependencies(monkeypatch, data, revise=revise)
    row = generated_condition(data, manifest, tmp_path / "asset-tamper", FakeClient([{}]), project_root=tmp_path)
    assert row["run_status"] == "failed" and row["validation_status"] == "failed"
    assert row["comparison_status"] == "ineligible"
    assert any("SHA-256 mismatch" in error for error in row["comparison_errors"])
    assert row["final_plan_sha256"] and row["generation_posts"] == 0
