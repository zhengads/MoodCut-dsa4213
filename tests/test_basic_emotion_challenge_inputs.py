"""Offline integrity checks for the authored S13-S18 review challenges."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from moodcut.contracts import CONDITIONS, VEMOCLAP_EMOTIONS
from moodcut.client import FakeClient
from moodcut.evaluation import build_assignments
from moodcut import pipeline
from moodcut.validation import validate_scene
from moodcut.video_generation import get_video_template_sha256


ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "docs/studies/six-story-clear-emotions-20261024"
DESIGN_PATH = STUDY / "design-basic-emotion-challenge.json"
INDEX_PATH = STUDY / "inputs/basic-emotion-challenge-index.json"
CONFIG_PATH = ROOT / "configs/basic-emotions-challenge-experiment.json"

SOURCE_ASSETS = {
    "s13_unilateral_decision": "s02_stay_with_me",
    "s14_spoiled_drink": "s01_reunion",
    "s15_cracking_bridge": "s04_exit_closing",
    "s16_approval_arrives": "s06_last_place",
    "s17_old_tree_gone": "s03_footsteps_outside",
    "s18_room_ready": "s05_broken_cooperation",
}

EXPECTED_LANGUAGES = {
    "s13_unilateral_decision": "Mandarin Chinese",
    "s14_spoiled_drink": "English",
    "s15_cracking_bridge": "Mandarin Chinese",
    "s16_approval_arrives": "Mandarin Chinese",
    "s17_old_tree_gone": "English",
    "s18_room_ready": "English",
}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_challenge_design_index_and_config_are_complete():
    design, index, config = read_json(DESIGN_PATH), read_json(INDEX_PATH), read_json(CONFIG_PATH)
    assert design["version"] == index["version"] == "1.0"
    assert tuple(design["emotion_definitions"]) == VEMOCLAP_EMOTIONS
    assert tuple(index["selected_emotions"]) == VEMOCLAP_EMOTIONS
    assert design["duration_s"] == index["duration_s"] == 8
    assert design["planned_condition_entries"] == index["planned_condition_entries"] == 18
    assert design["conditions"] == index["conditions"] == config["conditions"] == list(CONDITIONS)
    assert index["design_path"] == DESIGN_PATH.relative_to(ROOT).as_posix()
    assert index["design_sha256"] == sha256(DESIGN_PATH)
    assert [row["id"] for row in design["stories"]] == list(SOURCE_ASSETS)
    assert [row["story_id"] for row in index["stories"]] == list(SOURCE_ASSETS)
    assert {row["id"]: row["language"] for row in design["stories"]} == EXPECTED_LANGUAGES
    assert {row["story_id"]: row["language"] for row in index["stories"]} == EXPECTED_LANGUAGES
    assert config["scenes"] == [row["scene_path"] for row in index["stories"]]
    assert len({character["character_id"]
                for story in design["stories"] for character in story["cast"]}) == 12
    assert design["challenge_policy"]["draft_status"].startswith(
        "The draft is an authored stress-test fixture")
    assert index["authored_drafts_are_model_outputs"] is False


def test_challenge_scenes_drafts_and_reused_assets_validate_offline():
    index = read_json(INDEX_PATH)
    fixture_assets = read_json(ROOT / "tests/fixtures/assets.json")["assets"]
    for row in index["stories"]:
        story_id = row["story_id"]
        scene_path = ROOT / row["scene_path"]
        assets_path = ROOT / row["assets_path"]
        draft_path = ROOT / row["draft_dialogue_path"]
        scene, manifest, draft = map(read_json, (scene_path, assets_path, draft_path))
        source_assets = STUDY / "inputs" / SOURCE_ASSETS[story_id] / "assets.json"

        assert row["scene_sha256"] == sha256(scene_path)
        assert row["assets_sha256"] == sha256(assets_path)
        assert row["draft_dialogue_sha256"] == sha256(draft_path)
        assert assets_path.read_bytes() == source_assets.read_bytes()
        assert scene["schema_version"] == "1.1"
        assert scene["output_mode"] == "generated"
        assert scene["tone"] == row["emotion"] == draft["target_emotion"]
        assert draft["language"] == row["language"] == EXPECTED_LANGUAGES[story_id]
        language_instruction = "只用自然英语" if row["language"] == "English" else "使用自然普通话"
        assert language_instruction in scene["story"]
        assert "台词不直接念出anger、disgust、fear、joy、sadness、surprise" in scene["story"]
        assert "参考图只确定角色身份与服装" in scene["story"]
        assert "不引用原电影台词" in scene["story"]
        assert scene["provenance"]["design_path"] == DESIGN_PATH.relative_to(ROOT).as_posix()
        assert scene["provenance"]["design_story_id"] == story_id == draft["story_id"]
        assert scene["provenance"]["draft_dialogue_path"] == row["draft_dialogue_path"]
        assert scene["asset_ids"] == row["asset_ids"]
        assert scene["min_duration_s"] == scene["max_duration_s"] == draft["duration_s"] == 8
        assert scene["min_shot_duration_s"] == scene["max_shot_duration_s"] == 8
        assert len(scene["characters"]) == len(scene["beats"]) == len(draft["dialogue"]) == 2
        assert [line["character_id"] for line in draft["dialogue"]] == row["character_ids"]
        assert all(line["text"].strip() for line in draft["dialogue"])
        assert len(draft["designed_revision_opportunities"]) >= 2
        assert draft["kind"] == "authored_review_challenge_draft_not_model_output"
        assert "Do not present" in draft["usage_limit"]

        local_manifest = deepcopy(manifest)
        for target, fixture in zip(local_manifest["assets"], fixture_assets):
            for field in ("path", "width", "height", "sha256", "allowed_crops"):
                target[field] = deepcopy(fixture[field])
        assert validate_scene(
            scene, local_manifest, project_root=ROOT, output_mode="generated") == []


def test_challenge_fixed_emotions_produce_eighteen_offline_assignments():
    config = read_json(CONFIG_PATH)
    scenes = [read_json(ROOT / path) for path in config["scenes"]]
    assignments = build_assignments(
        scenes, replicates=config["replicates"], tones=None,
        conditions=config["conditions"],
    )
    assert len(assignments) == 18
    assert {(row["scene_id"], row["tone"]) for row in assignments} == {
        (scene["scene_id"], scene["tone"]) for scene in scenes
    }
    assert {row["condition"] for row in assignments} == set(CONDITIONS)


def _s13_generated_case():
    scene = read_json(STUDY / "inputs/s13_unilateral_decision/scene.json")
    manifest = read_json(STUDY / "inputs/s13_unilateral_decision/assets.json")
    fixture_assets = read_json(ROOT / "tests/fixtures/assets.json")["assets"]
    for target, fixture in zip(manifest["assets"], fixture_assets):
        for field in ("path", "width", "height", "sha256", "allowed_crops"):
            target[field] = deepcopy(fixture[field])
    dialogue = [
        {"character_id": "despicableme4_lucy", "text": "Planner-generated anger."},
        {"character_id": "despicableme4_gru", "text": "Planner-generated defence."},
    ]
    plan = {
        "schema_version": "1.1", "output_mode": "generated",
        "scene_id": scene["scene_id"], "tone": scene["tone"],
        "scene_direction": "Lucy and Gru remain seated opposite each other in one quiet room.",
        "shots": [{
            "shot_id": "s1", "beat_ids": ["b1", "b2"], "duration_s": 8,
            "visuals": [{"asset_id": asset_id, "crop": "full"}
                        for asset_id in scene["asset_ids"]],
            "dialogue": dialogue, "narration": "",
            "direction": "A steady medium shot holds both characters during the disagreement.",
        }],
    }
    draft = read_json(STUDY / "inputs/s13_unilateral_decision/draft-dialogue.json")
    settings = read_json(ROOT / "tests/fixtures/generated_contract.json")["settings"]
    settings["characters"] = [
        {"id": character["id"], "asset_id": asset_id,
         "voice": "Shared offline-test voice requirement."}
        for character, asset_id in zip(scene["characters"], scene["asset_ids"])
    ]
    return scene, manifest, plan, draft, settings


def test_authored_draft_replaces_only_dialogue_without_mutating_inputs():
    scene, _manifest, plan, draft, _settings = _s13_generated_case()
    assert draft["dialogue"] == [
        {"character_id": "despicableme4_lucy", "text": "所以你没有问我，就自己决定了。"},
        {"character_id": "despicableme4_gru", "text": "我只是觉得这样更简单。"},
    ]
    before = deepcopy((scene, plan, draft))
    adapted = pipeline.apply_authored_dialogue_draft(scene, plan, draft)
    assert adapted["shots"][0]["dialogue"] == draft["dialogue"]
    assert {**adapted["shots"][0], "dialogue": []} == {
        **plan["shots"][0], "dialogue": []}
    assert (scene, plan, draft) == before


def test_generated_pipeline_uses_one_authored_draft_for_all_conditions_offline(tmp_path):
    scene, manifest, planner_plan, draft, settings = _s13_generated_case()
    director = {"scene_id": scene["scene_id"], "tone": scene["tone"],
                "beat_order": ["b1", "b2"], "approach": "Offline shared-draft test"}
    staged = {"scene_id": scene["scene_id"], "scene_direction": planner_plan["scene_direction"],
              "segments": [{"beat_ids": ["b1", "b2"], "description": "Offline segment",
                            "direction": planner_plan["shots"][0]["direction"], "duration_s": 8}]}
    empty_generic = {"schema_version": "1.0", "scene_id": scene["scene_id"],
                     "mode": "generic_review", "issues": []}
    empty_moodcut = {**empty_generic, "mode": "moodcut"}
    client = FakeClient([director, staged, planner_plan, empty_generic, empty_moodcut])
    output = tmp_path / "shared-draft"

    block = pipeline.run_experiment(
        scene, manifest, client, out_dir=output, project_root=ROOT, render=False,
        output_mode="generated", generation_settings=settings,
        template_sha256=get_video_template_sha256(), authored_dialogue_draft=draft)

    assert block["status"] == "prepared"
    assert block["planning"]["calls"] == 3
    assert block["planning"]["raw_responses"]["shot"] == planner_plan
    assert block["initial_plan_source"]["kind"] == "authored_shared_dialogue"
    initial = read_json(output / "initial.json")
    assert initial["shots"][0]["dialogue"] == draft["dialogue"]
    assert read_json(output / "draft-dialogue.json") == draft
    assert [row["review_calls"] for row in block["runs"]] == [0, 1, 1]
    for condition in CONDITIONS:
        assert read_json(output / condition / "initial.json") == initial
        assert read_json(output / condition / "final.json") == initial
    pipeline._load_generated_block(output, ROOT)
    tampered = deepcopy(draft)
    tampered["dialogue"][0]["text"] = "Tampered after script preparation."
    (output / "draft-dialogue.json").write_text(
        json.dumps(tampered, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="draft hash mismatch"):
        pipeline._load_generated_block(output, ROOT)


def test_authored_draft_mismatch_fails_before_condition_copying():
    scene, _manifest, plan, draft, _settings = _s13_generated_case()
    draft["story_id"] = "s14_spoiled_drink"
    with pytest.raises(ValueError, match="story identity"):
        pipeline.apply_authored_dialogue_draft(scene, plan, draft)
