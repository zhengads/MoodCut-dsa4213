"""Task-local synthetic data; not shared fixtures or model evidence."""
import unittest
import json
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
from moodcut.client import FakeClient
from moodcut.reviewer import (MAX_OUTPUT_TOKENS, review_and_revise,
                             validate_report, validate_verification)


def inputs():
    scene = {"scene_id": "dev", "tone": "suspicious"}
    plan = {"scene_id": "dev", "shots": [{"shot_id": "s1"}]}
    report = {"schema_version": "1.0", "scene_id": "dev", "mode": "moodcut",
              "issues": [{"issue_id": "r1", "shot_id": "s1", "dimension": "tone",
                          "evidence": "The line confirms receipt without hesitation.",
                          "suggestion": "Ask a hesitant question.", "severity": "minor"}]}
    return scene, plan, report


class ReportTests(unittest.TestCase):
    def test_valid_and_empty_in_both_modes(self):
        scene, plan, report = inputs()
        for mode in ("moodcut", "generic_review"):
            report["mode"] = mode
            self.assertEqual(validate_report(scene, plan, report), [])
        report["issues"] = []
        self.assertEqual(validate_report(scene, plan, report), [])

    def test_invalid_fields(self):
        scene, plan, report = inputs()
        for field, value in (("issue_id", None), ("shot_id", "unknown"),
                             ("evidence", " "), ("suggestion", []),
                             ("dimension", "score"), ("severity", "critical")):
            with self.subTest(field=field):
                bad = deepcopy(report)
                bad["issues"][0][field] = value
                self.assertTrue(validate_report(scene, plan, bad))

    def test_duplicates_and_bad_envelopes(self):
        scene, plan, report = inputs()
        report["issues"] *= 2
        self.assertTrue(validate_report(scene, plan, report))
        for bad in (None, {}, {**report, "issues": {}}, {**report, "scene_id": "other"},
                    {**report, "schema_version": "2.0"}, {**report, "mode": "baseline"}):
            self.assertTrue(validate_report(scene, plan, bad))

    def test_missing_ids_and_malformed_context(self):
        scene, plan, report = inputs()
        for field in ("issue_id", "shot_id"):
            bad = deepcopy(report)
            del bad["issues"][0][field]
            self.assertTrue(validate_report(scene, plan, bad))
        for bad in (None, {"scene_id": "dev", "shots": None}):
            self.assertTrue(validate_report(scene, bad, report))
        report["scene_id"] = None
        self.assertTrue(validate_report({}, {}, report))


class ReviewFlowTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parent / "fixtures"
        self.scene, self.plan, self.assets, self.report, self.patch, self.verify = [
            json.loads((root / f"{name}.json").read_text(encoding="utf-8"))
            for name in ("scene", "plan", "assets", "review", "patch", "verification")]

    def run_review(self, client, mode="moodcut"):
        return review_and_revise(self.scene, self.plan, self.assets, client, mode=mode)

    def test_modes_share_budget_templates_and_preserve_inputs(self):
        before = deepcopy((self.scene, self.plan, self.assets))
        clients = []
        for mode in ("generic_review", "moodcut"):
            report = {**self.report, "mode": mode}
            client = FakeClient([report, self.patch, self.verify, {"unused": True}])
            result = self.run_review(client, mode)
            self.assertEqual(result["status"], "applied", result)
            self.assertEqual([c["stage"] for c in client.calls], ["critique", "revise", "verify"])
            self.assertEqual([c["max_output_tokens"] for c in client.calls], [MAX_OUTPUT_TOKENS] * 3)
            self.assertEqual(client.remaining, 1)
            self.assertEqual(result["report"], report)
            self.assertEqual(result["patch"], self.patch)
            self.assertEqual(result["verification"], self.verify)
            self.assertEqual(result["plan"]["shots"][1]["dialogue"], self.patch["edits"][0]["set"]["dialogue"])
            json.dumps(result, allow_nan=False)
            clients.append(client)
        for index in (1, 2):
            self.assertEqual(clients[0].calls[index]["system"], clients[1].calls[index]["system"])
        first, second = [json.loads(c.calls[0]["user"]) for c in clients]
        first.pop("mode")
        second.pop("mode")
        self.assertEqual(first, second)
        self.assertEqual(first["scene"]["tone"], self.scene["tone"])
        self.assertEqual(before, (self.scene, self.plan, self.assets))

    def test_no_issues_exits_after_one_call_with_trace(self):
        client = FakeClient([{**self.report, "issues": []}, self.patch, self.verify])
        with self.assertLogs("moodcut.review.trace", level="INFO") as logs:
            result = self.run_review(client)
        self.assertEqual(result["status"], "unchanged")
        self.assertEqual(result["plan"], self.plan)
        self.assertIsNone(result["verification"])
        self.assertEqual(result["patch"]["edits"], [])
        self.assertEqual(len(client.calls), 1)
        events = [json.loads(record.getMessage()) for record in logs.records]
        self.assertEqual(events[-1]["calls"], 1)
        self.assertEqual(events[1]["response"], result["report"])

    def test_rejected_patch_stops_before_verify(self):
        self.patch["edits"][0]["set"]["tone"] = "hostile"
        client = FakeClient([self.report, self.patch, self.verify])
        result = self.run_review(client)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["plan"], self.plan)
        self.assertEqual(result["patch"], self.patch)
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(client.remaining, 1)

    def test_unresolved_and_new_concerns_do_not_trigger_another_round(self):
        self.verify.update(resolved_issue_ids=[], unresolved_issue_ids=["r1"],
                           new_concerns=["The question may sound too direct."])
        client = FakeClient([self.report, self.patch, self.verify, {}])
        result = self.run_review(client)
        self.assertEqual(result["status"], "applied")
        self.assertEqual(result["verification"], self.verify)
        self.assertEqual(client.remaining, 1)

    def test_empty_patch_still_verifies_and_remains_unchanged(self):
        self.patch["edits"] = []
        self.verify.update(resolved_issue_ids=[], unresolved_issue_ids=["r1"])
        client = FakeClient([self.report, self.patch, self.verify])
        result = self.run_review(client)
        self.assertEqual(result["status"], "unchanged")
        self.assertEqual(result["verification"]["unresolved_issue_ids"], ["r1"])
        self.assertEqual(len(client.calls), 3)

    def test_bad_reports_fail_without_revision(self):
        for bad in ({}, {**self.report, "mode": "generic_review"},
                    {**self.report, "issues": [{"shot_id": "unknown"}]}):
            client = FakeClient([bad, self.patch, self.verify])
            result = self.run_review(client)
            self.assertEqual(result["status"], "review_failed")
            self.assertEqual(result["plan"], self.plan)
            self.assertEqual(result["report"], bad)
            self.assertEqual(len(client.calls), 1)

    def test_exhaustion_at_each_stage_fails_without_retry(self):
        queue = [self.report, self.patch, self.verify]
        for count in range(3):
            client = FakeClient(queue[:count])
            result = self.run_review(client)
            self.assertEqual(result["status"], "review_failed")
            self.assertEqual(result["plan"], self.plan)
            self.assertEqual(len(client.calls), count + 1)
            self.assertTrue(result["errors"])

    def test_non_json_responses_fail_at_each_stage(self):
        queue = [self.report, self.patch, self.verify]
        for index in range(3):
            client = FakeClient(queue[:index] + [{"bad": float("nan")}])
            result = self.run_review(client)
            self.assertEqual(result["status"], "review_failed")
            self.assertEqual(result["plan"], self.plan)
            self.assertEqual(len(client.calls), index + 1)

    def test_api_timeout_does_not_retry(self):
        client = FakeClient([])
        with patch.object(client, "complete_json", side_effect=TimeoutError("offline injected timeout")) as call:
            result = self.run_review(client)
        call.assert_called_once()
        self.assertEqual(result["status"], "review_failed")
        self.assertIn("TimeoutError", result["errors"][0])

    def test_invalid_verification_rolls_back_and_retains_response(self):
        for fields in ({"resolved_issue_ids": []},
                       {"resolved_issue_ids": ["r1", "r1"]},
                       {"unresolved_issue_ids": ["r1"]},
                       {"resolved_issue_ids": ["unknown"]},
                       {"resolved_issue_ids": "r1"},
                       {"scene_id": "other"}, {"new_concerns": [123]}):
            bad = {**self.verify, **fields}
            self.assertTrue(validate_verification(self.report, bad))
            client = FakeClient([self.report, self.patch, bad])
            result = self.run_review(client)
            self.assertEqual(result["status"], "review_failed")
            self.assertEqual(result["plan"], self.plan)
            self.assertEqual(result["verification"], bad)
            self.assertEqual(len(client.calls), 3)

    def test_invalid_mode_or_input_does_not_call_client(self):
        client = FakeClient([])
        self.assertEqual(self.run_review(client, "baseline")["status"], "review_failed")
        self.plan["shots"][0]["duration_s"] = 0
        self.assertEqual(self.run_review(client)["status"], "review_failed")
        self.assertEqual(client.calls, [])

    def test_unexpected_client_return_logged_and_rejected(self):
        client = FakeClient([])
        with patch.object(client, "complete_json", return_value="not JSON"):
            with self.assertLogs("moodcut.review.trace", level="INFO") as logs:
                result = self.run_review(client)
        self.assertEqual(result["status"], "review_failed")
        events = [json.loads(record.getMessage()) for record in logs.records]
        self.assertEqual(events[1]["response"], "not JSON")
