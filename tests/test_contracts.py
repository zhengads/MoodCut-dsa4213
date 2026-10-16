"""Counterfactual checks for the public generated-mode contract, never model scores."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from moodcut.contracts import (
    CONDITIONS, CONTRACT_VERSION, allowed_patch_fields, assert_dialogue_only_revision,
    json_hash, non_dialogue_plan, shared_generation_payload, shared_generation_sha256,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def data():
    example = json.loads((ROOT / "tests/fixtures/generated_contract.json").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / example["manifest_file"]).read_text(encoding="utf-8"))
    return example, manifest


def identity(example, manifest, plan=None):
    return shared_generation_sha256(
        example["scene"], plan or example["initial_plan"], manifest, example["settings"],
        template_sha256=example["template_sha256"])


def test_legacy_hash_bytes_and_import_are_unchanged():
    from moodcut.pipeline import json_hash as legacy_hash
    value = {"中文": [1, 1.0, True, None], "z": "x"}
    expected = hashlib.sha256(json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")).hexdigest()
    assert json_hash(value) == legacy_hash(value) == expected
    assert legacy_hash is json_hash


def test_modes_have_explicit_equal_review_capabilities():
    assert CONTRACT_VERSION == "1.1"
    assert allowed_patch_fields(output_mode="generated") == frozenset({"dialogue"})
    assert allowed_patch_fields(output_mode="animatic") == frozenset(
        {"dialogue", "narration", "visuals", "duration_s"})
    with pytest.raises(ValueError):
        allowed_patch_fields(output_mode="video")


def test_three_conditions_share_identity_and_inputs_remain_unchanged(data):
    example, manifest = data
    before = deepcopy((example, manifest))
    expected = example["shared_generation_sha256"]
    assert set(example["condition_plans"]) == set(CONDITIONS)
    for plan in example["condition_plans"].values():
        assert_dialogue_only_revision(example["initial_plan"], plan)
        assert identity(example, manifest, plan) == expected
    payload = shared_generation_payload(
        example["scene"], example["initial_plan"], manifest, example["settings"],
        template_sha256=example["template_sha256"])
    payload["plan"]["shots"][0]["direction"] = "Changed returned copy"
    assert (example, manifest) == before


def test_full_plan_hash_retains_the_dialogue_treatment(data):
    example, _ = data
    initial = example["initial_plan"]
    revised = example["condition_plans"]["moodcut"]
    assert initial != revised
    assert json_hash(initial) != json_hash(revised)
    assert non_dialogue_plan(initial) == non_dialogue_plan(revised)


def test_helpers_do_not_open_files_or_connect_to_services(data, monkeypatch):
    import builtins
    import socket
    import urllib.request
    example, manifest = data
    def forbidden(*args, **kwargs):
        raise AssertionError("Public contract helpers must not perform I/O")
    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    assert identity(example, manifest) == example["shared_generation_sha256"]
    assert_dialogue_only_revision(example["initial_plan"], example["condition_plans"]["moodcut"])


@pytest.mark.parametrize("change", ["direction", "duration_s", "narration", "visuals", "extra"])
def test_non_dialogue_and_unknown_shot_changes_rejected(data, change):
    example, manifest = data
    original = example["initial_plan"]
    candidate = deepcopy(original)
    shot = candidate["shots"][0]
    if change == "duration_s":
        shot[change] += 1
    elif change == "visuals":
        shot[change][0]["crop"] = "center_close"
    elif change == "extra":
        shot["future_acting_control"] = {"intensity": 2}
    else:
        shot[change] += " altered"
    with pytest.raises(ValueError, match="non-dialogue"):
        assert_dialogue_only_revision(original, candidate)
    assert identity(example, manifest, candidate) != identity(example, manifest)


def test_unknown_root_fields_and_order_are_not_dropped(data):
    example, _ = data
    original = example["initial_plan"]
    for candidate in [dict(original, future_camera="close"),
                      dict(original, shots=list(reversed(original["shots"])) )]:
        with pytest.raises(ValueError, match="non-dialogue"):
            assert_dialogue_only_revision(original, candidate)
    candidate = deepcopy(original)
    candidate["shots"][0]["duration_s"] = True
    with pytest.raises(ValueError, match="non-dialogue"):
        assert_dialogue_only_revision(original, candidate)


@pytest.mark.parametrize("field,value", [
    ("model", "software-fixture/other"), ("seed", 99), ("resolution", "480p"),
    ("style", "other shared style"), ("sound", "other shared sound"),
])
def test_generation_controls_change_identity(data, field, value):
    example, manifest = data
    before = identity(example, manifest)
    example["settings"][field] = value
    assert identity(example, manifest) != before


def test_voice_reference_content_and_template_are_frozen(data):
    example, manifest = data
    before = identity(example, manifest)
    edited = deepcopy(example)
    edited["settings"]["characters"][0]["voice"] += " changed"
    assert identity(edited, manifest) != before
    changed_manifest = deepcopy(manifest)
    changed_manifest["assets"][0]["sha256"] = "a" * 64
    assert identity(example, changed_manifest) != before
    changed_manifest = deepcopy(manifest)
    changed_manifest["assets"][0]["source_url"] = "https://example.org/reference.png"
    assert identity(example, changed_manifest) != before
    edited = deepcopy(example)
    edited["template_sha256"] = "b" * 64
    assert identity(edited, manifest) != before


def test_material_local_path_and_dictionary_key_order_do_not_change_identity(data):
    example, manifest = data
    before = identity(example, manifest)
    manifest["assets"][0]["path"] = "assets/raw/moved.png"
    manifest["assets"] = list(reversed(manifest["assets"]))
    example["settings"] = dict(reversed(list(example["settings"].items())))
    assert identity(example, manifest) == before


@pytest.mark.parametrize("value", [float("nan"), float("inf"), {1: "non-string key"}, (1, 2)])
def test_identity_rejects_non_json_or_nonfinite_fields(data, value):
    example, manifest = data
    example["initial_plan"]["future_control"] = value
    with pytest.raises(ValueError):
        identity(example, manifest)


@pytest.mark.parametrize("change", ["old_schema", "wrong_mode", "unknown_setting", "missing_dialogue",
                                    "bad_hash", "duplicate_asset", "wrong_character", "bad_audio"])
def test_invalid_identity_inputs_fail_closed(data, change):
    example, manifest = data
    if change == "old_schema":
        example["scene"]["schema_version"] = "1.0"
    elif change == "wrong_mode":
        example["initial_plan"]["output_mode"] = "animatic"
    elif change == "unknown_setting":
        example["settings"]["output_dir"] = "ignored-if-unsafe"
    elif change == "missing_dialogue":
        del example["initial_plan"]["shots"][0]["dialogue"]
    elif change == "bad_hash":
        manifest["assets"][0]["sha256"] = "not-a-hash"
    elif change == "duplicate_asset":
        manifest["assets"].append(deepcopy(manifest["assets"][0]))
    elif change == "wrong_character":
        example["settings"]["characters"][0]["asset_id"] = "dev_b"
    elif change == "bad_audio":
        example["settings"]["generate_audio"] = False
    with pytest.raises(ValueError):
        identity(example, manifest)


def test_fixture_records_are_unrendered_synthetic_and_readable_by_existing_summary(data):
    from moodcut.evaluation import summarize
    example, _ = data
    records = example["run_records"]
    assert {r["condition"] for r in records} == set(CONDITIONS)
    assert all(r["source_kind"] == "synthetic" and r["mock"] for r in records)
    assert all(r["render_status"] == "not_started" and r["video_path"] is None for r in records)
    assert all(r["generation_status"] == "not_started" and r["calls"] == 0 for r in records)
    assert all(r["validation_status"] == "not_started" and r["comparison_status"] == "not_checked"
               for r in records)
    assert {r["shared_generation_sha256"] for r in records} == {example["shared_generation_sha256"]}
    assert hashlib.sha256(example["template_text"].encode("utf-8")).hexdigest() == example["template_sha256"]
    for record in records:
        assert record["initial_plan_sha256"] == json_hash(example["initial_plan"])
        assert record["final_plan_sha256"] == json_hash(example["condition_plans"][record["condition"]])
    summary = summarize(records, [])
    assert summary["overall"]["coverage"]["planned_runs"] == 3
    assert summary["overall"]["coverage"]["rated_clips"] == 0
    assert summary["overall"]["equal_clip_means"]["tone_accuracy"] is None
