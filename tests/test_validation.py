

"""Unit tests for MoodCut structural validation."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from moodcut.validation import validate_plan


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def load_fixture(filename):
    """Load a JSON fixture from the shared fixture directory."""
    path = FIXTURE_DIR / filename
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def valid_data():
    """Return independent copies of the shared valid fixtures."""
    return (
        load_fixture("scene.json"),
        load_fixture("plan.json"),
        load_fixture("assets.json"),
    )


def assert_invalid(scene, plan, manifest):
    """Assert that validation reports at least one error."""
    errors = validate_plan(scene, plan, manifest)
    assert isinstance(errors, list)
    assert errors, "Expected validation errors, but received []"
    assert all(isinstance(error, str) for error in errors)


def test_valid_plan(valid_data):
    scene, plan, manifest = valid_data
    assert validate_plan(scene, plan, manifest) == []


def test_invalid_schema_version(valid_data):
    scene, plan, manifest = valid_data
    plan["schema_version"] = "2.0"
    assert_invalid(scene, plan, manifest)


def test_mismatched_scene_id(valid_data):
    scene, plan, manifest = valid_data
    plan["scene_id"] = "different_scene"
    assert_invalid(scene, plan, manifest)


def test_invalid_tone(valid_data):
    scene, plan, manifest = valid_data
    scene["tone"] = "happy"
    assert_invalid(scene, plan, manifest)


def test_mismatched_tone(valid_data):
    scene, plan, manifest = valid_data
    plan["tone"] = "hostile"
    assert_invalid(scene, plan, manifest)


def test_duplicate_character_id(valid_data):
    scene, plan, manifest = valid_data
    scene["characters"][1]["id"] = "a"
    assert_invalid(scene, plan, manifest)


def test_duplicate_shot_id(valid_data):
    scene, plan, manifest = valid_data
    plan["shots"][1]["shot_id"] = "s1"
    assert_invalid(scene, plan, manifest)


def test_unknown_beat_reference(valid_data):
    scene, plan, manifest = valid_data
    plan["shots"][0]["beat_ids"] = ["unknown_beat"]
    assert_invalid(scene, plan, manifest)


def test_missing_beat_coverage(valid_data):
    scene, plan, manifest = valid_data
    plan["shots"][1]["beat_ids"] = ["b1"]
    assert_invalid(scene, plan, manifest)


@pytest.mark.parametrize("duration", [-5, 0, True, None, float("inf"), float("nan")])
def test_invalid_shot_duration(valid_data, duration):
    scene, plan, manifest = valid_data
    plan["shots"][0]["duration_s"] = duration
    assert_invalid(scene, plan, manifest)


def test_total_duration_too_short(valid_data):
    scene, plan, manifest = valid_data
    for shot in plan["shots"]:
        shot["duration_s"] = 10
    assert_invalid(scene, plan, manifest)


def test_total_duration_too_long(valid_data):
    scene, plan, manifest = valid_data
    for shot in plan["shots"]:
        shot["duration_s"] = 40
    assert_invalid(scene, plan, manifest)


def test_too_many_shots(valid_data):
    scene, plan, manifest = valid_data
    plan["shots"] = [
        deepcopy(plan["shots"][i % 3])
        for i in range(7)
    ]
    assert_invalid(scene, plan, manifest)


def test_empty_shot_list(valid_data):
    scene, plan, manifest = valid_data
    plan["shots"] = []
    assert_invalid(scene, plan, manifest)


def test_unknown_character_in_dialogue(valid_data):
    scene, plan, manifest = valid_data
    plan["shots"][0]["dialogue"][0]["character_id"] = "unknown"
    assert_invalid(scene, plan, manifest)


def test_unknown_asset_reference(valid_data):
    scene, plan, manifest = valid_data
    plan["shots"][0]["visuals"][0]["asset_id"] = "unknown"
    assert_invalid(scene, plan, manifest)


def test_invalid_crop(valid_data):
    scene, plan, manifest = valid_data
    plan["shots"][0]["visuals"][0]["crop"] = "extreme_zoom"
    assert_invalid(scene, plan, manifest)


def test_too_many_visuals(valid_data):
    scene, plan, manifest = valid_data
    plan["shots"][0]["visuals"].append(
        deepcopy(plan["shots"][0]["visuals"][0])
    )
    assert_invalid(scene, plan, manifest)


def test_missing_asset_file(valid_data):
    scene, plan, manifest = valid_data
    manifest["assets"][0]["path"] = (
        "tests/fixtures/images/nonexistent.png"
    )
    assert_invalid(scene, plan, manifest)


def test_incorrect_asset_hash(valid_data):
    scene, plan, manifest = valid_data
    manifest["assets"][0]["sha256"] = "0" * 64
    assert_invalid(scene, plan, manifest)


def test_incorrect_image_dimensions(valid_data):
    scene, plan, manifest = valid_data
    manifest["assets"][0]["width"] = 999
    assert_invalid(scene, plan, manifest)


def test_absolute_asset_path(valid_data):
    scene, plan, manifest = valid_data
    manifest["assets"][0]["path"] = "/tmp/unsafe.png"
    assert_invalid(scene, plan, manifest)


def test_asset_path_traversal(valid_data):
    scene, plan, manifest = valid_data
    manifest["assets"][0]["path"] = "../../outside.png"
    assert_invalid(scene, plan, manifest)


def test_validation_does_not_modify_inputs(valid_data):
    scene, plan, manifest = valid_data

    original_scene = deepcopy(scene)
    original_plan = deepcopy(plan)
    original_manifest = deepcopy(manifest)

    validate_plan(scene, plan, manifest)

    assert scene == original_scene
    assert plan == original_plan
    assert manifest == original_manifest
