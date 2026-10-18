"""Task-local synthetic data; not shared fixtures or model evidence."""
import unittest
import json
import hashlib
import pytest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
from moodcut.client import FakeClient
from moodcut.reviewer import (MAX_OUTPUT_TOKENS, review_and_revise,
                             get_review_prompt_hashes, validate_report, validate_verification)


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


def _review_case_data(output_mode):
    """Minimal reconstruction of the duplicate-shot error; no private runs/model evidence."""
    root = Path(__file__).resolve().parent / "fixtures"
    if output_mode == "generated":
        data = json.loads((root / "generated_contract.json").read_text(encoding="utf-8"))
        scene, plan = data["scene"], data["initial_plan"]
    else:
        scene, plan = [json.loads((root / f"{name}.json").read_text(encoding="utf-8")) for name in ("scene", "plan")]
    manifest = json.loads((root / "assets.json").read_text(encoding="utf-8"))
    # Four opinions, but the fourth shares the second shot. The original
    # failure was edits[3]: conflicting or duplicate edit; keep that rule.
    report = {"schema_version": "1.0", "scene_id": scene["scene_id"], "mode": "moodcut", "issues": [
        {"issue_id": f"q{i+1}", "shot_id": plan["shots"][index]["shot_id"], "dimension": "tone",
         "severity": "minor", "evidence": "Synthetic concern about this line.",
         "suggestion": "Consider a restrained dialogue revision."} for i, index in enumerate((0, 1, 2, 1))]}
    edits = [{"issue_id": f"q{i+1}", "shot_id": shot["shot_id"], "set": {"dialogue": [
        {"character_id": scene["characters"][0]["id"], "text": f"Software revision {i+1}."}]}}
        for i, shot in enumerate(plan["shots"])]
    patch_data = {"schema_version": "1.0", "scene_id": scene["scene_id"], "edits": edits}
    verification = {"scene_id": scene["scene_id"], "resolved_issue_ids": ["q1", "q2", "q3", "q4"],
                    "unresolved_issue_ids": [], "new_concerns": []}
    return scene, plan, manifest, report, patch_data, verification, output_mode


@pytest.fixture(params=("animatic", "generated"))
def review_case(request, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr("socket.socket.connect", lambda *a, **k: pytest.fail("No real network in review tests"))
    return _review_case_data(request.param)


@pytest.fixture
def generated_review_case(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr("socket.socket.connect", lambda *a, **k: pytest.fail("No real network in review tests"))
    return _review_case_data("generated")


def call_review(case, client, *, mode="moodcut"):
    scene, plan, manifest, *_rest, output_mode = case
    return review_and_revise(scene, plan, manifest, client, mode=mode,
                             project_root=Path(__file__).resolve().parents[1], output_mode=output_mode)


@pytest.mark.parametrize("mode", ("generic_review", "moodcut"))
def test_grouped_opinions_retain_all_ids_and_verify_the_returned_plan(review_case, mode):
    scene, plan, manifest, report, patch_data, verification, output_mode = review_case
    report["mode"] = mode
    before = deepcopy(review_case)
    client = FakeClient([report, patch_data, verification])
    result = call_review(review_case, client, mode=mode)
    assert result["status"] == "applied" and review_case == before
    assert [c["stage"] for c in client.calls] == ["critique", "revise", "verify"]
    assert all(c["max_output_tokens"] == MAX_OUTPUT_TOKENS for c in client.calls)
    revision = json.loads(client.calls[1]["user"])
    assert [len(g["issues"]) for g in revision["issues_by_shot"]] == [1, 2, 1]
    assert [i["issue_id"] for i in revision["issues_by_shot"][1]["issues"]] == ["q2", "q4"]
    assert revision["report"] == report
    checked = json.loads(client.calls[2]["user"])
    assert checked["plan"] == plan and checked["revised_plan"] == result["plan"]
    assert checked["report"] == report and result["verification"] == verification
    assert json.loads(client.calls[0]["user"])["scene"]["tone"] == scene["tone"]
    names = ("generic" if mode == "generic_review" else "moodcut", "revise", "verify")
    hashes = get_review_prompt_hashes(output_mode=output_mode)
    assert [hashlib.sha256(c["system"].encode("utf-8")).hexdigest() for c in client.calls] == [hashes[n] for n in names]
    if output_mode == "generated":
        from moodcut.contracts import assert_dialogue_only_revision
        assert_dialogue_only_revision(plan, result["plan"])
        assert revision["output_mode"] == "generated"


def test_fourth_edit_for_same_shot_is_still_rejected_before_verify(review_case):
    _scene, plan, _manifest, report, patch_data, verification, _mode = review_case
    fourth = deepcopy(patch_data["edits"][1])
    fourth["issue_id"] = "q4"
    patch_data["edits"].append(fourth)
    client = FakeClient([report, patch_data, verification])
    result = call_review(review_case, client)
    assert result["status"] == "rejected" and result["plan"] == plan
    assert "edits[3]: conflicting or duplicate edit" in result["errors"]
    assert result["patch"] == patch_data and client.remaining == 1 and len(client.calls) == 2


@pytest.mark.parametrize("path", ("no_issues", "empty_patch", "same_value"))
def test_valid_unchanged_paths_keep_actual_call_counts(review_case, path):
    _scene, plan, _manifest, report, patch_data, verification, _mode = review_case
    if path == "no_issues":
        report["issues"] = []
    elif path == "empty_patch":
        patch_data["edits"] = []
    else:
        for edit, shot in zip(patch_data["edits"], plan["shots"]):
            edit["set"]["dialogue"] = deepcopy(shot["dialogue"])
    verification.update(resolved_issue_ids=[], unresolved_issue_ids=[i["issue_id"] for i in report["issues"]])
    client = FakeClient([report, patch_data, verification])
    result = call_review(review_case, client)
    assert result["status"] == "unchanged" and result["plan"] == plan
    assert len(client.calls) == (1 if path == "no_issues" else 3)
    assert (result["verification"] is None) == (path == "no_issues")


def test_verification_cannot_omit_unreferenced_grouped_issue(review_case):
    _scene, plan, _manifest, report, patch_data, verification, _mode = review_case
    verification["resolved_issue_ids"].remove("q4")
    client = FakeClient([report, patch_data, verification])
    result = call_review(review_case, client)
    assert result["status"] == "review_failed" and result["plan"] == plan
    assert result["patch"] == patch_data and result["verification"] == verification
    assert len(client.calls) == 3 and len(json.loads(client.calls[2]["user"])["report"]["issues"]) == 4


@pytest.mark.parametrize("field", ("narration", "direction", "duration_s", "visuals"))
def test_actual_generated_patch_policy_rejects_non_dialogue_before_verify(generated_review_case, field):
    _scene, plan, _manifest, report, patch_data, verification, _mode = generated_review_case
    patch_data["edits"][1]["set"] = {field: "forbidden change"}
    client = FakeClient([report, patch_data, verification])
    result = call_review(generated_review_case, client)
    assert result["status"] == "rejected" and result["plan"] == plan and result["patch"] == patch_data
    assert len(client.calls) == 2 and result["verification"] is None and client.remaining == 1


@pytest.mark.parametrize("output_mode", ("animatic", "unknown", None))
def test_generated_review_requires_explicit_valid_output_mode(generated_review_case, output_mode):
    scene, plan, manifest, _report, _patch, _verify, _mode = generated_review_case
    client = FakeClient([])
    result = review_and_revise(scene, plan, manifest, client, mode="moodcut", output_mode=output_mode,
                              project_root=Path(__file__).resolve().parents[1])
    assert result["status"] == "review_failed" and result["plan"] == plan and client.calls == []


@pytest.mark.parametrize("count", (0, 1, 2))
def test_generated_and_legacy_transport_failure_do_not_retry(review_case, count):
    _scene, plan, _manifest, report, patch_data, verification, _mode = review_case
    client = FakeClient([report, patch_data, verification][:count])
    result = call_review(review_case, client)
    assert result["status"] == "review_failed" and result["plan"] == plan
    assert len(client.calls) == count + 1 and result["errors"]


@pytest.mark.parametrize("change", ("scene", "direction", "narration", "duration", "crop", "order", "extension"))
def test_generated_reviewer_guards_actual_candidate_before_verify(generated_review_case, monkeypatch, change):
    from moodcut import patches
    review_case = generated_review_case
    _scene, plan, _manifest, report, patch_data, verification, output_mode = review_case
    def faulty_patch(*args, **kwargs):
        candidate = deepcopy(plan)
        if change == "scene":
            candidate["scene_direction"] += " tampered"
        elif change == "direction":
            candidate["shots"][0]["direction"] += " tampered"
        elif change == "narration":
            candidate["shots"][0]["narration"] += " tampered"
        elif change == "duration":
            candidate["shots"][0]["duration_s"] += 1
        elif change == "crop":
            candidate["shots"][0]["visuals"][0]["crop"] = "center_close"
        elif change == "order":
            candidate["shots"].reverse()
        else:
            candidate["future_extension"] = {"changed": True}
        return {"plan": candidate, "status": "applied", "errors": []}
    monkeypatch.setattr(patches, "apply_patch", faulty_patch)
    client = FakeClient([report, patch_data, verification])
    result = call_review(review_case, client)
    assert result["status"] == "rejected" and result["plan"] == plan and result["errors"]
    assert len(client.calls) == 2 and result["verification"] is None


def test_actual_planner_reviewer_pipeline_prepares_three_conditions(tmp_path, monkeypatch):
    from moodcut import pipeline
    from moodcut.contracts import assert_dialogue_only_revision
    root = Path(__file__).resolve().parents[1]
    data = pipeline.read_json(root / "tests/fixtures/generated_contract.json")
    scene, plan = data["scene"], data["initial_plan"]
    manifest = pipeline.read_json(root / "tests/fixtures/assets.json")
    staged = [{"scene_id": scene["scene_id"], "tone": scene["tone"],
               "beat_order": [b["id"] for b in scene["beats"]], "approach": "Software planning intent."},
              {"scene_id": scene["scene_id"], "scene_direction": plan["scene_direction"], "segments": [
                  {"beat_ids": s["beat_ids"], "description": s["narration"], "direction": s["direction"],
                   "duration_s": s["duration_s"]} for s in plan["shots"]]}, plan]
    report = {"schema_version": "1.0", "scene_id": scene["scene_id"], "mode": "generic_review", "issues": [
        {"issue_id": i, "shot_id": "s2", "dimension": "tone", "severity": "minor",
         "evidence": "Software concern.", "suggestion": "Consider a dialogue change."} for i in ("g1", "g2")]}
    revision = {"schema_version": "1.0", "scene_id": scene["scene_id"], "edits": [
        {"issue_id": "g1", "shot_id": "s2", "set": {"dialogue": [{"character_id": "b", "text": "Who else read it?"}]}}]}
    verified = {"scene_id": scene["scene_id"], "resolved_issue_ids": ["g1", "g2"], "unresolved_issue_ids": [], "new_concerns": []}
    empty = {"schema_version": "1.0", "scene_id": scene["scene_id"], "mode": "moodcut", "issues": []}
    client = FakeClient([*staged, report, revision, verified, empty])
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr("socket.socket.connect", lambda *a, **k: pytest.fail("No real network"))
    output = tmp_path / "actual-script-chain"
    block = pipeline.run_experiment(scene, manifest, client, out_dir=output, project_root=root,
        output_mode="generated", generation_settings=data["settings"], template_sha256=data["template_sha256"])
    assert block["status"] == "prepared" and block["planning"]["calls"] == 3
    assert [r["review_calls"] for r in block["runs"]] == [0, 3, 1]
    assert [r["review_status"] for r in block["runs"]] == ["not_applicable", "applied", "unchanged"]
    assert len({r["shared_generation_sha256"] for r in block["runs"]}) == 1
    assert len(client.calls) == 7 and all(r["video_path"] is None and r["generation_posts"] == 0 for r in block["runs"])
    assert all(r["comparison_status"] == "not_checked" for r in block["runs"])
    for row in block["runs"]:
        final = pipeline.read_json(output / row["condition"] / "final.json")
        assert_dialogue_only_revision(plan, final)
        assert row["prompt_hashes"] == get_review_prompt_hashes(output_mode="generated") | {"video_template": data["template_sha256"]}
    checked = json.loads(client.calls[5]["user"])["revised_plan"]
    assert checked == pipeline.read_json(output / "generic_review/final.json")
    assert pipeline.read_json(output / "generic_review/review.json")["plan"] == checked
    # The real P1 source gate now accepts the real P2/P3 script chain. No P4
    # compiler, video client or paid/model call is required or substituted.
    _path, saved, source = pipeline._load_generated_block(output, root)
    assert saved == block and source["plans"]["generic_review"] == checked
