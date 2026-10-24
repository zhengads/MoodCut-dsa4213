

"""Unit tests for MoodCut structural validation."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from moodcut.validation import validate_plan, validate_scene


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


@pytest.fixture
def generated_data():
    """Published 1.1 software inputs, not model or formal experiment data."""
    data = load_fixture("generated_contract.json")
    return data["scene"], data["initial_plan"], load_fixture("assets.json")


def test_generated_short_scene_and_plan_validate_without_mutation(generated_data):
    scene, plan, manifest = generated_data
    before = deepcopy(generated_data)
    assert validate_scene(scene, manifest, output_mode="generated") == []
    assert validate_plan(scene, plan, manifest, output_mode="generated") == []
    assert sum(s["duration_s"] for s in plan["shots"]) == 18
    assert generated_data == before


@pytest.mark.parametrize("tone", ["tense", "suspicious"])
@pytest.mark.parametrize("mode", ["animatic", "generated"])
def test_tense_and_legacy_suspicious_remain_distinct_supported_tones(
        tone, mode, valid_data, generated_data):
    scene, plan, manifest = generated_data if mode == "generated" else valid_data
    scene["tone"] = plan["tone"] = tone
    before = deepcopy((scene, plan, manifest))
    assert validate_scene(scene, manifest, output_mode=mode) == []
    assert validate_plan(scene, plan, manifest, output_mode=mode) == []
    assert (scene, plan, manifest) == before


def test_modes_are_explicit_and_old_animatic_still_works(valid_data, generated_data):
    scene, plan, manifest = valid_data
    assert validate_scene(scene, manifest) == []
    assert validate_plan(scene, plan, manifest, output_mode="animatic") == []
    assert validate_plan(scene, plan, manifest, output_mode="generated")
    scene, plan, manifest = generated_data
    assert validate_scene(scene, manifest)
    assert validate_plan(scene, plan, manifest)


@pytest.mark.parametrize("mode", ["video", "", None, [], {}])
def test_unknown_output_modes_return_errors(generated_data, mode):
    scene, plan, manifest = generated_data
    assert validate_scene(scene, manifest, output_mode=mode)
    assert validate_plan(scene, plan, manifest, output_mode=mode)


@pytest.mark.parametrize("owner,key,value", [
    ("scene", "schema_version", "1.0"), ("plan", "schema_version", "1.0"),
    ("scene", "output_mode", "animatic"), ("plan", "output_mode", "animatic"),
    ("scene", "output_mode", None), ("plan", "output_mode", None),
    ("plan", "scene_direction", ""), ("plan", "scene_direction", None),
])
def test_generated_headers_and_scene_direction_are_required(generated_data, owner, key, value):
    scene, plan, manifest = generated_data
    (scene if owner == "scene" else plan)[key] = value
    assert validate_plan(scene, plan, manifest, output_mode="generated")


@pytest.mark.parametrize("field", ["min_duration_s", "max_duration_s", "min_shot_duration_s", "max_shot_duration_s"])
@pytest.mark.parametrize("value", [0, -1, True, 6.0, None, float("nan"), float("inf")])
def test_generated_bounds_require_positive_integers(generated_data, field, value):
    scene, plan, manifest = generated_data
    scene[field] = value
    assert validate_scene(scene, manifest, output_mode="generated")
    assert validate_plan(scene, plan, manifest, output_mode="generated")


@pytest.mark.parametrize("lower,upper", [("min_duration_s", "max_duration_s"),
                                        ("min_shot_duration_s", "max_shot_duration_s")])
def test_generated_bounds_must_be_ordered(generated_data, lower, upper):
    scene, plan, manifest = generated_data
    scene[lower] = scene[upper] + 1
    assert validate_scene(scene, manifest, output_mode="generated")
    assert validate_plan(scene, plan, manifest, output_mode="generated")


@pytest.mark.parametrize("value", [0, -1, True, 6.0, None, float("nan"), float("inf"), 3, 9])
def test_generated_per_shot_duration_must_match_bounds(generated_data, value):
    scene, plan, manifest = generated_data
    plan["shots"][0]["duration_s"] = value
    assert validate_plan(scene, plan, manifest, output_mode="generated")


def test_generated_total_and_scene_shot_count_are_checked(generated_data):
    scene, plan, manifest = generated_data
    for minimum, maximum in [(19, 30), (5, 17)]:
        candidate = dict(scene, min_duration_s=minimum, max_duration_s=maximum)
        assert validate_plan(candidate, plan, manifest, output_mode="generated")
    scene["max_shots"] = 2
    assert validate_plan(scene, plan, manifest, output_mode="generated")


def test_generated_bounds_have_no_legacy_ninety_second_cap(generated_data):
    scene, plan, manifest = generated_data
    scene.update(min_duration_s=100, max_duration_s=130, min_shot_duration_s=30, max_shot_duration_s=50)
    for shot in plan["shots"]:
        shot["duration_s"] = 40
    assert validate_scene(scene, manifest, output_mode="generated") == []
    assert validate_plan(scene, plan, manifest, output_mode="generated") == []
    # Structural range checks are independent of a provider's actual capabilities.


@pytest.mark.parametrize("field,value", [("direction", ""), ("direction", None),
                                         ("narration", None), ("beat_ids", ["missing"]),
                                         ("dialogue", [{"character_id": "missing", "text": "x"}]),
                                         ("dialogue", [{"character_id": "a", "text": "x", "voice": "override"}])])
def test_generated_shot_structure_is_checked(generated_data, field, value):
    scene, plan, manifest = generated_data
    plan["shots"][0][field] = value
    assert validate_plan(scene, plan, manifest, output_mode="generated")


@pytest.mark.parametrize("change", ["hash", "path", "dimensions", "crop", "speaker", "asset", "beat"])
def test_generated_reuses_asset_and_reference_validation(generated_data, change):
    scene, plan, manifest = generated_data
    if change == "hash":
        manifest["assets"][0]["sha256"] = "0" * 64
    elif change == "path":
        manifest["assets"][0]["path"] = "../../outside.png"
    elif change == "dimensions":
        manifest["assets"][0]["width"] = 1
    elif change == "crop":
        plan["shots"][0]["visuals"][0]["crop"] = []
    elif change == "speaker":
        plan["shots"][0]["dialogue"][0]["character_id"] = []
    elif change == "asset":
        plan["shots"][0]["visuals"][0]["asset_id"] = []
    elif change == "beat":
        plan["shots"][1]["beat_ids"] = ["b1"]
    assert validate_plan(scene, plan, manifest, output_mode="generated")


def test_generated_manifest_stays_version_one(generated_data):
    scene, plan, manifest = generated_data
    manifest["schema_version"] = "1.1"
    assert validate_scene(scene, manifest, output_mode="generated")
    assert validate_plan(scene, plan, manifest, output_mode="generated")


@pytest.mark.parametrize("value", [None, [[]], {}, ["invalid"]])
def test_invalid_manifest_crops_return_errors_without_raising(generated_data, value):
    scene, plan, manifest = generated_data
    manifest["assets"][0]["allowed_crops"] = value
    assert validate_scene(scene, manifest, output_mode="generated")
    assert validate_plan(scene, plan, manifest, output_mode="generated")


@pytest.mark.parametrize("value", [float("nan"), {1: "key"}, (1, 2)])
def test_generated_invalid_json_extensions_are_not_ignored(generated_data, value):
    scene, plan, manifest = generated_data
    plan["future_control"] = value
    assert validate_plan(scene, plan, manifest, output_mode="generated")
