"""Offline integrity checks for the supplementary S07-S12 study inputs."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

from moodcut.contracts import CONDITIONS, VEMOCLAP_EMOTIONS
from moodcut.validation import validate_scene


ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "docs/studies/six-story-clear-emotions-20261024"
INDEX_PATH = STUDY / "inputs/basic-emotions-index.json"
DESIGN_PATH = STUDY / "design-basic-emotions.json"

SOURCE_ASSETS = {
    "s07_broken_promise": "s05_broken_cooperation",
    "s08_foul_medicine": "s06_last_place",
    "s09_forest_creature": "s03_footsteps_outside",
    "s10_celebration_saved": "s01_reunion",
    "s11_irreplaceable_keepsake": "s02_stay_with_me",
    "s12_finished_task": "s04_exit_closing",
}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_basic_emotion_design_and_index_are_complete_and_hash_bound():
    design, index = read_json(DESIGN_PATH), read_json(INDEX_PATH)
    assert design["version"] == index["version"] == "1.0"
    assert tuple(design["emotion_definitions"]) == VEMOCLAP_EMOTIONS
    assert tuple(index["selected_emotions"]) == VEMOCLAP_EMOTIONS
    assert index["design_path"] == DESIGN_PATH.relative_to(ROOT).as_posix()
    assert index["design_sha256"] == sha256(DESIGN_PATH)
    assert design["conditions"] == index["conditions"] == list(CONDITIONS)
    assert design["planned_condition_entries"] == index["planned_condition_entries"] == 18
    assert len(design["stories"]) == len(index["stories"]) == 6
    assert [row["id"] for row in design["stories"]] == list(SOURCE_ASSETS)
    assert [row["story_id"] for row in index["stories"]] == list(SOURCE_ASSETS)
    assert len({character["character_id"]
                for row in design["stories"] for character in row["cast"]}) == 12


def test_basic_emotion_scenes_reuse_assets_and_validate_offline():
    index = read_json(INDEX_PATH)
    fixture_assets = read_json(ROOT / "tests/fixtures/assets.json")["assets"]
    seen_characters = set()
    for row in index["stories"]:
        story_id = row["story_id"]
        scene_path = ROOT / row["scene_path"]
        assets_path = ROOT / row["assets_path"]
        scene, manifest = read_json(scene_path), read_json(assets_path)
        source = STUDY / "inputs" / SOURCE_ASSETS[story_id] / "assets.json"

        assert row["scene_sha256"] == sha256(scene_path)
        assert row["assets_sha256"] == sha256(assets_path)
        assert assets_path.read_bytes() == source.read_bytes()
        assert scene["schema_version"] == "1.1"
        assert scene["output_mode"] == "generated"
        assert scene["tone"] == row["emotion"]
        assert scene["provenance"]["design_path"] == DESIGN_PATH.relative_to(ROOT).as_posix()
        assert scene["provenance"]["design_story_id"] == story_id
        assert len(scene["characters"]) == len(scene["beats"]) == 2
        assert scene["asset_ids"] == row["asset_ids"]
        assert scene["min_duration_s"] == scene["max_duration_s"] == 5
        assert scene["min_shot_duration_s"] == scene["max_shot_duration_s"] == 5
        seen_characters.update(row["character_ids"])

        local_manifest = deepcopy(manifest)
        for target, fixture in zip(local_manifest["assets"], fixture_assets):
            for field in ("path", "width", "height", "sha256", "allowed_crops"):
                target[field] = deepcopy(fixture[field])
        assert validate_scene(
            scene, local_manifest, project_root=ROOT, output_mode="generated") == []

    assert len(seen_characters) == 12
