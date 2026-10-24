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
                             get_review_prompt_hashes, validate_report, validate_verification,
                             ACTOR_REVIEW, ACTOR_REVIEW_V2, ACTOR_REVIEW_V3, validate_actor_review_result)


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



def actor_software_case(mode='moodcut'):
    """Explicit software opinions/patches for structural checks, not model evidence."""
    root = Path(__file__).resolve().parents[1]
    data = json.loads((root / 'tests/fixtures/generated_contract.json').read_text(encoding='utf-8'))
    scene, plan = data['scene'], data['initial_plan']
    manifest = json.loads((root / 'tests/fixtures/assets.json').read_text(encoding='utf-8'))
    plan['shots'][0]['dialogue'][0]['text'] = 'Here it is.'
    plan['shots'][0]['dialogue'].append({'character_id': 'b', 'text': 'Thank you.'})
    sid = plan['shots'][0]['shot_id']
    reports = [{'schema_version': '1.0', 'scene_id': scene['scene_id'], 'mode': mode,
        'actor_id': actor, 'issues': [{'issue_id': 'local-1', 'shot_id': sid, 'line_indices': [index],
        'dimension': 'naturalness', 'severity': 'minor', 'evidence': 'Software feedback on my own line.',
        'suggestion': 'Software-only revision marker.'}]} for index, actor in enumerate(('a', 'b'))]
    lines = [{'character_id': 'a', 'text': 'Software revised A.'},
             {'character_id': 'b', 'text': 'Software revised B.'}]
    writer = {'patch': {'schema_version': '1.0', 'scene_id': scene['scene_id'], 'edits': [
        {'issue_id': 'actor-1:local-1', 'shot_id': sid, 'set': {'dialogue': lines}}]},
        'feedback_disposition': {'addressed_issue_ids': ['actor-1:local-1', 'actor-2:local-1'],
                                'unaddressed_issue_ids': [], 'unaddressed_reasons': {}}}
    return scene, plan, manifest, reports, writer


def call_actor(case, client, mode='moodcut'):
    return review_and_revise(*case[:3], client, mode=mode, output_mode='generated',
        review_protocol=ACTOR_REVIEW, project_root=Path(__file__).resolve().parents[1])


@pytest.mark.parametrize('mode', ['generic_review', 'moodcut'])
def test_actor_feedback_independent_owned_and_unified_once(mode, monkeypatch):
    monkeypatch.setattr('socket.socket.connect', lambda *a, **k: pytest.fail('No network allowed'))
    case = actor_software_case(mode)
    before = deepcopy(case)
    client = FakeClient(case[3] + [case[4]])
    result = call_actor(case, client, mode)
    assert result['status'] == 'applied' and case == before
    assert [c['stage'] for c in client.calls] == ['actor_critique', 'actor_critique', 'actor_revise']
    assert result['actor_reports'] == [{'actor_id': a['actor_id'], 'response': a} for a in case[3]]
    for position, actor in enumerate(('a', 'b')):
        payload = json.loads(client.calls[position]['user'])
        assert payload['actor']['id'] == actor and payload['plan'] == case[1]
        assert all(case[1]['shots'][0]['dialogue'][r['line_index']]['character_id'] == actor
                   for r in payload['own_dialogue'] if r['shot_id'] == case[1]['shots'][0]['shot_id'])
        assert 'actor_reports' not in payload and 'report' not in payload
    rewrite = json.loads(client.calls[2]['user'])
    assert rewrite['actor_reports'] == result['actor_reports']
    assert len(rewrite['issues_by_shot']) == 1 and len(rewrite['issues_by_shot'][0]['issues']) == 2
    assert [i['issue_id'] for i in result['report']['issues']] == ['actor-1:local-1', 'actor-2:local-1']
    assert result['verification'] is None and result['actor_endorsement'] == 'not_requested'
    assert result['actor_feedback_status'] == 'writer_addressed'
    assert validate_actor_review_result(*case[:3], result, mode=mode,
        project_root=Path(__file__).resolve().parents[1]) == []


def test_actor_empty_first_does_not_suppress_second_and_silent_actor_is_valid():
    case = actor_software_case()
    case[3][0]['issues'] = []
    case[4]['patch']['edits'][0]['issue_id'] = 'actor-2:local-1'
    case[4]['patch']['edits'][0]['set']['dialogue'][0] = deepcopy(case[1]['shots'][0]['dialogue'][0])
    case[4]['feedback_disposition']['addressed_issue_ids'] = ['actor-2:local-1']
    client = FakeClient(case[3] + [case[4]])
    assert call_actor(case, client)['status'] == 'applied' and len(client.calls) == 3
    case = actor_software_case()
    for shot in case[1]['shots']:
        shot['dialogue'] = [line for line in shot['dialogue'] if line['character_id'] == 'a']
    for report in case[3]: report['issues'] = []
    client = FakeClient(case[3])
    result = call_actor(case, client)
    assert result['status'] == 'unchanged' and len(client.calls) == 2
    assert json.loads(client.calls[1]['user'])['own_dialogue'] == []


@pytest.mark.parametrize('bad', ['wrong_actor', 'other_line', 'bool_index', 'unknown_line', 'duplicate_index', 'duplicate_issue'])
def test_actor_invalid_ownership_stops_before_other_actor_or_writer(bad):
    case = actor_software_case()
    report = case[3][0]
    if bad == 'wrong_actor': report['actor_id'] = 'b'
    elif bad == 'other_line': report['issues'][0]['line_indices'] = [1]
    elif bad == 'bool_index': report['issues'][0]['line_indices'] = [False]
    elif bad == 'unknown_line': report['issues'][0]['line_indices'] = [100]
    elif bad == 'duplicate_index': report['issues'][0]['line_indices'] = [0, 0]
    else: report['issues'].append(deepcopy(report['issues'][0]))
    client = FakeClient(case[3] + [case[4]])
    result = call_actor(case, client)
    assert result['status'] == 'review_failed' and result['plan'] == case[1]
    assert len(client.calls) == 1 and len(result['actor_reports']) == 1


def test_actor_second_failure_preserves_first_report_and_never_rewrites():
    case = actor_software_case()
    case[3][1]['actor_id'] = 'a'
    client = FakeClient(case[3] + [case[4]])
    result = call_actor(case, client)
    assert result['status'] == 'review_failed' and len(client.calls) == 2
    assert result['actor_reports'][0]['response'] == case[3][0]
    assert result['writer_response'] is None


@pytest.mark.parametrize('bad', ['drop_feedback', 'fake_addressed', 'delete_actor', 'change_speaker', 'illegal_field', 'duplicate_shot', 'no_reason'])
def test_actor_writer_cannot_silently_veto_or_overwrite_feedback(bad):
    case = actor_software_case()
    writer = case[4]
    if bad == 'drop_feedback': writer['feedback_disposition']['addressed_issue_ids'].pop()
    elif bad == 'fake_addressed': writer['patch']['edits'][0]['set']['dialogue'][1]['text'] = case[1]['shots'][0]['dialogue'][1]['text']
    elif bad == 'delete_actor': writer['patch']['edits'][0]['set']['dialogue'].pop()
    elif bad == 'change_speaker': writer['patch']['edits'][0]['set']['dialogue'][1]['character_id'] = 'a'
    elif bad == 'illegal_field': writer['patch']['edits'][0]['set']['duration_s'] = 99
    elif bad == 'duplicate_shot': writer['patch']['edits'].append(deepcopy(writer['patch']['edits'][0]))
    else:
        writer['feedback_disposition']['addressed_issue_ids'].pop()
        writer['feedback_disposition']['unaddressed_issue_ids'] = ['actor-2:local-1']
    client = FakeClient(case[3] + [writer])
    result = call_actor(case, client)
    assert result['status'] in ('review_failed', 'rejected') and result['plan'] == case[1]
    assert len(client.calls) == 3 and len(result['actor_reports']) == 2
    assert result['writer_response'] == writer


def test_actor_disagreement_with_reason_remains_a_viewable_pending_draft():
    case = actor_software_case()
    writer = case[4]
    writer['patch']['edits'][0]['set']['dialogue'][1] = deepcopy(case[1]['shots'][0]['dialogue'][1])
    writer['feedback_disposition'] = {'addressed_issue_ids': ['actor-1:local-1'],
        'unaddressed_issue_ids': ['actor-2:local-1'],
        'unaddressed_reasons': {'actor-2:local-1': 'Software example: conflicting suggestion, retained for viewing.'}}
    result = call_actor(case, FakeClient(case[3] + [writer]))
    assert result['status'] == 'applied' and result['actor_feedback_status'] == 'has_unaddressed'
    assert result['actor_endorsement'] == 'not_requested'
    assert result['feedback_disposition'] == writer['feedback_disposition']
    changed = deepcopy(result); changed['actor_endorsement'] = 'approved'
    assert validate_actor_review_result(*case[:3], changed, mode='moodcut')



def test_actor_pipeline_routes_writer_to_planner_and_binds_saved_feedback(tmp_path, monkeypatch):
    import io
    from unittest.mock import Mock
    from moodcut import pipeline
    from moodcut.client import OpenRouterClient, RoleRoutedClient
    from moodcut.video_generation import get_video_template_sha256
    from moodcut.evaluation import validate_generated_comparison
    root = Path(__file__).resolve().parents[1]
    case = actor_software_case('generic_review')
    scene, initial, manifest = case[:3]
    for asset in manifest['assets']:
        asset['source_url'] = 'https://example.invalid/' + asset['asset_id'] + '.png'
    director = {'scene_id': scene['scene_id'], 'tone': scene['tone'],
                'beat_order': [b['id'] for b in scene['beats']], 'approach': 'Software replay only'}
    staged = {'scene_id': scene['scene_id'], 'scene_direction': initial['scene_direction'],
        'segments': [{k: shot[k] for k in ('beat_ids', 'duration_s', 'direction')} | {'description': 'Software segment'}
                     for shot in initial['shots']]}
    other = actor_software_case('moodcut')
    responses = [director, staged, initial] + case[3] + [case[4]] + other[3] + [other[4]]
    def envelope(response):
        return io.BytesIO(json.dumps({'id': 'software-envelope', 'model': 'software-response-model',
            'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(response)}}],
            'usage': {'prompt_tokens': 100, 'completion_tokens': 20, 'cost': .001}}).encode())
    send = Mock(side_effect=[envelope(r) for r in responses])
    monkeypatch.setattr('moodcut.client.build_opener', Mock(return_value=Mock(open=send)))
    clients = [OpenRouterClient(api_key='software-key', model=model, allow_paid=True, max_cost_usd=.1,
        input_price_per_million=1, output_price_per_million=1) for model in ('test/planning', 'test/review')]
    client = RoleRoutedClient(*clients, max_cost_usd=.1)
    settings = pipeline.read_json(root / 'tests/fixtures/generated_contract.json')['settings']
    settings['model'] = pipeline.read_json(root / 'configs/video.json')['model']
    out = tmp_path / 'actor-source'
    block = pipeline.run_experiment(scene, manifest, client, out_dir=out, project_root=root, render=False,
        output_mode='generated', generation_settings=settings, template_sha256=get_video_template_sha256(),
        review_protocol=ACTOR_REVIEW)
    assert block['status'] == 'prepared' and send.call_count == 9
    assert block['review_protocol'] == ACTOR_REVIEW
    assert [json.loads(c.args[0].data)['model'] for c in send.call_args_list] == (
        ['test/planning'] * 3 + ['test/review'] * 2 + ['test/planning'] + ['test/review'] * 2 + ['test/planning'])
    assert all(r.get('actor_endorsement') == 'not_requested' for r in block['runs'][1:])
    pipeline._load_generated_block(out, root)
    prepared = pipeline.prepare_generated_run(out, out_dir=tmp_path / 'requests', project_root=root,
                                              pricing_config=root / 'configs/video.json')
    assert prepared['status'] == 'prepared_offline' and send.call_count == 9
    plans = {r['condition']: pipeline.read_json(out / r['condition'] / 'final.json') for r in block['runs']}
    mixed = deepcopy(block['runs']); mixed[0].pop('review_protocol')
    errors = validate_generated_comparison(mixed, scene=scene, initial=initial, plans=plans,
        manifest=manifest, settings=settings, template_sha256=get_video_template_sha256(), project_root=root)
    assert any('consistent review protocol' in e for e in errors)
    path = out / 'generic_review/review.json'
    saved = path.read_text(encoding='utf-8');review = json.loads(saved)
    review['actor_reports'].pop()
    path.write_text(json.dumps(review), encoding='utf-8')
    with pytest.raises(ValueError, match='one report per actor'):
        pipeline._load_generated_block(out, root)
    path.write_text(saved, encoding='utf-8')
    review['actor_reports'] = json.loads(saved)['actor_reports']
    review['actor_reports'][0]['response']['issues'][0]['line_indices'] = [1]
    path.write_text(json.dumps(review), encoding='utf-8')
    with pytest.raises(ValueError, match='only that actor'):
        pipeline._load_generated_block(out, root)
    path.write_text(saved, encoding='utf-8')
    assert send.call_count == 9


def omission_case(mode="moodcut", omitted=("b",)):
    """Developer-authored structural example; never a paid Agent fallback."""
    case = actor_software_case(mode)
    addressed, unaddressed, reasons = [], [], {}
    for index, actor in enumerate(("a", "b"), 1):
        issue = f"actor-{index}:local-1"
        if actor in omitted:
            unaddressed.append(issue)
            reasons[issue] = "Software-only writer omission reason."
            case[4]["patch"]["edits"][0]["set"]["dialogue"][index-1] = deepcopy(case[1]["shots"][0]["dialogue"][index-1])
        else:
            addressed.append(issue)
    if not addressed:
        case[4]["patch"]["edits"] = []
    case[4]["feedback_disposition"] = {"addressed_issue_ids": addressed,
        "unaddressed_issue_ids": unaddressed, "unaddressed_reasons": reasons}
    return case


def confirmation_response(case, actor, decision="accept_omission", mode="moodcut"):
    candidate = deepcopy(case[1])
    if case[4]["patch"]["edits"]:
        candidate["shots"][0]["dialogue"] = deepcopy(case[4]["patch"]["edits"][0]["set"]["dialogue"])
    from moodcut.contracts import json_hash
    prefix = f"actor-{('a', 'b').index(actor)+1}:"
    ids = [i for i in case[4]["feedback_disposition"]["unaddressed_issue_ids"] if i.startswith(prefix)]
    return {"schema_version": "1.0", "scene_id": case[0]["scene_id"], "mode": mode, "actor_id": actor,
        "initial_plan_sha256": json_hash(case[1]), "candidate_plan_sha256": json_hash(candidate),
        "decisions": [{"issue_id": i, "decision": decision, "reason": "Software-only actor decision, not a quality judgment."} for i in ids]}


def call_confirmed(case, client, mode="moodcut"):
    return review_and_revise(*case[:3], client, mode=mode, output_mode="generated",
        review_protocol=ACTOR_REVIEW_V2, project_root=Path(__file__).resolve().parents[1])


def bounded_software_case(mode="moodcut", omitted=("a", "b"), first="maintain_objection", final="maintain_objection"):
    """Explicit developer-authored replies for bounded-protocol regression, not Agent evidence."""
    case = omission_case(mode, omitted)
    responses = deepcopy(case[3]) + [deepcopy(case[4])]
    for actor in omitted:
        responses.append(confirmation_response(case, actor, first, mode))
    if first == "maintain_objection" and omitted:
        second = deepcopy(actor_software_case(mode)[4])
        ids = [f"actor-{('a', 'b').index(a)+1}:local-1" for a in omitted]
        second["objection_responses"] = {i: "Software-only second revision responding to this actor." for i in ids}
        responses.append(second)
        second_case = list(deepcopy(case))
        second_case[4] = second
        for actor in omitted:
            response = confirmation_response(second_case, actor, final, mode)
            issue = f"actor-{('a', 'b').index(actor)+1}:local-1"
            response["decisions"] = [{"issue_id": issue, "decision": final, "reason": "Software-only final actor view."}]
            responses.append(response)
    def by_shot(writer):
        value = {"dialogue_by_shot": {e["shot_id"]: deepcopy(e["set"]["dialogue"]) for e in writer["patch"]["edits"]},
                 "feedback_disposition": deepcopy(writer["feedback_disposition"])}
        if "objection_responses" in writer:
            value["objection_responses"] = deepcopy(writer["objection_responses"])
        return value
    responses = [by_shot(r) if "patch" in r else r for r in responses]
    case = (*case[:4], by_shot(case[4]))
    return case, responses


def call_bounded(case, client, mode="moodcut"):
    return review_and_revise(*case[:3], client, mode=mode, output_mode="generated",
        review_protocol=ACTOR_REVIEW_V3, project_root=Path(__file__).resolve().parents[1])


@pytest.mark.parametrize("mode", ["generic_review", "moodcut"])
def test_v3_writer_returns_one_dialogue_per_shot_for_both_actor_issues(mode):
    case = actor_software_case(mode)
    writer = {"dialogue_by_shot": {case[1]["shots"][0]["shot_id"]:
        deepcopy(case[4]["patch"]["edits"][0]["set"]["dialogue"])},
        "feedback_disposition": deepcopy(case[4]["feedback_disposition"])}
    client = FakeClient(case[3] + [writer])
    result = call_bounded(case, client, mode)
    assert result["status"] == "applied", result["errors"]
    assert result["writer_response"] == writer
    assert len(result["patch"]["edits"]) == 1
    assert result["patch"]["edits"][0]["set"]["dialogue"] == writer["dialogue_by_shot"][case[1]["shots"][0]["shot_id"]]
    assert len(result["feedback_disposition"]["addressed_issue_ids"]) == 2 and len(client.calls) == 3
    assert validate_actor_review_result(*case[:3], result, mode=mode) == []


@pytest.mark.parametrize("bad", ["legacy_edits", "unknown_shot", "feedback_free_shot", "array", "alternatives", "wrong_speaker", "missing_line", "false_addressed", "extra_field"])
def test_v3_shot_writer_fails_closed_without_guessing_or_merging(bad):
    case, replies = bounded_software_case(omitted=(), first="accept_candidate")
    writer = replies[2]
    sid = case[1]["shots"][0]["shot_id"]
    if bad == "legacy_edits": writer = deepcopy(actor_software_case()[4]); writer["patch"]["edits"].append(deepcopy(writer["patch"]["edits"][0])); replies[2] = writer
    elif bad == "unknown_shot": writer["dialogue_by_shot"]["not-a-shot"] = deepcopy(writer["dialogue_by_shot"][sid])
    elif bad == "feedback_free_shot": writer["dialogue_by_shot"][case[1]["shots"][1]["shot_id"]] = deepcopy(case[1]["shots"][1]["dialogue"])
    elif bad == "array": writer["dialogue_by_shot"] = [writer["dialogue_by_shot"]]
    elif bad == "alternatives": writer["dialogue_by_shot"][sid] = [writer["dialogue_by_shot"][sid], writer["dialogue_by_shot"][sid]]
    elif bad == "wrong_speaker": writer["dialogue_by_shot"][sid][1]["character_id"] = "a"
    elif bad == "missing_line": writer["dialogue_by_shot"][sid].pop()
    elif bad == "false_addressed": writer["dialogue_by_shot"] = {}
    else: writer["duration_s"] = 99
    client = FakeClient(replies)
    result = call_bounded(case, client)
    assert result["status"] == "review_failed" and result["plan"] == case[1] and len(client.calls) == 3
    assert result["negotiation_rounds"][0]["writer_response"] == writer


def test_v3_duplicate_json_shot_keys_are_rejected_before_conversion():
    from moodcut.client import _strict_json
    with pytest.raises(ValueError, match="duplicate JSON key"):
        _strict_json('{"dialogue_by_shot":{"S":[],"S":[]},"feedback_disposition":{}}')


def test_v3_saved_raw_shot_dialogue_and_derived_patch_must_agree():
    case, replies = bounded_software_case()
    result = call_bounded(case, FakeClient(replies))
    changed = deepcopy(result)
    sid = case[1]["shots"][0]["shot_id"]
    changed["negotiation_rounds"][0]["writer_response"]["dialogue_by_shot"] = {sid: deepcopy(case[1]["shots"][0]["dialogue"])}
    assert validate_actor_review_result(*case[:3], changed, mode="moodcut")
    changed = deepcopy(result); changed["writer_output_contract"] = "issue_patch_v1"
    assert validate_actor_review_result(*case[:3], changed, mode="moodcut")


def test_v3_old_writer_contract_prompt_identity_remains_available():
    import hashlib
    root = Path(__file__).resolve().parents[1] / "src/moodcut/prompts"
    old = get_review_prompt_hashes(output_mode="generated", review_protocol=ACTOR_REVIEW_V3, writer_output_contract="issue_patch_v1")
    new = get_review_prompt_hashes(output_mode="generated", review_protocol=ACTOR_REVIEW_V3)
    assert old["revise"] == hashlib.sha256((root / "review_actor_revise.txt").read_text(encoding="utf-8").encode()).hexdigest()
    assert old["negotiate"] == hashlib.sha256((root / "review_actor_negotiate.txt").read_text(encoding="utf-8").encode()).hexdigest()
    assert old["revise"] != new["revise"] and old["negotiate"] != new["negotiate"]
    assert all(old[k] == new[k] for k in ("generic", "moodcut", "confirm"))


@pytest.mark.parametrize("mode", ["generic_review", "moodcut"])
@pytest.mark.parametrize("final", ["maintain_objection", "accept_candidate"])
def test_v3_final_disagreement_is_viewable_after_two_real_revision_attempts(mode, final):
    case, responses = bounded_software_case(mode, final=final)
    original = deepcopy(case)
    client = FakeClient(responses)
    result = call_bounded(case, client, mode)
    assert result["status"] == "applied" and result["errors"] == [] and len(client.calls) == 8
    assert result["negotiation_round_count"] == 2 and len(result["negotiation_rounds"]) == 2
    assert result["negotiation_status"] == ("disputed" if final == "maintain_objection" else "complete")
    assert result["actor_confirmation_status"] == ("disputed" if final == "maintain_objection" else "accepted")
    assert bool(result["disputed_issue_ids"]) == (final == "maintain_objection")
    assert result["feedback_disposition"]["unaddressed_issue_ids"] == []
    assert result["actor_endorsement"] == "not_requested" and result["verification"] is None
    assert result["negotiation_rounds"][0]["writer_response"] == case[4]
    assert result["negotiation_rounds"][0]["disputed_issue_ids"] == ["actor-1:local-1", "actor-2:local-1"]
    assert validate_actor_review_result(*case[:3], result, mode=mode) == [] and case == original
    writer_payload = json.loads(client.calls[5]["user"])
    assert writer_payload["previous_round"] == result["negotiation_rounds"][0]
    assert writer_payload["required_objection_ids"] == result["negotiation_rounds"][0]["disputed_issue_ids"]
    for call in [client.calls[i] for i in (3, 4, 6, 7)]:
        payload = json.loads(call["user"])
        actor = payload["actor"]["id"]
        assert all(i["actor_id"] == actor for i in payload["issues_to_confirm"])
        assert "actor_reports" not in payload and "actor_confirmations" not in payload
        assert payload["actor_report"] == case[3][('a', 'b').index(actor)]
    assert json.loads(client.calls[6]["user"])["previous_own_decisions"] == responses[3]["decisions"]


@pytest.mark.parametrize("empty,omitted", [(True, ()), (False, ()), (False, ("b",))])
def test_v3_no_objection_needs_no_extra_round(empty, omitted):
    case, responses = bounded_software_case(omitted=omitted, first="accept_candidate")
    if empty:
        for response in case[3]:
            response["issues"] = []
        responses = case[3]
    client = FakeClient(responses)
    result = call_bounded(case, client)
    assert result["status"] in ("applied", "unchanged")
    assert result["negotiation_round_count"] == (0 if empty else 1)
    assert len(client.calls) == (2 if empty else 3 + len(omitted))
    assert validate_actor_review_result(*case[:3], result, mode="moodcut") == []


def test_v3_invalid_original_actor_report_is_failed_not_no_issues():
    case, responses = bounded_software_case()
    responses[0]["actor_id"] = "b"
    client = FakeClient(responses)
    result = call_bounded(case, client)
    assert result["status"] == "review_failed" and result["negotiation_status"] == "failed"
    assert result["negotiation_rounds"] == [] and len(client.calls) == 1


@pytest.mark.parametrize("bad", ["no_response", "same_dialogue", "omit_again", "drop_prior", "non_dialogue", "bad_speaker"])
def test_v3_second_writer_cannot_repeat_its_veto_or_bypass_constraints(bad):
    case, responses = bounded_software_case(omitted=("b",))
    writer = responses[4]
    if bad == "no_response": writer["objection_responses"] = {}
    elif bad == "same_dialogue": writer["dialogue_by_shot"][case[1]["shots"][0]["shot_id"]][1] = deepcopy(case[1]["shots"][0]["dialogue"][1])
    elif bad == "omit_again":
        writer["feedback_disposition"] = deepcopy(case[4]["feedback_disposition"])
        writer["dialogue_by_shot"] = deepcopy(case[4]["dialogue_by_shot"])
    elif bad == "drop_prior":
        writer["feedback_disposition"]["addressed_issue_ids"].remove("actor-1:local-1")
        writer["feedback_disposition"]["unaddressed_issue_ids"] = ["actor-1:local-1"]
        writer["feedback_disposition"]["unaddressed_reasons"] = {"actor-1:local-1": "Software-only rejected prior change"}
        writer["dialogue_by_shot"][case[1]["shots"][0]["shot_id"]][0] = deepcopy(case[1]["shots"][0]["dialogue"][0])
    elif bad == "non_dialogue": writer["dialogue_by_shot"][case[1]["shots"][0]["shot_id"]] = {"duration_s": 99}
    else: writer["dialogue_by_shot"][case[1]["shots"][0]["shot_id"]][1]["character_id"] = "a"
    client = FakeClient(responses)
    result = call_bounded(case, client)
    assert result["status"] == "review_failed" and result["plan"] == case[1]
    assert result["negotiation_status"] == "failed" and len(client.calls) == 5
    assert result["negotiation_rounds"][1]["writer_response"] == writer and client.remaining == 1


@pytest.mark.parametrize("round_index", [1, 2])
@pytest.mark.parametrize("bad", ["wrong_owner", "wrong_hash", "missing_issue", "other_issue", "empty_reason", "missing_reply"])
def test_v3_hard_confirmation_errors_stop_without_retry(round_index, bad):
    case, responses = bounded_software_case()
    slot = 3 if round_index == 1 else 6
    response = responses[slot]
    if bad == "wrong_owner": response["actor_id"] = "b"
    elif bad == "wrong_hash": response["candidate_plan_sha256"] = "0" * 64
    elif bad == "missing_issue": response["decisions"] = []
    elif bad == "other_issue": response["decisions"][0]["issue_id"] = "actor-2:local-1"
    elif bad == "empty_reason": response["decisions"][0]["reason"] = " "
    else: responses = responses[:slot]
    client = FakeClient(responses)
    result = call_bounded(case, client)
    assert result["status"] == "review_failed" and result["plan"] == case[1]
    assert result["actor_confirmation_status"] == "failed" and len(client.calls) == slot + 1
    assert len(result["negotiation_rounds"]) == round_index


@pytest.mark.parametrize("bad", ["drop_round", "third_round", "missing_final_reply", "wrong_candidate", "hide_dispute", "fake_approval", "skip_revision"])
def test_v3_saved_source_cannot_hide_rounds_disagreements_or_actual_candidate(bad):
    case, responses = bounded_software_case()
    result = call_bounded(case, FakeClient(responses))
    if bad == "drop_round": result["negotiation_rounds"].pop(0)
    elif bad == "third_round": result["negotiation_rounds"].append(deepcopy(result["negotiation_rounds"][-1]))
    elif bad == "missing_final_reply": result["negotiation_rounds"][-1]["actor_confirmations"].pop()
    elif bad == "wrong_candidate": result["negotiation_rounds"][0]["writer_candidate_plan"] = deepcopy(result["plan"])
    elif bad == "hide_dispute": result["disputed_issue_ids"] = []
    elif bad == "fake_approval": result["actor_endorsement"] = "approved"
    else: result["negotiation_rounds"] = result["negotiation_rounds"][:1]
    assert validate_actor_review_result(*case[:3], result, mode="moodcut")


@pytest.mark.parametrize("outcome", ["disputed", "accepted", "unknown_cost", "over_budget", "http_error", "json_error"])
def test_v3_pipeline_routes_nineteen_calls_and_enforces_source_and_cost_gates(tmp_path, monkeypatch, outcome):
    import io
    from unittest.mock import Mock
    from urllib.error import HTTPError
    from moodcut import pipeline
    from moodcut.client import OpenRouterClient, RoleRoutedClient
    from moodcut.video_generation import get_video_template_sha256
    from moodcut.evaluation import validate_generated_comparison
    root = Path(__file__).resolve().parents[1]
    monkeypatch.setattr("socket.socket.connect", lambda *a, **k: pytest.fail("Real network is forbidden"))
    decision = "accept_candidate" if outcome == "accepted" else "maintain_objection"
    case, branch = bounded_software_case("generic_review", final=decision)
    _, other = bounded_software_case("moodcut", final=decision)
    scene, initial, manifest = case[:3]
    for asset in manifest["assets"]:
        asset["source_url"] = "https://example.invalid/" + asset["asset_id"] + ".png"
    director = {"scene_id": scene["scene_id"], "tone": scene["tone"], "beat_order": [b["id"] for b in scene["beats"]], "approach": "Software only"}
    staged = {"scene_id": scene["scene_id"], "scene_direction": initial["scene_direction"], "segments": [
        {k:s[k] for k in ("beat_ids", "duration_s", "direction")} | {"description": "Software segment"} for s in initial["shots"]]}
    envelopes = []
    for index, response in enumerate([director, staged, initial] + branch + other):
        cost = None if outcome == "unknown_cost" and index == 9 else .2 if outcome == "over_budget" and index == 9 else .001
        envelopes.append(HTTPError("https://example.invalid", 503, "Software failure", {}, None)
            if outcome == "http_error" and index == 9 else io.BytesIO(json.dumps({
                "id": "software-only", "model": "software-response", "choices": [
                    {"finish_reason": "stop", "message": {"content": '{"broken":' if outcome == "json_error" and index == 9 else json.dumps(response)}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 20, "cost": cost}}).encode()))
    send = Mock(side_effect=envelopes)
    monkeypatch.setattr("moodcut.client.build_opener", Mock(return_value=Mock(open=send)))
    clients = [OpenRouterClient(api_key="software-key", model=model, allow_paid=True, max_cost_usd=.1,
        input_price_per_million=1, output_price_per_million=1) for model in ("test/planning", "test/review")]
    client = RoleRoutedClient(*clients, max_cost_usd=.1)
    settings = pipeline.read_json(root / "tests/fixtures/generated_contract.json")["settings"]
    settings["model"] = pipeline.read_json(root / "configs/video.json")["model"]
    out = tmp_path / "bounded-source"
    block = pipeline.run_experiment(scene, manifest, client, out_dir=out, project_root=root, render=False,
        output_mode="generated", generation_settings=settings, template_sha256=get_video_template_sha256(),
        review_protocol=ACTOR_REVIEW_V3)
    for call in block['planning']['call_records']:
        assert (out / call['response_artifact']['body_path']).is_file()
    for row in block['runs']:
        for call in row['call_records']:
            assert (out / row['condition'] / call['response_artifact']['body_path']).is_file()
    if outcome == 'json_error':
        failed=block['runs'][1]['call_records'][-1]
        assert failed['parse_error']['kind']=='syntax_error' and failed['provider_cost_usd']==.001
        assert (out/'generic_review'/failed['response_artifact']['content_path']).read_text()=='{"broken":'
    if outcome not in ("disputed", "accepted"):
        assert block["status"] == "failed" and send.call_count == 10 and client.stopped
        assert block["runs"][1]["negotiation_status"] == "failed"
        assert block["runs"][2]["review_status"] == "not_started"
        review = pipeline.read_json(out / "generic_review/review.json")
        assert len(review["negotiation_rounds"]) == 2 and review["negotiation_rounds"][0]["disputed_issue_ids"]
        with pytest.raises(ValueError, match="prepared"):
            pipeline.prepare_generated_run(out, out_dir=tmp_path / "blocked", project_root=root,
                pricing_config=root / "configs/video.json")
        assert not (tmp_path / "blocked").exists()
        return
    assert block["status"] == "prepared" and send.call_count == 19 and not client.stopped
    roles = ["test/planning"] * 3 + (["test/review"] * 2 + ["test/planning"] + ["test/review"] * 2
             + ["test/planning"] + ["test/review"] * 2) * 2
    assert [json.loads(c.args[0].data)["model"] for c in send.call_args_list] == roles
    assert all(r["negotiation_round_count"] == 2 for r in block["runs"][1:])
    assert all(bool(r["disputed_issue_ids"]) == (outcome == "disputed") for r in block["runs"][1:])
    prepared = pipeline.prepare_generated_run(out, out_dir=tmp_path / "prepared", project_root=root,
        pricing_config=root / "configs/video.json")
    assert prepared["status"] == "prepared_offline" and send.call_count == 19
    plans = {c: pipeline.read_json(out / c / "final.json") for c in ("baseline", "generic_review", "moodcut")}
    options = dict(scene=scene, initial=initial, plans=plans, manifest=manifest, settings=settings,
                   template_sha256=get_video_template_sha256(), project_root=root)
    assert validate_generated_comparison(block["runs"], **options) == []
    for field, value in (("negotiation_status", "failed"), ("negotiation_round_count", 3),
                         ("confirmation_issue_ids", []), ("actor_confirmation_status", "failed")):
        records = deepcopy(block["runs"])
        records[1][field] = value
        assert any("bounded actor negotiation" in e for e in validate_generated_comparison(records, **options))
    records = deepcopy(block["runs"]); records[0]["review_protocol"] = ACTOR_REVIEW_V2
    assert any("consistent review protocol" in e for e in validate_generated_comparison(records, **options))
    review_path = out / "generic_review/review.json"
    saved = review_path.read_text(encoding="utf-8")
    for bad in ("missing_reply", "round_count", "call_sequence"):
        review = json.loads(saved)
        run_path = out / "generic_review/run.json"
        run_saved = run_path.read_text(encoding="utf-8")
        block_path = out / "block.json"
        block_saved = block_path.read_text(encoding="utf-8")
        if bad == "missing_reply":
            review["negotiation_rounds"][-1]["actor_confirmations"].pop()
            review_path.write_text(json.dumps(review), encoding="utf-8")
        else:
            modified = json.loads(block_saved)
            row = modified["runs"][1]
            if bad == "round_count": row["negotiation_round_count"] = 1
            else: row["call_records"].pop()
            run_path.write_text(json.dumps(row), encoding="utf-8")
            block_path.write_text(json.dumps(modified), encoding="utf-8")
        with pytest.raises(ValueError):
            pipeline._load_generated_block(out, root)
        review_path.write_text(saved, encoding="utf-8")
        run_path.write_text(run_saved, encoding="utf-8")
        block_path.write_text(block_saved, encoding="utf-8")
    pipeline._load_generated_block(out, root)
    assert send.call_count == 19


@pytest.mark.parametrize("mode", ["generic_review", "moodcut"])
def test_v2_only_corresponding_actor_can_accept_its_omission(mode):
    case = omission_case(mode)
    response = confirmation_response(case, "b", mode=mode)
    before = deepcopy(case)
    client = FakeClient(case[3] + [case[4], response])
    result = call_confirmed(case, client, mode)
    assert result["status"] == "applied" and result["actor_confirmation_status"] == "accepted"
    assert result["actor_feedback_status"] == "has_unaddressed" and result["actor_endorsement"] == "not_requested"
    assert result["actor_confirmations"] == [{"actor_id": "b", "response": response}] and case == before
    assert [c["stage"] for c in client.calls] == ["actor_critique", "actor_critique", "actor_revise", "actor_confirm"]
    payload = json.loads(client.calls[-1]["user"])
    assert payload["actor"]["id"] == "b" and payload["actor_report"] == case[3][1]
    assert payload["initial_plan"] == case[1] and payload["revised_plan"] == result["plan"]
    assert [i["issue_id"] for i in payload["unaddressed_issues"]] == ["actor-2:local-1"]
    assert payload["unaddressed_issues"][0]["writer_reason"] == case[4]["feedback_disposition"]["unaddressed_reasons"]["actor-2:local-1"]
    assert "actor_reports" not in payload and "actor_confirmations" not in payload
    assert validate_actor_review_result(*case[:3], result, mode=mode) == []


def test_v2_objection_blocks_finalization_but_keeps_candidate_and_both_positions():
    case = omission_case()
    response = confirmation_response(case, "b", "maintain_objection")
    client = FakeClient(case[3] + [case[4], response])
    result = call_confirmed(case, client)
    assert result["status"] == "review_failed" and result["actor_confirmation_status"] == "disputed"
    assert result["plan"] == case[1] and result["writer_candidate_plan"] != case[1]
    assert result["writer_response"] == case[4] and result["actor_reports"][1]["response"] == case[3][1]
    assert result["actor_confirmations"][0]["response"] == response and len(client.calls) == 4
    assert any("maintains objection" in e for e in result["errors"])


def test_v2_groups_all_omitted_issues_per_actor_in_at_most_two_calls():
    case = omission_case(omitted=("a", "b"))
    extra = deepcopy(case[3][1]["issues"][0]);extra["issue_id"] = "local-2"
    case[3][1]["issues"].append(extra)
    case[4]["feedback_disposition"]["unaddressed_issue_ids"].append("actor-2:local-2")
    case[4]["feedback_disposition"]["unaddressed_reasons"]["actor-2:local-2"] = "Second software-only reason."
    responses = [confirmation_response(case, a) for a in ("a", "b")]
    client = FakeClient(case[3] + [case[4]] + responses)
    result = call_confirmed(case, client)
    assert result["status"] == "unchanged" and result["actor_confirmation_status"] == "accepted"
    assert len(client.calls) == 5 and [r["actor_id"] for r in result["actor_confirmations"]] == ["a", "b"]
    assert len(json.loads(client.calls[-1]["user"])["unaddressed_issues"]) == 2
    assert all("actor_confirmations" not in json.loads(c["user"]) for c in client.calls[-2:])


@pytest.mark.parametrize("bad", ["wrong_actor", "other_issue", "missing_issue", "duplicate_issue", "wrong_candidate",
    "wrong_initial", "wrong_scene", "wrong_mode", "patch", "empty_reason", "invalid_decision"])
def test_v2_invalid_confirmation_cannot_release_writer_omission(bad):
    case = omission_case()
    response = confirmation_response(case, "b")
    if bad == "wrong_actor": response["actor_id"] = "a"
    elif bad == "other_issue": response["decisions"][0]["issue_id"] = "actor-1:local-1"
    elif bad == "missing_issue": response["decisions"] = []
    elif bad == "duplicate_issue": response["decisions"].append(deepcopy(response["decisions"][0]))
    elif bad == "wrong_candidate": response["candidate_plan_sha256"] = "0"*64
    elif bad == "wrong_initial": response["initial_plan_sha256"] = "0"*64
    elif bad == "wrong_scene": response["scene_id"] = "other"
    elif bad == "wrong_mode": response["mode"] = "generic_review"
    elif bad == "patch": response["patch"] = case[4]["patch"]
    elif bad == "empty_reason": response["decisions"][0]["reason"] = " "
    else: response["decisions"][0]["decision"] = True
    client = FakeClient(case[3] + [case[4], response])
    result = call_confirmed(case, client)
    assert result["status"] == "review_failed" and result["actor_confirmation_status"] == "failed"
    assert result["plan"] == case[1] and result["actor_confirmations"][0]["response"] == response
    assert len(client.calls) == 4 and result["writer_response"] == case[4]


def test_v2_invalid_first_confirmation_stops_before_second_actor_and_does_not_retry():
    case = omission_case(omitted=("a", "b"))
    wrong = confirmation_response(case, "a");wrong["actor_id"] = "b"
    client = FakeClient(case[3] + [case[4], wrong, confirmation_response(case, "b")])
    result = call_confirmed(case, client)
    assert result["status"] == "review_failed" and len(client.calls) == 4 and client.remaining == 1
    client = FakeClient(case[3] + [case[4]])
    result = call_confirmed(case, client)
    assert result["status"] == "review_failed" and result["actor_confirmation_status"] == "failed"
    assert len(client.calls) == 4 and result["actor_confirmations"] == [] and result["writer_candidate_plan"] == case[1]


@pytest.mark.parametrize("empty", [False, True])
def test_v2_no_omission_has_no_confirmation_or_extra_call(empty):
    case = actor_software_case()
    if empty:
        for report in case[3]:report["issues"] = []
    client = FakeClient(case[3] + ([] if empty else [case[4]]))
    result = call_confirmed(case, client)
    assert result["status"] == ("unchanged" if empty else "applied")
    assert result["actor_confirmation_status"] == "not_needed" and result["actor_confirmations"] == []
    assert len(client.calls) == (2 if empty else 3)
    assert validate_actor_review_result(*case[:3], result, mode="moodcut") == []


def test_v2_source_checks_cannot_be_satisfied_by_a_writer_status_or_other_candidate():
    case = omission_case()
    result = call_confirmed(case, FakeClient(case[3] + [case[4], confirmation_response(case, "b")]))
    for change in ("missing", "disputed", "candidate", "missing_candidate", "endorsement"):
        tampered = deepcopy(result)
        if change == "missing":tampered["actor_confirmations"] = []
        elif change == "disputed":tampered["actor_confirmations"][0]["response"]["decisions"][0]["decision"] = "maintain_objection"
        elif change == "candidate":tampered["writer_candidate_plan"] = case[1]
        elif change == "missing_candidate":tampered.pop("writer_candidate_plan")
        else:tampered["actor_endorsement"] = "approved"
        assert validate_actor_review_result(*case[:3], tampered, mode="moodcut")
    assert set(get_review_prompt_hashes(output_mode="generated", review_protocol=ACTOR_REVIEW)) == {"generic", "moodcut", "revise"}
    v2 = get_review_prompt_hashes(output_mode="generated", review_protocol=ACTOR_REVIEW_V2)
    assert set(v2) == {"generic", "moodcut", "revise", "confirm"}
    assert {k:v for k,v in v2.items() if k!="confirm"} == get_review_prompt_hashes(output_mode="generated", review_protocol=ACTOR_REVIEW)


@pytest.mark.parametrize("outcome", ["accepted", "disputed", "unknown_cost"])
def test_v2_pipeline_routes_confirmations_and_rejects_missing_or_disputed_source(tmp_path, monkeypatch, outcome):
    import io
    from unittest.mock import Mock
    from moodcut import pipeline
    from moodcut.client import OpenRouterClient, RoleRoutedClient
    from moodcut.video_generation import get_video_template_sha256
    from moodcut.evaluation import validate_generated_comparison
    root = Path(__file__).resolve().parents[1]
    monkeypatch.setattr("socket.socket.connect", lambda *a, **k: pytest.fail("No real network"))
    case = omission_case("generic_review");other = omission_case("moodcut")
    scene, initial, manifest = case[:3]
    for asset in manifest["assets"]:asset["source_url"] = "https://example.invalid/"+asset["asset_id"]+".png"
    director = {"scene_id": scene["scene_id"], "tone": scene["tone"], "beat_order": [b["id"] for b in scene["beats"]], "approach": "Software only"}
    staged = {"scene_id": scene["scene_id"], "scene_direction": initial["scene_direction"], "segments": [
        {k:s[k] for k in ("beat_ids", "duration_s", "direction")} | {"description": "Software segment"} for s in initial["shots"]]}
    confirmation = confirmation_response(case, "b", "maintain_objection" if outcome=="disputed" else "accept_omission", "generic_review")
    responses = [director, staged, initial] + case[3] + [case[4], confirmation] + other[3] + [other[4], confirmation_response(other, "b")]
    envelopes = []
    for index, response in enumerate(responses):
        cost = None if outcome=="unknown_cost" and index==6 else .001
        envelopes.append(io.BytesIO(json.dumps({"id": "software-only", "model": "software-response", "choices": [
            {"finish_reason": "stop", "message": {"content": json.dumps(response)}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 20, "cost": cost}}).encode()))
    send = Mock(side_effect=envelopes)
    monkeypatch.setattr("moodcut.client.build_opener", Mock(return_value=Mock(open=send)))
    clients = [OpenRouterClient(api_key="software-key", model=model, allow_paid=True, max_cost_usd=.1,
        input_price_per_million=1, output_price_per_million=1) for model in ("test/planning", "test/review")]
    client = RoleRoutedClient(*clients, max_cost_usd=.1)
    settings = pipeline.read_json(root/"tests/fixtures/generated_contract.json")["settings"]
    settings["model"] = pipeline.read_json(root/"configs/video.json")["model"]
    out = tmp_path/"source"
    block = pipeline.run_experiment(scene, manifest, client, out_dir=out, project_root=root, render=False,
        output_mode="generated", generation_settings=settings, template_sha256=get_video_template_sha256(), review_protocol=ACTOR_REVIEW_V2)
    if outcome!="accepted":
        assert block["status"] == "failed" and send.call_count == 7
        assert block["runs"][1]["actor_confirmation_status"] == ("disputed" if outcome=="disputed" else "failed")
        assert block["runs"][2]["review_status"] == "not_started" and client.stopped
        with pytest.raises(ValueError, match="prepared"):
            pipeline.prepare_generated_run(out, out_dir=tmp_path/"blocked", project_root=root, pricing_config=root/"configs/video.json")
        assert not (tmp_path/"blocked").exists()
        return
    assert block["status"] == "prepared" and send.call_count == 11
    assert [json.loads(c.args[0].data)["model"] for c in send.call_args_list] == (
        ["test/planning"]*3 + ["test/review"]*2 + ["test/planning", "test/review"] + ["test/review"]*2 + ["test/planning", "test/review"])
    prepared = pipeline.prepare_generated_run(out, out_dir=tmp_path/"prepared", project_root=root, pricing_config=root/"configs/video.json")
    assert prepared["status"] == "prepared_offline" and send.call_count == 11
    mixed = deepcopy(block["runs"]);mixed[0]["review_protocol"] = ACTOR_REVIEW
    plans = {c:pipeline.read_json(out/c/"final.json") for c in ("baseline", "generic_review", "moodcut")}
    assert any("consistent review protocol" in e for e in validate_generated_comparison(mixed, scene=scene, initial=initial,
        plans=plans, manifest=manifest, settings=settings, template_sha256=get_video_template_sha256(), project_root=root))
    for forged in ("disputed", "not_needed", None):
        bad = deepcopy(block["runs"]);bad[1]["actor_confirmation_status"] = forged
        assert any("corresponding-actor confirmation" in e for e in validate_generated_comparison(bad,
            scene=scene, initial=initial, plans=plans, manifest=manifest, settings=settings,
            template_sha256=get_video_template_sha256(), project_root=root))
    path = out/"generic_review/review.json";saved = path.read_text(encoding="utf-8")
    review = json.loads(saved);review["actor_confirmations"] = []
    path.write_text(json.dumps(review),encoding="utf-8")
    with pytest.raises(ValueError, match="one omission confirmation"):
        pipeline._load_generated_block(out,root)
    path.write_text(saved,encoding="utf-8")
    pipeline._load_generated_block(out,root)
    assert send.call_count == 11
