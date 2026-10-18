"""Staged planning and rejection tests using queued software fixtures only."""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from moodcut.client import FakeClient
from moodcut.planner import (PlanningError, get_planning_prompt_hashes, make_plan,
                             make_plan_with_trace, normalize_plan)


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def planning_data():
    scene, manifest, plan = [json.loads((ROOT / "tests/fixtures" / name).read_text(encoding="utf-8"))
                             for name in ("scene.json", "assets.json", "plan.json")]
    responses = [{"scene_id": scene["scene_id"], "tone": scene["tone"],
                  "beat_order": [b["id"] for b in scene["beats"]], "approach": "Restrained questioning."},
                 {"scene_id": scene["scene_id"], "segments": [
                     {"beat_ids": [b["id"]], "description": b["description"]} for b in scene["beats"]]}, plan]
    return scene, manifest, plan, responses


def test_three_stages_validate_and_preserve_inputs_and_trace(planning_data):
    scene, manifest, plan, responses = planning_data
    before = deepcopy((scene, manifest, responses))
    client = FakeClient(responses)
    result = make_plan_with_trace(scene, manifest, client, project_root=ROOT)
    assert result["plan"] == plan
    assert [call["stage"] for call in client.calls] == ["director", "scene", "shot"]
    assert result["raw_responses"] == dict(zip(("director", "scene", "shot"), responses))
    assert result["prompt_hashes"] == get_planning_prompt_hashes()
    assert all(len(value) == 64 for value in result["prompt_hashes"].values())
    assert (scene, manifest, responses) == before
    payload = json.loads(client.calls[2]["user"])
    assert payload["scene"] == scene and len(payload["prior_responses"]) == 2


@pytest.mark.parametrize("wrapper", ["direct", "shots", "plan", "scenes"])
def test_equivalent_envelopes_normalize(planning_data, wrapper):
    scene, manifest, plan, responses = planning_data
    responses[2] = {"direct": plan, "shots": {"shots": plan["shots"]},
                    "plan": {"plan": plan}, "scenes": {"scenes": [plan]}}[wrapper]
    assert make_plan(scene, manifest, FakeClient(responses), project_root=ROOT) == plan


@pytest.mark.parametrize("field,value,error", [("beat_ids", ["unknown"], "unknown beat"),
    ("duration_s", 100, "duration"), ("visuals", [{"asset_id": "unknown", "crop": "full"}], "asset_id"),
    ("dialogue", [{"character_id": "unknown", "text": "Hi"}], "character_id")])
def test_invalid_final_plan_preserves_raw_and_never_retries(planning_data, field, value, error):
    scene, manifest, plan, responses = planning_data
    responses[2]["shots"][0][field] = value
    client = FakeClient(responses)
    with pytest.raises(PlanningError, match=error) as captured:
        make_plan(scene, manifest, client, project_root=ROOT)
    assert len(client.calls) == 3 and captured.value.stage == "shot"
    assert captured.value.raw_responses["shot"] == responses[2]


def test_missing_beat_is_not_silently_removed(planning_data):
    scene, manifest, plan, responses = planning_data
    responses[2]["shots"].pop()
    with pytest.raises(PlanningError, match="missing beat coverage"):
        make_plan(scene, manifest, FakeClient(responses), project_root=ROOT)


@pytest.mark.parametrize("stage", [0, 1])
def test_invalid_intermediate_stops_before_next_call(planning_data, stage):
    scene, manifest, plan, responses = planning_data
    responses[stage]["scene_id"] = "other"
    client = FakeClient(responses)
    with pytest.raises(PlanningError, match="scene_id") as captured:
        make_plan(scene, manifest, client, project_root=ROOT)
    assert len(client.calls) == stage + 1
    assert len(captured.value.raw_responses) == stage + 1


def test_local_invalid_assets_cost_zero_calls(planning_data):
    scene, manifest, plan, responses = planning_data
    manifest["assets"][0]["sha256"] = "0" * 64
    client = FakeClient(responses)
    with pytest.raises(PlanningError, match="SHA-256"):
        make_plan(scene, manifest, client, project_root=ROOT)
    assert client.calls == []


def test_client_failure_keeps_prior_outputs_without_retry(planning_data):
    scene, manifest, plan, responses = planning_data
    client = FakeClient(responses[:1])
    with pytest.raises(PlanningError) as captured:
        make_plan(scene, manifest, client, project_root=ROOT)
    assert captured.value.stage == "scene"
    assert set(captured.value.raw_responses) == {"director"}
    assert len(client.calls) == 2


def test_normalizer_does_not_truncate_scenes_or_override_metadata(planning_data):
    scene, manifest, plan, responses = planning_data
    with pytest.raises(ValueError, match="exactly one"):
        normalize_plan({"scenes": [plan, plan]}, scene)
    with pytest.raises(ValueError, match="conflicting"):
        normalize_plan({"scene_id": "wrong", "scenes": [plan]}, scene)


@pytest.fixture(params=("letter", "umbrella"))
def generated_planning_data(request, monkeypatch):
    """Hand-authored software responses, not model outputs or a new dataset."""
    data = json.loads((ROOT / "tests/fixtures/generated_contract.json").read_text(encoding="utf-8"))
    scene, plan, settings = deepcopy((data["scene"], data["initial_plan"], data["settings"]))
    manifest = json.loads((ROOT / "tests/fixtures/assets.json").read_text(encoding="utf-8"))
    if request.param == "umbrella":
        scene.update(scene_id="software_bus_stop", story="Noor waits at a bus stop. Mika returns an umbrella; Noor takes it and waits with Mika.",
            characters=[{"id": "waiting", "name": "Noor"}, {"id": "returning", "name": "Mika"}],
            beats=[{"id": "return", "description": "Mika returns the borrowed umbrella to Noor."},
                   {"id": "wait", "description": "Noor takes it and both wait at the bus stop."}],
            min_duration_s=8, max_duration_s=12, min_shot_duration_s=4, max_shot_duration_s=6,
            provenance={"kind": "temporary_software_fixture", "adaptation": "Hand-authored non-letter software test only; not experimental data."})
        plan.update(scene_id=scene["scene_id"], scene_direction="Two people in a bus shelter; preserve their geography.",
                    shots=plan["shots"][:2])
        for shot, beat, speaker, action in zip(plan["shots"], scene["beats"], ("returning", "waiting"),
                ("Mika returns the umbrella to Noor, medium two-shot.", "Noor takes it; both wait, fixed wide shot.")):
            shot.update(shot_id="software_" + beat["id"], beat_ids=[beat["id"]], duration_s=5, direction=action,
                        narration=beat["description"], dialogue=[{"character_id": speaker, "text": "Here we are."}])
        mapping = {"a": "waiting", "b": "returning"}
        for asset in manifest["assets"]:
            asset["character_id"] = mapping[asset["character_id"]]
        for character in settings["characters"]:
            character["id"] = mapping[character["id"]]
    responses = [{"scene_id": scene["scene_id"], "tone": scene["tone"],
                  "beat_order": [b["id"] for b in scene["beats"]], "approach": "Shared software production intent."},
                 {"scene_id": scene["scene_id"], "scene_direction": plan["scene_direction"], "segments": [
                    {"beat_ids": deepcopy(shot["beat_ids"]), "description": shot["narration"],
                     "direction": shot["direction"], "duration_s": shot["duration_s"]} for shot in plan["shots"]]}, plan]
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr("socket.socket.connect", lambda *a, **k: pytest.fail("No real network in generated planning tests"))
    return scene, manifest, plan, responses, settings, data["template_sha256"]


def test_generated_stages_use_input_timing_and_leave_sources_unchanged(generated_planning_data):
    scene, manifest, plan, responses, _, _ = generated_planning_data
    before = deepcopy((scene, manifest, responses))
    client = FakeClient(responses)
    traced = make_plan_with_trace(scene, manifest, client, project_root=ROOT, output_mode="generated")
    assert traced["plan"] == plan and sum(s["duration_s"] for s in plan["shots"]) < 60
    assert [c["stage"] for c in client.calls] == ["director", "scene", "shot"]
    assert traced["raw_responses"] == dict(zip(("director", "scene", "shot"), responses))
    assert traced["prompt_hashes"] == get_planning_prompt_hashes(output_mode="generated")
    assert traced["prompt_hashes"] != get_planning_prompt_hashes()
    for call in client.calls:
        payload = json.loads(call["user"])
        assert payload["scene"] == scene and payload["manifest"] == manifest and payload["output_mode"] == "generated"
        assert payload["scene"]["provenance"] == scene["provenance"]
        assert "condition" not in payload
    assert (scene, manifest, responses) == before
    assert make_plan(scene, manifest, FakeClient(responses), project_root=ROOT, output_mode="generated") == plan


@pytest.mark.parametrize("wrapper", ["direct", "plan", "scenes", "split_metadata"])
def test_generated_envelopes_keep_header_and_extensions(generated_planning_data, wrapper):
    scene, manifest, plan, responses, _, _ = generated_planning_data
    plan["software_extension"] = {"preserve": ["source", 1]}
    if wrapper == "plan":
        responses[2] = {"plan": plan}
    elif wrapper == "scenes":
        responses[2] = {"scenes": [plan]}
    elif wrapper == "split_metadata":
        inner = deepcopy(plan)
        version = inner.pop("schema_version")
        responses[2] = {"schema_version": version, "scenes": [inner]}
    assert make_plan(scene, manifest, FakeClient(responses), project_root=ROOT, output_mode="generated") == plan


@pytest.mark.parametrize("change", ["direction", "scene_direction", "float_duration", "shot_duration", "total_duration", "beat_order", "scene_id"])
def test_generated_scene_errors_stop_before_shot_and_keep_raw(generated_planning_data, change):
    scene, manifest, _, responses, _, _ = generated_planning_data
    staged = responses[1]
    if change == "direction":
        staged["segments"][0]["direction"] = " "
    elif change == "scene_direction":
        staged.pop("scene_direction")
    elif change == "float_duration":
        staged["segments"][0]["duration_s"] = float(staged["segments"][0]["duration_s"])
    elif change == "shot_duration":
        staged["segments"][0]["duration_s"] = scene["max_shot_duration_s"] + 1
    elif change == "total_duration":
        scene["min_duration_s"] = scene["max_duration_s"] = 40
    elif change == "beat_order":
        staged["segments"].reverse()
    else:
        staged["scene_id"] = "wrong"
    client = FakeClient(responses)
    with pytest.raises(PlanningError) as caught:
        make_plan(scene, manifest, client, project_root=ROOT, output_mode="generated")
    assert caught.value.stage == "scene" and len(client.calls) == 2
    assert caught.value.raw_responses == dict(zip(("director", "scene"), responses[:2]))


@pytest.mark.parametrize("change", ["direction", "scene_direction", "missing_direction", "missing_scene_direction",
    "retimed", "beat_order", "speaker", "asset", "missing_beat", "old_header", "missing_mode"])
def test_generated_final_errors_are_not_repaired_or_retried(generated_planning_data, change):
    scene, manifest, plan, responses, _, _ = generated_planning_data
    if change == "direction":
        plan["shots"][0]["direction"] += " changed after staging"
    elif change == "scene_direction":
        plan["scene_direction"] += " changed after staging"
    elif change == "missing_direction":
        plan["shots"][0].pop("direction")
    elif change == "missing_scene_direction":
        plan.pop("scene_direction")
    elif change == "retimed":
        plan["shots"][0]["duration_s"] += 1
    elif change == "beat_order":
        plan["shots"].reverse()
    elif change == "speaker":
        plan["shots"][0]["dialogue"] = [{"character_id": "outsider", "text": "Hello"}]
    elif change == "asset":
        plan["shots"][0]["visuals"][0]["asset_id"] = "outsider"
    elif change == "missing_beat":
        plan["shots"].pop()
    elif change == "old_header":
        plan["schema_version"] = "1.0"
    else:
        plan.pop("output_mode")
    client = FakeClient(responses)
    before = deepcopy(responses)
    with pytest.raises(PlanningError) as caught:
        make_plan(scene, manifest, client, project_root=ROOT, output_mode="generated")
    assert caught.value.stage == "shot" and len(client.calls) == 3
    assert caught.value.raw_responses["shot"] == before[2] and responses == before


@pytest.mark.parametrize("output_mode", ["animatic", "unknown", None])
def test_generated_mode_is_explicit_and_invalid_mode_has_zero_calls(generated_planning_data, output_mode):
    scene, manifest, _, responses, _, _ = generated_planning_data
    client = FakeClient(responses)
    with pytest.raises(PlanningError) as caught:
        make_plan(scene, manifest, client, project_root=ROOT, output_mode=output_mode)
    assert caught.value.stage == "preflight" and client.calls == []


def test_generated_partial_result_does_not_acquire_an_implicit_header(generated_planning_data):
    scene, manifest, plan, responses, _, _ = generated_planning_data
    responses[2] = {"shots": plan["shots"], "scene_direction": plan["scene_direction"]}
    client = FakeClient(responses)
    with pytest.raises(PlanningError, match="schema_version") as caught:
        make_plan(scene, manifest, client, project_root=ROOT, output_mode="generated")
    assert "schema_version" not in caught.value.raw_responses["shot"] and len(client.calls) == 3


def test_actual_generated_planner_runs_once_before_three_condition_split(generated_planning_data, tmp_path):
    from moodcut import pipeline
    from moodcut.contracts import CONDITIONS, json_hash, shared_generation_sha256
    scene, manifest, plan, responses, settings, template = generated_planning_data
    empty_reviews = [{"schema_version": "1.0", "scene_id": scene["scene_id"], "mode": mode, "issues": []}
                     for mode in ("generic_review", "moodcut")]
    client = FakeClient([*responses, *empty_reviews])
    cache = tmp_path / "cache"
    output = tmp_path / "shared"
    block = pipeline.run_experiment(scene, manifest, client, out_dir=output, project_root=ROOT,
                                   cache_dir=cache, output_mode="generated", generation_settings=settings,
                                   template_sha256=template)
    assert block["planning"]["status"] == "completed" and block["planning"]["calls"] == 3
    assert block["planning"]["prompt_hashes"] == get_planning_prompt_hashes(output_mode="generated")
    assert [c["stage"] for c in client.calls] == ["director", "scene", "shot", "critique", "critique"]
    assert pipeline.read_json(output / "scene.json") == scene
    assert pipeline.read_json(output / "initial.json") == plan
    shared = shared_generation_sha256(scene, plan, manifest, settings, template_sha256=template)
    for condition, row in zip(CONDITIONS, block["runs"]):
        initial = pipeline.read_json(output / condition / "initial.json")
        assert initial == plan and row["initial_plan_sha256"] == json_hash(plan)
        assert pipeline.read_json(output / condition / "generation_settings.json") == settings
        assert row["shared_generation_sha256"] == shared
    assert block["runs"][0]["run_status"] == "prepared"
    # Actual planner/reviewer business code, software model responses only.
    # Prepared scripts are not generated media or eligible comparisons.
    assert block["status"] == "prepared" and all(row["run_status"] == "prepared" for row in block["runs"])
    assert all(row["review_status"] == "unchanged" for row in block["runs"][1:])
    second_client = FakeClient(empty_reviews)
    cached = pipeline.run_experiment(scene, manifest, second_client, out_dir=tmp_path / "cached", project_root=ROOT,
                                    cache_dir=cache, output_mode="generated", generation_settings=settings,
                                    template_sha256=template)
    assert cached["planning"]["cache_hit"] is True and cached["planning"]["calls"] == 0
    assert [c["stage"] for c in second_client.calls] == ["critique", "critique"]
    assert cached["initial_plan_sha256"] == block["initial_plan_sha256"]


def test_actual_pipeline_keeps_generated_planning_failure_artifacts(generated_planning_data, tmp_path):
    from moodcut import pipeline
    scene, manifest, _, responses, settings, template = generated_planning_data
    responses[1]["segments"][0].pop("direction")
    client = FakeClient(responses)
    output = tmp_path / "failed-planning"
    block = pipeline.run_experiment(scene, manifest, client, out_dir=output, project_root=ROOT,
                                   output_mode="generated", generation_settings=settings, template_sha256=template)
    saved = pipeline.read_json(output / "planning.json")
    assert saved["status"] == "failed" and saved["calls"] == 2 and saved["errors"]
    assert saved["raw_responses"]["scene"] == responses[1]
    assert pipeline.read_json(output / "scene.json") == scene
    assert block["status"] == "failed" and all(r["run_status"] == "failed" for r in block["runs"])
    assert [c["stage"] for c in client.calls] == ["director", "scene"]
