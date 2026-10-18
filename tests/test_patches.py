"""Atomic patch unit tests and integration with MC-01 shared fixtures."""
import json
import unittest
import pytest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch as mock_patch
from moodcut.patches import apply_patch
from moodcut.validation import validate_plan
from test_reviewer import inputs, _review_case_data


class PatchTests(unittest.TestCase):
    def setUp(self):
        self.scene, self.plan, self.report = inputs()
        self.plan.update(schema_version="1.0", tone="suspicious")
        self.plan["shots"][0].update(beat_ids=["b1"], duration_s=60,
                                    dialogue=[{"character_id": "a", "text": "Here."}],
                                    narration="A hands over the letter.",
                                    visuals=[{"asset_id": "a", "crop": "full"}])
        self.manifest = {"assets": [{"asset_id": "a", "allowed_crops": ["full", "center_close"]}]}
        self.patch = {"schema_version": "1.0", "scene_id": "dev", "edits": [
            {"issue_id": "r1", "shot_id": "s1", "set": {"dialogue": [
                {"character_id": "a", "text": "Where did you get this letter?"}]}}]}

    def run_patch(self):
        return apply_patch(self.scene, self.plan, self.manifest, self.report, self.patch)

    def test_valid_change_and_inputs_unchanged(self):
        before = deepcopy((self.scene, self.plan, self.manifest, self.report, self.patch))
        with mock_patch("moodcut.validation.validate_plan", create=True, return_value=[]) as spy:
            result = self.run_patch()
        self.assertEqual(result["status"], "applied")
        self.assertEqual(result["plan"]["shots"][0]["dialogue"], self.patch["edits"][0]["set"]["dialogue"])
        spy.assert_called_once_with(self.scene, result["plan"], self.manifest)
        self.assertEqual(before, (self.scene, self.plan, self.manifest, self.report, self.patch))
        result["plan"]["shots"][0]["beat_ids"].append("x")
        self.assertEqual(self.plan["shots"][0]["beat_ids"], ["b1"])

    def test_empty_and_same_value(self):
        with mock_patch("moodcut.validation.validate_plan", create=True, return_value=[]):
            self.patch["edits"] = []
            self.report["issues"] = []
            self.assertEqual(self.run_patch()["status"], "unchanged")

    def test_forbidden_fields(self):
        for field in ("shot_id", "beat_ids", "story", "tone", "scene_id", "shots", "actions"):
            with self.subTest(field=field):
                self.patch["edits"][0]["set"] = {field: "changed"}
                result = self.run_patch()
                self.assertEqual(result["status"], "rejected")
                self.assertEqual(result["plan"], self.plan)

    def test_bad_references_conflicts_and_shapes(self):
        original = deepcopy(self.patch)
        variants = [None, {}, {**original, "edits": {}},
                    {**original, "scene_id": "other"}, {**original, "tone": "hostile"}]
        for field, value in (("shot_id", "unknown"), ("issue_id", "unknown"), ("set", {})):
            bad = deepcopy(original)
            bad["edits"][0][field] = value
            variants.append(bad)
        variants.append({**original, "edits": original["edits"] * 2})
        for value in variants:
            self.patch = value
            result = self.run_patch()
            self.assertEqual(result["status"], "rejected")
            self.assertEqual(result["plan"], self.plan)

    def test_asset_replacement_and_order(self):
        self.patch["edits"][0]["set"] = {"visuals": [{"asset_id": "b", "crop": "full"}]}
        self.assertEqual(self.run_patch()["status"], "rejected")
        self.plan["shots"][0]["visuals"].append({"asset_id": "b", "crop": "full"})
        self.patch["edits"][0]["set"]["visuals"] = list(reversed(self.plan["shots"][0]["visuals"]))
        self.assertEqual(self.run_patch()["status"], "rejected")

    def test_validator_errors_atomic_rollback(self):
        # These errors come from the shared validator, not a local imitation.
        for changes, errors in (({"duration_s": 10}, ["total duration below minimum"]),
                                ({"visuals": [{"asset_id": "a", "crop": "forbidden"}]}, ["crop not allowed"]),
                                ({"narration": "Subtitle only."}, ["invalid plan", "asset missing"])):
            self.patch["edits"][0]["set"] = changes
            with mock_patch("moodcut.validation.validate_plan", create=True, return_value=errors):
                result = self.run_patch()
            self.assertEqual(result, {"plan": self.plan, "status": "rejected", "errors": errors})

    def test_multiple_shots_roll_back_on_later_illegal_edit(self):
        second = deepcopy(self.plan["shots"][0])
        second["shot_id"] = "s2"
        self.plan["shots"].append(second)
        issue = deepcopy(self.report["issues"][0])
        issue.update(issue_id="r2", shot_id="s2")
        self.report["issues"].append(issue)
        self.patch["edits"].append({"issue_id": "r2", "shot_id": "s2", "set": {"beat_ids": []}})
        with mock_patch("moodcut.validation.validate_plan", create=True, return_value=[]) as spy:
            result = self.run_patch()
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["plan"], self.plan)
        spy.assert_not_called()

    def test_valid_crop_and_duration_forwarded(self):
        self.patch["edits"][0]["set"] = {
            "visuals": [{"asset_id": "a", "crop": "center_close"}], "duration_s": 70}
        with mock_patch("moodcut.validation.validate_plan", create=True, return_value=[]) as spy:
            result = self.run_patch()
        self.assertEqual(result["status"], "applied")
        self.assertEqual(spy.call_args.args[1]["shots"][0]["duration_s"], 70)

    def test_validator_cannot_mutate_inputs(self):
        before = deepcopy((self.scene, self.plan, self.manifest))

        def failing_validator(scene, plan, manifest):
            scene.clear()
            plan.clear()
            manifest.clear()
            raise RuntimeError("validation interrupted")

        with mock_patch("moodcut.validation.validate_plan", create=True, side_effect=failing_validator):
            result = self.run_patch()
        self.assertEqual(result["plan"], self.plan)
        self.assertEqual(before, (self.scene, self.plan, self.manifest))

    def test_validator_missing_exception_or_invalid_return(self):
        with mock_patch("moodcut.validation.validate_plan", create=True, new=None):
            self.assertEqual(self.run_patch()["status"], "rejected")
        for value in (None, True, [123]):
            with mock_patch("moodcut.validation.validate_plan", create=True, return_value=value):
                self.assertEqual(self.run_patch()["status"], "rejected")
        with mock_patch("moodcut.validation.validate_plan", create=True, side_effect=RuntimeError("failed")):
            self.assertEqual(self.run_patch()["plan"], self.plan)


class SharedFixtureTests(unittest.TestCase):
    """Exercise the real validator, including on-disk asset integrity."""

    def setUp(self):
        fixture_dir = Path(__file__).resolve().parent / "fixtures"
        self.data = [json.loads((fixture_dir / f"{name}.json").read_text(encoding="utf-8"))
                     for name in ("scene", "plan", "assets", "review", "patch")]
        self.scene, self.plan, self.manifest, self.report, self.patch = self.data

    def run_patch(self):
        return apply_patch(*self.data)

    def assert_rejected(self, result, contains):
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["plan"], self.plan)
        self.assertIsNot(result["plan"], self.plan)
        self.assertTrue(any(contains in error for error in result["errors"]), result)

    def test_shared_patch_applies_and_preserves_inputs(self):
        before = deepcopy(self.data)
        self.assertEqual(validate_plan(self.scene, self.plan, self.manifest), [])
        result = self.run_patch()
        self.assertEqual(result["status"], "applied")
        self.assertEqual(validate_plan(self.scene, result["plan"], self.manifest), [])
        expected = deepcopy(self.plan)
        expected["shots"][1].update(self.patch["edits"][0]["set"])
        self.assertEqual(result["plan"], expected)
        self.assertEqual(self.data, before)

    def test_no_issues_and_no_change(self):
        self.report["issues"] = []
        self.patch["edits"] = []
        self.assertEqual(self.run_patch(), {"plan": self.plan, "status": "unchanged", "errors": []})

    def test_same_value_returns_unchanged(self):
        self.patch["edits"][0]["set"] = {"duration_s": self.plan["shots"][1]["duration_s"]}
        self.assertEqual(self.run_patch()["status"], "unchanged")

    def test_duration_limits_and_invalid_numbers(self):
        for duration in (1, 51, 0, -1, True, float("nan"), float("inf"), "20"):
            with self.subTest(duration=duration):
                self.patch["edits"][0]["set"]["duration_s"] = duration
                self.assert_rejected(self.run_patch(), "duration")
        for duration in (20, 50):
            self.patch["edits"][0]["set"]["duration_s"] = duration
            self.assertEqual(self.run_patch()["status"], "applied")

    def test_manifest_crop_restriction(self):
        self.manifest["assets"][1]["allowed_crops"] = ["full"]
        self.assert_rejected(self.run_patch(), "crop not allowed by manifest")

    def test_invalid_crop_character_and_text(self):
        changes = self.patch["edits"][0]["set"]
        changes["visuals"][0]["crop"] = "unsupported"
        self.assert_rejected(self.run_patch(), "crop")
        changes["visuals"][0]["crop"] = "center_close"
        changes["dialogue"][0]["character_id"] = "unknown"
        self.assert_rejected(self.run_patch(), "character_id")
        changes["dialogue"][0]["character_id"] = "b"
        changes["dialogue"][0]["text"] = " "
        self.assert_rejected(self.run_patch(), "text")

    def test_nested_action_fields_rejected(self):
        self.patch["edits"][0]["set"]["dialogue"][0]["actions"] = ["new animation"]
        self.assert_rejected(self.run_patch(), "dialogue entries")

    def test_asset_hash_failure_rolls_back(self):
        self.manifest["assets"][0]["sha256"] = "0" * 64
        self.assert_rejected(self.run_patch(), "SHA-256 mismatch")

    def test_later_shot_validation_failure_rolls_back_all_edits(self):
        issue = deepcopy(self.report["issues"][0])
        issue.update(issue_id="r2", shot_id="s3")
        self.report["issues"].append(issue)
        self.patch["edits"].append({"issue_id": "r2", "shot_id": "s3",
                                    "set": {"duration_s": 0}})
        before = deepcopy(self.data)
        self.assert_rejected(self.run_patch(), "duration_s")
        self.assertEqual(self.data, before)

    def test_two_edits_for_one_shot_and_mismatched_issue(self):
        issue = deepcopy(self.report["issues"][0])
        issue["issue_id"] = "r2"
        self.report["issues"].append(issue)
        self.patch["edits"].append({"issue_id": "r2", "shot_id": "s2",
                                    "set": {"narration": "Subtitle."}})
        self.assert_rejected(self.run_patch(), "conflicting")
        self.patch["edits"].pop()
        self.patch["edits"][0]["shot_id"] = "s1"
        self.assert_rejected(self.run_patch(), "issue_id")

    def test_invalid_target_plan_fails_without_exception(self):
        for shots in (None, [None], [{"shot_id": []}], self.plan["shots"] * 2):
            with self.subTest(shots=shots):
                original_shots = self.plan["shots"]
                self.plan["shots"] = shots
                result = self.run_patch()
                self.assertEqual(result["status"], "rejected")
                self.assertEqual(result["plan"], self.plan)
                self.plan["shots"] = original_shots


def test_generated_patch_preserves_complete_non_dialogue_identity():
    from moodcut.contracts import assert_dialogue_only_revision
    scene, plan, manifest, report, patch_data, _verification, _mode = _review_case_data("generated")
    plan["future_extension"] = {"frozen": [1, {"continuity": True}]}
    before = deepcopy((scene, plan, manifest, report, patch_data))
    result = apply_patch(scene, plan, manifest, report, patch_data,
                         project_root=Path(__file__).resolve().parents[1], output_mode="generated")
    assert result["status"] == "applied" and result["errors"] == []
    assert_dialogue_only_revision(plan, result["plan"])
    assert result["plan"]["future_extension"] == plan["future_extension"]
    assert (scene, plan, manifest, report, patch_data) == before


@pytest.mark.parametrize("field", ("narration", "visuals", "duration_s", "direction", "scene_direction",
    "shot_id", "beat_ids", "shots", "future_extension"))
def test_generated_non_dialogue_edit_rejects_the_whole_patch(field):
    scene, plan, manifest, report, patch_data, _verification, _mode = _review_case_data("generated")
    patch_data["edits"][1]["set"] = {field: "forbidden change"}
    before = deepcopy((scene, plan, manifest, report, patch_data))
    result = apply_patch(scene, plan, manifest, report, patch_data,
                         project_root=Path(__file__).resolve().parents[1], output_mode="generated")
    assert result["status"] == "rejected" and result["plan"] == plan and result["errors"]
    assert (scene, plan, manifest, report, patch_data) == before


@pytest.mark.parametrize("field", ("actions", "voice", "direction"))
def test_generated_dialogue_cannot_hide_extra_controls(field):
    scene, plan, manifest, report, patch_data, _verification, _mode = _review_case_data("generated")
    patch_data["edits"][0]["set"]["dialogue"][0][field] = "hidden control"
    result = apply_patch(scene, plan, manifest, report, patch_data,
                         project_root=Path(__file__).resolve().parents[1], output_mode="generated")
    assert result["status"] == "rejected" and result["plan"] == plan


@pytest.mark.parametrize("mode", ("animatic", "unknown", None))
def test_generated_records_require_explicit_valid_output_mode(mode):
    scene, plan, manifest, report, patch_data, _verification, _mode = _review_case_data("generated")
    result = apply_patch(scene, plan, manifest, report, patch_data,
                         project_root=Path(__file__).resolve().parents[1], output_mode=mode)
    assert result["status"] == "rejected" and result["plan"] == plan
