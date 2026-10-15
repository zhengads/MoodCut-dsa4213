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
