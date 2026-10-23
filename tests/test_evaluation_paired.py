"""Synthetic arithmetic and temporary media test the protocol, not emotion quality."""
import copy
import csv
import tempfile
import unittest
from pathlib import Path
import pytest

from moodcut.evaluation import build_assignments, export_blind_items, summarize


def records_fixture():
    rows = build_assignments([dict(scene_id="synthetic_a"), dict(scene_id="synthetic_b")],
                             replicates=1, tones=["suspicious"],
                             conditions=["baseline", "generic_review", "moodcut"])
    for index, row in enumerate(rows):
        row.update(initial_plan_sha256="a" * 64, render_status="rendered",
                   review_status="unchanged", source_kind="synthetic", item_id=f"item{index}",
                   calls=0, input_tokens=0, output_tokens=0, elapsed_s=1,
                   estimated_cost_usd=0, provider_cost_usd=0)
    return rows


def rating(item, tone="suspicious", rater="rater_a", value=3):
    return dict(rater_id=rater, item_id=item, perceived_tone=tone, confidence=value,
                naturalness=value, story_clarity=value, overstatement=value)


class PairedEvaluationTests(unittest.TestCase):
    def test_assignments_ids_stable_across_condition_order_and_scene_order(self):
        first = build_assignments([dict(scene_id="a"), dict(scene_id="b")], replicates=2,
                                  tones=["suspicious", "hostile"], conditions=["baseline", "moodcut"])
        second = build_assignments([dict(scene_id="b"), dict(scene_id="a")], replicates=2,
                                   tones=["hostile", "suspicious"], conditions=["moodcut", "baseline"])
        self.assertEqual(len(first), 16)
        self.assertEqual({r["run_id"] for r in first}, {r["run_id"] for r in second})
        self.assertEqual(first, build_assignments([dict(scene_id="a"), dict(scene_id="b")],
                          replicates=2, tones=["suspicious", "hostile"], conditions=["baseline", "moodcut"]))
        for args in (dict(replicates=0, tones=["hostile"], conditions=["baseline"]),
                     dict(replicates=True, tones=["hostile"], conditions=["baseline"]),
                     dict(replicates=1, tones=["hostile", "hostile"], conditions=["baseline"]),
                     dict(replicates=1, tones=["hostile"], conditions=["unknown"])):
            with self.subTest(args=args), self.assertRaises(ValueError):
                build_assignments([dict(scene_id="a")], **args)

    def test_equal_clip_means_uncertain_and_failed_coverage(self):
        rows = records_fixture()
        rows[-1].update(render_status="render_failed", review_status="review_failed",
                        failure_kind="timeout", calls=1, provider_cost_usd=None,
                        estimated_cost_usd=0.2, input_tokens=10, output_tokens=None)
        votes = [rating("item0"), rating("item1"),
                 rating("item1", "hostile", "rater_b"),
                 rating("item1", "uncertain", "rater_c"), rating("item2", value=5),
                 rating("item3", "uncertain"), rating("item4")]
        result = summarize(rows, votes)
        generic = result["by_condition"]["generic_review"]
        # Generic clip means are 1/3 and 1; equal clip average is 2/3, not 2/4.
        self.assertAlmostEqual(generic["equal_clip_means"]["tone_accuracy"], 2 / 3)
        self.assertEqual(generic["coverage"]["ratings"], 4)
        baseline = result["by_condition"]["baseline"]
        self.assertEqual(baseline["equal_clip_means"]["tone_accuracy"], 0.5)
        coverage = result["overall"]["coverage"]
        self.assertEqual(coverage["planned_runs"], 6)
        self.assertEqual(coverage["rendered_runs"], 5)
        self.assertEqual(coverage["rated_clips"], 5)
        self.assertEqual(coverage["missing_ratings"], 1)
        self.assertEqual(coverage["uncertain_ratings"], 2)
        self.assertEqual(coverage["review_failed_runs"], 1)
        self.assertEqual(coverage["timeout_runs"], 1)
        self.assertEqual(coverage["known_zero_call_runs"], 5)
        common = result["common_moodcut_generic"]
        self.assertEqual(common["common_evaluable_blocks"], 1)
        self.assertEqual(common["planned_paired_blocks"], 2)
        self.assertEqual(common["common_coverage"], 0.5)
        self.assertAlmostEqual(common["mean_moodcut_minus_generic"]["tone_accuracy"], 2 / 3)
        usage = result["overall"]["usage"]
        self.assertIsNone(usage["provider_cost_usd"]["total"])
        self.assertEqual(usage["provider_cost_usd"]["unknown_runs"], 1)
        self.assertEqual(usage["estimated_cost_usd"]["total"], 0.2)
        self.assertEqual(usage["calls"]["total"], 1)
        self.assertFalse(result["planning_costs_included"])

    def test_empty_and_no_ratings_denominators(self):
        result = summarize([], [])
        self.assertIsNone(result["overall"]["equal_clip_means"]["tone_accuracy"])
        self.assertIsNone(result["common_moodcut_generic"]["common_coverage"])
        result = summarize(records_fixture(), [])
        self.assertEqual(result["overall"]["coverage"]["missing_ratings"], 6)
        self.assertIsNone(result["by_condition"]["moodcut"]["equal_clip_means"]["naturalness"])

    def test_bad_rating_rows_are_not_silently_dropped(self):
        valid = rating("item0")
        for bad in (valid | {"confidence": True}, valid | {"naturalness": "3.0"},
                    valid | {"story_clarity": 0}, valid | {"perceived_tone": "happy"},
                    valid | {"item_id": "unknown"}, valid | {"rater_id": ""},
                    {k: v for k, v in valid.items() if k != "confidence"}):
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, "row 2"):
                summarize(records_fixture(), [bad])
        with self.assertRaisesRegex(ValueError, "row 3.*duplicate"):
            summarize(records_fixture(), [valid, valid])
        string_csv = {k: str(v) for k, v in valid.items()}
        self.assertEqual(summarize(records_fixture(), [string_csv])["overall"]
                         ["equal_clip_means"]["confidence"], 3)
        rows = records_fixture()
        rows[0]["render_status"] = "render_failed"
        with self.assertRaisesRegex(ValueError, "rendered clip"):
            summarize(rows, [valid])

    def test_pairing_mismatches_duplicates_and_mixed_sources_rejected(self):
        rows = records_fixture()
        for mutate in (lambda r: r[1].update(initial_plan_sha256="b" * 64),
                       lambda r: r.append(copy.deepcopy(r[0])),
                       lambda r: r[1].update(source_kind="formal"),
                       lambda r: r[1].update(estimated_cost_usd=float("nan")),
                       lambda r: r[1].update(calls=True),
                       lambda r: r[1].update(initial_plan_sha256=None)):
            changed = copy.deepcopy(rows)
            mutate(changed)
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                summarize(changed, [])
        rows[0].update(render_status="not_rendered", initial_plan_sha256=None)
        summarize(rows, [])  # Failed/no-plan attempts stay in coverage, not comparison.

    def test_blind_export_copies_anonymous_files_and_separates_answer_key(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rows = records_fixture()
            rows[-1]["render_status"] = "render_failed"
            for index, row in enumerate(rows[:-1]):
                source = root / f"suspicious_moodcut_source_{index}.mp4"
                source.write_bytes(b"synthetic format-agnostic fixture " + bytes([index]))
                row["video_path"] = str(source)
            first = export_blind_items(rows, out_dir=root / "first", seed=17)
            second = export_blind_items(rows, out_dir=root / "second", seed=17)
            self.assertEqual(first["record_items"], second["record_items"])
            self.assertEqual(first["exported_clips"], 5)
            self.assertEqual(first["excluded_runs"], 1)
            public = Path(first["public_dir"])
            self.assertEqual(Path(first["private_key_path"]).parent.name, "PRIVATE")
            self.assertFalse(Path(first["private_key_path"]).is_relative_to(public))
            with Path(first["blind_items_path"]).open(encoding="utf-8", newline="") as handle:
                blind = list(csv.DictReader(handle))
            self.assertTrue(all(set(row) == {"item_id", "video_file"} for row in blind))
            self.assertTrue(all((public / row["video_file"]).is_file() for row in blind))
            for path in public.glob("*.csv"):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("suspicious", text)
                self.assertNotIn("moodcut", text)
                self.assertNotIn("synthetic_a", text)
            with Path(first["ratings_path"]).open(encoding="utf-8", newline="") as handle:
                template = list(csv.DictReader(handle))
            self.assertTrue(all(row["perceived_tone"] == "" and row["rater_id"] == "" for row in template))
            mapping = {row["run_id"]: row["item_id"] for row in first["record_items"]}
            mapped = [dict(row, item_id=mapping.get(row["run_id"], row["item_id"])) for row in rows]
            summary = summarize(mapped, [rating(blind[0]["item_id"])])
            self.assertEqual(summary["overall"]["coverage"]["rated_clips"], 1)
            with self.assertRaises(FileExistsError):
                export_blind_items(rows, out_dir=root / "first", seed=17)

    def test_export_preflights_missing_videos_and_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "new"
            rows = records_fixture()
            rows[0]["video_path"] = str(Path(directory) / "missing.mp4")
            with self.assertRaises(ValueError):
                export_blind_items(rows, out_dir=out, seed=0)
            self.assertFalse(out.exists())
            rows[1]["initial_plan_sha256"] = "b" * 64
            with self.assertRaisesRegex(ValueError, "mismatch"):
                export_blind_items(rows, out_dir=out, seed=0)
            self.assertFalse(out.exists())



class GeneratedComparisonTests(unittest.TestCase):
    def setUp(self):
        from contextlib import chdir
        self.enterContext(chdir(Path(__file__).resolve().parents[1]))

    def fixture(self):
        import json
        root = Path(__file__).resolve().parents[1]
        f = json.loads((root / "tests/fixtures/generated_contract.json").read_text(encoding="utf-8"))
        assets = json.loads((root / f["manifest_file"]).read_text(encoding="utf-8"))
        # Local reference assets only; no model calls or generated media.
        return f["run_records"], dict(scene=f["scene"], initial=f["initial_plan"],
            plans=f["condition_plans"], manifest=assets, settings=f["settings"], template_sha256=f["template_sha256"])

    def check(self, records, args):
        from moodcut.evaluation import validate_generated_comparison
        return validate_generated_comparison(records, **args)

    def test_valid_fixture_preserves_every_input_and_status(self):
        records, args = self.fixture()
        before = copy.deepcopy((records, args))
        self.assertEqual(self.check(records, args), [])
        self.assertEqual((records, args), before)
        self.assertEqual(records[0]["comparison_status"], "not_checked")

    def test_declared_hashes_are_not_trusted(self):
        for field in ("initial_plan_sha256", "final_plan_sha256", "shared_generation_sha256", "video_model_id"):
            records, args = self.fixture()
            for record in records:
                record[field] = "a" * 64
            with self.subTest(field=field):
                self.assertTrue(any(field in e for e in self.check(records, args)))

    def test_non_dialogue_change_even_with_recomputed_claims(self):
        from moodcut.contracts import json_hash, shared_generation_sha256
        records, args = self.fixture()
        plan = args["plans"]["moodcut"]
        plan["shots"][0]["unexpected_extension"] = "changed action"
        records[2]["final_plan_sha256"] = json_hash(plan)
        records[2]["shared_generation_sha256"] = shared_generation_sha256(
            args["scene"], plan, args["manifest"], args["settings"], template_sha256=args["template_sha256"])
        self.assertTrue(any("non-dialogue" in e for e in self.check(records, args)))

    def test_shared_input_changes_require_new_identity(self):
        for change in ("seed", "voice", "template", "asset_url"):
            records, args = self.fixture()
            if change == "seed": args["settings"]["seed"] += 1
            elif change == "voice": args["settings"]["characters"][0]["voice"] += " changed"
            elif change == "template": args["template_sha256"] = "b" * 64
            else: args["manifest"]["assets"][0]["source_url"] = "https://example.org/changed.png"
            with self.subTest(change=change):
                self.assertTrue(self.check(records, args))

    def test_unchanged_requires_exact_initial_and_failures_rejected(self):
        from moodcut.contracts import json_hash
        records, args = self.fixture()
        records[1]["review_status"] = "unchanged"
        self.assertTrue(self.check(records, args))
        args["plans"]["generic_review"] = copy.deepcopy(args["initial"])
        records[1]["final_plan_sha256"] = json_hash(args["initial"])
        self.assertEqual(self.check(records, args), [])
        for status in ("rejected", "review_failed", "no_changes"):
            records[1]["review_status"] = status
            with self.subTest(status=status): self.assertTrue(self.check(records, args))

    def test_conditions_block_and_scope(self):
        for change in ("missing", "duplicate", "block", "source", "scope", "legacy", "failed"):
            records, args = self.fixture()
            if change == "missing": records.pop()
            elif change == "duplicate": records[2] = copy.deepcopy(records[1])
            elif change == "block": records[1]["block_id"] = "another"
            elif change == "source": records[1]["source_kind"] = "formal"
            elif change == "scope": records[1]["selected_shot_ids"] = [args["initial"]["shots"][0]["shot_id"]]
            elif change == "legacy": records[1]["schema_version"] = "1.0"
            else: records[1]["generation_status"] = "failed"
            with self.subTest(change=change): self.assertTrue(self.check(records, args))

    def test_unknown_costs_and_reuse_are_preserved_not_recounted(self):
        records, args = self.fixture()
        records[0]["provider_cost_usd"] = None
        records[1]["generation_jobs"] = [{"reused_from": {"run_id": records[0]["run_id"], "shot_id": "s1"}}]
        before = copy.deepcopy(records)
        self.assertEqual(self.check(records, args), [])
        self.assertEqual(records, before)
        report = summarize(records, [])
        self.assertIsNone(report["overall"]["usage"]["provider_cost_usd"]["total"])
        self.assertEqual(report["overall"]["coverage"]["planned_runs"], 3)

    def test_malformed_inputs_return_errors(self):
        records, args = self.fixture()
        for malformed in (None, {}, [None], [{"condition": []}]):
            with self.subTest(records=malformed): self.assertTrue(self.check(malformed, args))
        args["initial"]["shots"] = None
        self.assertTrue(self.check(records, args))



class GeneratedMediaFileTests(unittest.TestCase):
    def setUp(self):
        import hashlib
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.video = self.root / "film.mp4"
        # Deliberately not decodable: this test certifies bytes only, not video.
        self.video.write_bytes(b"synthetic file identity fixture")
        self.record = dict(schema_version="1.1", output_mode="generated",
            run_status="completed", generation_status="assembled_requires_manual_inspection",
            comparison_status="not_checked", provider_cost_usd=None, video_path="film.mp4",
            media_check=dict(video_path=str(self.video),
                             sha256=hashlib.sha256(self.video.read_bytes()).hexdigest()))

    def check(self):
        from moodcut.evaluation import validate_generated_media_file
        return validate_generated_media_file(self.record, project_root=self.root)

    def test_matching_bytes_preserve_record_and_unknown_cost(self):
        before = copy.deepcopy(self.record)
        self.assertEqual(self.check(), [])
        self.assertEqual(self.record, before)

    def test_replaced_deleted_and_directory_paths_rejected(self):
        self.video.write_bytes(b"replacement")
        self.assertTrue(any("bytes differ" in e for e in self.check()))
        self.video.unlink()
        self.assertTrue(self.check())
        self.video.mkdir()
        self.assertTrue(self.check())

    def test_wrong_path_hash_and_incomplete_status_rejected(self):
        for field, value in (("sha256", "f" * 64), ("sha256", None),
                             ("video_path", "another.mp4")):
            before = copy.deepcopy(self.record)
            self.record["media_check"][field] = value
            with self.subTest(field=field, value=value): self.assertTrue(self.check())
            self.record = before
        self.record["generation_status"] = "prepared_offline"
        self.assertTrue(self.check())

    def test_missing_or_malformed_evidence_rejected(self):
        from moodcut.evaluation import validate_generated_media_file
        for record in (None, {}, {**self.record, "media_check": []},
                       {**self.record, "video_path": None}):
            with self.subTest(record=record):
                self.assertTrue(validate_generated_media_file(record, project_root=self.root))


class GeneratedSourceBindingsTests(unittest.TestCase):
    def setUp(self):
        GeneratedMediaFileTests.setUp(self)
        from moodcut.contracts import json_hash
        request = {"prompt": "synthetic request", "seed": 1}
        self.compiled = {"condition": "baseline", "jobs": [
            {"shot_id": "s1", "request": request, "request_sha256": json_hash(request)}]}
        self.record.update(condition="baseline", selected_shot_ids=["s1"], generation_jobs=[
            dict(shot_id="s1", request_sha256=json_hash(request), status="downloaded",
                 video_path="film.mp4", media_check=copy.deepcopy(self.record["media_check"]))])

    def bindings(self):
        from moodcut.evaluation import validate_generated_source_bindings
        return validate_generated_source_bindings(self.record, self.compiled, project_root=self.root)

    def test_single_clip_binding_and_no_mutation(self):
        before = copy.deepcopy((self.record, self.compiled))
        self.assertEqual(self.bindings(), [])
        self.assertEqual((self.record, self.compiled), before)

    def test_changed_request_and_source_status(self):
        self.compiled["jobs"][0]["request"]["seed"] = 2
        self.assertTrue(any("request identity" in e for e in self.bindings()))
        self.record["generation_jobs"][0]["status"] = "in_progress"
        self.assertTrue(any("not downloaded" in e for e in self.bindings()))

    def test_assembly_sidecar_binds_order_bytes_and_snapshot(self):
        import json
        from moodcut.contracts import json_hash
        second = copy.deepcopy(self.compiled["jobs"][0]); second["shot_id"] = "s2"
        self.compiled["jobs"].append(second)
        job = copy.deepcopy(self.record["generation_jobs"][0]); job["shot_id"] = "s2"
        self.record["generation_jobs"].append(job)
        self.record["selected_shot_ids"].append("s2")
        self.assertTrue(self.bindings())  # Multi-shot assembly requires evidence.
        saved = {"sha256": self.record["media_check"]["sha256"], "source_clips": [
            {"shot_id": j["shot_id"], "request_sha256": j["request_sha256"],
             "sha256": j["media_check"]["sha256"]} for j in self.record["generation_jobs"]]}
        sidecar = self.root / "media_check.json"
        sidecar.write_text(json.dumps(saved), encoding="utf-8")
        self.record["media_check"].update(source_media_check_path="media_check.json",
                                         source_media_check_sha256=json_hash(saved))
        self.assertEqual(self.bindings(), [])
        saved["source_clips"].reverse()
        sidecar.write_text(json.dumps(saved), encoding="utf-8")
        errors = self.bindings()
        self.assertTrue(any("sidecar identity" in e for e in errors))
        self.assertTrue(any("clip/request order" in e for e in errors))

    def test_missing_duplicate_or_malformed_jobs(self):
        for jobs in ([], [None], [self.record["generation_jobs"][0]] * 2):
            before = copy.deepcopy(self.record)
            self.record["generation_jobs"] = jobs
            with self.subTest(jobs=jobs): self.assertTrue(self.bindings())
            self.record = before


class GeneratedReceiptBindingTests(unittest.TestCase):
    def setUp(self):
        import json
        from moodcut.contracts import json_hash
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (self.root / "receipts").mkdir()
        self.path = self.root / "receipts" / "job.json"
        self.receipt = dict(schema_version="1.1", model="synthetic-model",
            request_sha256="a" * 64, job_id="synthetic-job", status="downloaded",
            video_path="../clip.mp4", provider_cost_usd=None)
        self.path.write_text(json.dumps(self.receipt), encoding="utf-8")
        self.job = dict(receipt_path="receipts/job.json", receipt_sha256=json_hash(self.receipt),
            request_sha256="a" * 64, job_id="synthetic-job", status="downloaded",
            video_path="clip.mp4", provider_cost_usd=None)

    def check(self):
        from moodcut.evaluation import validate_generated_receipt_binding
        return validate_generated_receipt_binding(self.job, expected_model="synthetic-model",
                                                  project_root=self.root)

    def test_matching_relative_paths_and_unknown_cost_are_preserved(self):
        before = copy.deepcopy(self.job)
        saved = self.path.read_bytes()
        self.assertEqual(self.check(), [])
        self.assertEqual(self.job, before)
        self.assertEqual(self.path.read_bytes(), saved)

    def test_receipt_edits_rejected_even_if_snapshot_hash_updated(self):
        import json
        from moodcut.contracts import json_hash
        for field, value, diagnostic in (
                ("request_sha256", "b" * 64, "request identity"),
                ("model", "other-model", "model mismatch"),
                ("job_id", "other-job", "job_id mismatch"),
                ("status", "completed", "both be downloaded"),
                ("video_path", "other.mp4", "video_path mismatch"),
                ("schema_version", "2.0", "schema_version")):
            changed = {**self.receipt, field: value}
            self.path.write_text(json.dumps(changed), encoding="utf-8")
            self.job["receipt_sha256"] = json_hash(changed)
            with self.subTest(field=field):
                self.assertTrue(any(diagnostic in e for e in self.check()))

    def test_stale_snapshot_missing_and_malformed_receipts(self):
        import json
        self.path.write_text(json.dumps({**self.receipt, "provider_cost_usd": 1}), encoding="utf-8")
        self.assertTrue(any("saved receipt identity" in e for e in self.check()))
        for content in ("[]", "null", "not-json"):
            self.path.write_text(content, encoding="utf-8")
            with self.subTest(content=content): self.assertTrue(self.check())
        self.path.unlink()
        self.assertTrue(self.check())

    def test_malformed_job_and_missing_id_do_not_pass(self):
        from moodcut.evaluation import validate_generated_receipt_binding
        for job in (None, {}, {**self.job, "job_id": None}, {**self.job, "request_sha256": None}):
            with self.subTest(job=job):
                self.assertTrue(validate_generated_receipt_binding(job,
                    expected_model="synthetic-model", project_root=self.root))


class GeneratedMediaEvidenceTests(unittest.TestCase):
    def setUp(self):
        import json
        from moodcut.contracts import json_hash
        GeneratedSourceBindingsTests.setUp(self)
        self.record["video_model_id"] = "synthetic-model"
        source = self.compiled["jobs"][0]
        source["request"]["model"] = "synthetic-model"
        source["request_sha256"] = json_hash(source["request"])
        receipt = dict(schema_version="1.1", model="synthetic-model", job_id="test-job",
            status="downloaded", request_sha256=source["request_sha256"], video_path="film.mp4")
        self.receipt_path = self.root / "receipt.json"
        self.receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        self.record["generation_jobs"][0].update(request_sha256=source["request_sha256"],
            job_id="test-job", receipt_path="receipt.json", receipt_sha256=json_hash(receipt))

    def check(self):
        from moodcut.evaluation import validate_generated_media_evidence
        return validate_generated_media_evidence(self.record, self.compiled, project_root=self.root)

    def test_combined_valid_evidence_preserves_inputs(self):
        before = copy.deepcopy((self.record, self.compiled))
        self.assertEqual(self.check(), [])
        self.assertEqual((self.record, self.compiled), before)
        self.assertEqual(self.record["comparison_status"], "not_checked")

    def test_collects_file_and_receipt_failures_together(self):
        self.video.write_bytes(b"replacement")
        self.receipt_path.unlink()
        errors = self.check()
        self.assertTrue(any("bytes differ" in e for e in errors))
        self.assertTrue(any("receipt binding" in e for e in errors))

    def test_receipt_model_is_checked_against_compiled_request(self):
        import json
        from moodcut.contracts import json_hash
        receipt = json.loads(self.receipt_path.read_text(encoding="utf-8"))
        receipt["model"] = "wrong-model"
        self.receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        self.record["generation_jobs"][0]["receipt_sha256"] = json_hash(receipt)
        self.assertTrue(any("receipt model mismatch" in e for e in self.check()))
        self.record["video_model_id"] = "wrong-model"
        self.assertTrue(any("compiled model differs" in e for e in self.check()))

    def test_malformed_condition_still_returns_diagnostics(self):
        from moodcut.evaluation import validate_generated_media_evidence
        for condition in (None, {}, {"jobs": [None]}, {"jobs": []}):
            with self.subTest(condition=condition):
                self.assertTrue(validate_generated_media_evidence(
                    self.record, condition, project_root=self.root))


# Reuse P4's existing fixture without copying its orchestration or changing its files.
from test_video_generation import inspection_inputs


def test_p5_reads_actual_inspection_records(inspection_inputs):
    """Actual P1-P4 + P5, FakeClient, synthetic moving/audio media; no provider."""
    from test_video_generation import inspect_local, ROOT
    from moodcut.pipeline import read_json
    from moodcut.evaluation import validate_generated_media_evidence

    case = inspection_inputs
    inspection = inspect_local(case)
    assert inspection["status"] == "ready_requires_manual_inspection"
    records = read_json(case["output"] / "records/block.json")
    before = copy.deepcopy(records)
    compiled = {c["condition"]: c for c in case["bundle"]["conditions"]}
    assert len(records["runs"]) == 3
    for record in records["runs"]:
        assert validate_generated_media_evidence(
            record, compiled[record["condition"]], project_root=ROOT) == []
        assert record["comparison_status"] == "not_checked"
    assert records == before
    assert records["accounting"]["planning_counted_once"] is True
    # Hand-written fixture bills are not actual spending. P5 must not recount them.
    assert records["accounting"]["provider_cost_usd"] == .28
    assert [r["generation_posts"] for r in records["runs"]] == [2, 1, 1]
    assert any(j.get("reused_from") for r in records["runs"] for j in r["generation_jobs"])
    checks = read_json(case["output"] / "manual_checks.json")
    assert checks["status"] == "not_reviewed"
    assert all(item["audio_lipsync"] is None for item in checks["items"])

    # A receipt changed after P4 inspection must no longer pass P5's read check.
    job = records["runs"][0]["generation_jobs"][0]
    receipt_path = Path(job["receipt_path"])
    import json
    receipt = read_json(receipt_path)
    receipt["job_id"] = "changed-after-inspection"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    errors = validate_generated_media_evidence(
        records["runs"][0], compiled["baseline"], project_root=ROOT)
    assert any("saved receipt identity mismatch" in e for e in errors)
    assert any("receipt job_id mismatch" in e for e in errors)
    assert records == before


def test_p5_actual_unknown_cost_records_remain_unknown(inspection_inputs):
    """Legacy missing counters are unknown, not failed media or zero spending."""
    import json
    from test_video_generation import inspect_local, ROOT
    from moodcut.pipeline import read_json
    from moodcut.evaluation import validate_generated_media_evidence

    case = inspection_inputs
    receipt_path = case["evidence"].parent / "receipt-0-0.json"
    receipt = read_json(receipt_path)
    receipt.update(schema_version="1.0", provider_cost_usd=None)
    receipt.pop("download_attempts")
    receipt.pop("download_redirect_attempts")
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    assert inspect_local(case)["status"] == "ready_requires_manual_inspection"
    records = read_json(case["output"] / "records/block.json")
    before = copy.deepcopy(records)
    compiled = {c["condition"]: c for c in case["bundle"]["conditions"]}
    for record in records["runs"]:
        assert validate_generated_media_evidence(
            record, compiled[record["condition"]], project_root=ROOT) == []
        assert record["comparison_status"] == "not_checked"
    assert records == before
    assert records["accounting"]["provider_cost_usd"] is None
    assert records["accounting"]["real_http_calls"] is None
    assert records["accounting"]["known_subtotals"]["provider_cost_usd"] == .21
    assert records["runs"][0]["generation_jobs"][0]["missing_counters"] == [
        "download_attempts", "download_redirect_attempts"]
    # Existing statistics consume final runs once, with no fabricated ratings.
    report = summarize(records["runs"], [])
    assert report["overall"]["usage"]["provider_cost_usd"]["total"] is None
    assert report["overall"]["coverage"]["planned_runs"] == 3
    assert records == before


def test_p5_actual_failed_run_is_rejected_but_kept_in_summary(inspection_inputs):
    """Failed generation remains in the final ledger, with unknown spending."""
    import json
    from test_video_generation import inspect_local, ROOT
    from moodcut.pipeline import read_json
    from moodcut.evaluation import validate_generated_media_evidence

    case = inspection_inputs
    receipt_path = case["evidence"].parent / "receipt-0-0.json"
    receipt = read_json(receipt_path)
    receipt.update(status="failed", video_path=None, provider_cost_usd=None)
    receipt.pop("download_attempts")
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    assert inspect_local(case)["status"] == "failed"
    records = read_json(case["output"] / "records/block.json")
    before = copy.deepcopy(records)
    compiled = {c["condition"]: c for c in case["bundle"]["conditions"]}
    baseline = next(r for r in records["runs"] if r["condition"] == "baseline")
    assert baseline["run_status"] == "failed"
    assert baseline["comparison_status"] == "ineligible"
    assert validate_generated_media_evidence(baseline, compiled["baseline"], project_root=ROOT)
    assert not (case["output"] / "baseline/film.mp4").exists()
    for record in records["runs"]:
        if record["condition"] != "baseline":
            assert validate_generated_media_evidence(
                record, compiled[record["condition"]], project_root=ROOT) == []
    report = summarize(records["runs"], [])
    coverage = report["overall"]["coverage"]
    assert coverage["planned_runs"] == 3
    assert coverage["rendered_runs"] == 2
    # Legacy rendering coverage stays compatible; generation has its own axis.
    assert baseline["generation_status"] == "failed"
    assert baseline["failure_kind"] == "generation"
    assert coverage["render_failed_runs"] == 0
    assert coverage["render_pending_or_skipped_runs"] == 1
    assert report["overall"]["generation"]["by_status"]["failed"] == 1
    assert report["overall"]["generation"]["failed_run_causes"] == {"generation": 1}
    assert coverage["rated_clips"] == 0
    assert report["overall"]["usage"]["provider_cost_usd"]["total"] is None
    assert records["accounting"]["provider_cost_usd"] is None
    assert records == before


def _rewrite_fixture_json(path, value):
    """Fault injection is limited to the test-owned temporary artifacts."""
    import json
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _qualify_inspection(case):
    from moodcut.evaluation import qualify_generated_records
    from test_video_generation import ROOT
    return qualify_generated_records(case["output"] / "records", project_root=ROOT,
                                     pricing_config=ROOT / "configs/video.json")


def test_offline_qualification_and_cli_preserve_originals(inspection_inputs, monkeypatch, tmp_path):
    from test_video_generation import inspect_local, ROOT
    from moodcut.pipeline import read_json
    from moodcut.__main__ import main
    case = inspection_inputs
    inspect_local(case)
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    block = read_json(case["output"] / "records/block.json")
    # Root binding works outside the checkout, without process-wide chdir inside P5.
    monkeypatch.chdir(tmp_path)
    report = _qualify_inspection(case)
    assert report["comparison_status"] == "eligible"
    assert report["accounting_verified"] is True
    assert report["record_block"] == block
    assert all(c["comparison_status"] == "eligible" for c in report["conditions"])
    assert report["formal_inclusion_approved"] is False and report["export_enabled"] is False
    assert report["speech_and_visual_quality"] == "not_reviewed"
    assert all(v == 0 for v in report["activity"].values())
    assert {p: p.read_bytes() for p in before} == before
    output = tmp_path / "qualification"
    args = ["qualify-generated-records", "--project-root", str(ROOT), "--records",
            str(case["output"] / "records"), "--pricing-config", "configs/video.json", "--output", str(output)]
    assert main(args) == 0
    assert read_json(output / "qualification.json") == report
    assert main(args) == 1  # Never overwrite.
    assert main(["evaluate", "--project-root", str(ROOT), "--records",
                 str(case["output"] / "records/block.json"), "--blind-output", str(tmp_path / "blind")]) == 1
    assert not (tmp_path / "blind").exists()
    assert {p: p.read_bytes() for p in before} == before


@pytest.mark.parametrize("mutation", ["request", "reuse", "ledger", "receipt", "source", "file", "run", "snapshot"])
def test_offline_qualification_rejects_changed_evidence(inspection_inputs, mutation):
    from test_video_generation import inspect_local
    from moodcut.pipeline import read_json
    from moodcut.contracts import json_hash
    case = inspection_inputs
    inspect_local(case)
    records = case["output"] / "records"
    block = read_json(records / "block.json")
    if mutation == "request":
        bundle = read_json(case["prep"] / "bundle.json")
        job = bundle["conditions"][0]["jobs"][0]
        job["request"]["prompt"] += " Alter the action for this condition."
        job["request_sha256"] = json_hash(job["request"])
        _rewrite_fixture_json(case["prep"] / "bundle.json", bundle)
        _rewrite_fixture_json(records / "bundle.json", bundle)
    elif mutation == "reuse":
        evidence = read_json(case["output"] / "evidence.json")
        evidence["conditions"][1]["jobs"][1]["reused_from"]["run_id"] = "outside-this-block"
        _rewrite_fixture_json(case["output"] / "evidence.json", evidence)
    elif mutation == "ledger":
        block["accounting"]["provider_cost_usd"] = 0
        _rewrite_fixture_json(records / "block.json", block)
    elif mutation == "receipt":
        path = Path(block["runs"][0]["generation_jobs"][0]["receipt_path"])
        receipt = read_json(path)
        receipt["job_id"] = "edited-after-inspection"
        _rewrite_fixture_json(path, receipt)
    elif mutation == "source":
        path = case["source"] / "moodcut/final.json"
        plan = read_json(path)
        plan["shots"][0]["direction"] += " Extra action."
        _rewrite_fixture_json(path, plan)
    elif mutation == "file":
        Path(block["runs"][0]["video_path"]).write_bytes(b"changed media")
    elif mutation == "run":
        row = read_json(records / "baseline/run.json")
        row["provider_cost_usd"] = 0
        _rewrite_fixture_json(records / "baseline/run.json", row)
    else:
        _rewrite_fixture_json(records / "receipts.json", {})
    before = {p: p.read_bytes() for p in case["evidence"].parent.rglob("*") if p.is_file()}
    report = _qualify_inspection(case)
    assert report["comparison_status"] == "ineligible"
    assert any(c["errors"] for c in report["conditions"])
    assert len(report["record_block"]["runs"]) == 3
    assert report["record_block"] == read_json(records / "block.json")
    if mutation == "request":
        assert any("actual P4 compiler" in e for e in report["errors"])
    if mutation == "ledger":
        assert report["accounting_verified"] is False
    assert {p: p.read_bytes() for p in before} == before


@pytest.mark.parametrize("variant", ["unknown", "failed", "unsubmitted"])
def test_offline_qualification_keeps_failures_unknowns_and_coverage(inspection_inputs, variant, tmp_path):
    from test_video_generation import inspect_local, ROOT
    from moodcut.pipeline import read_json
    from moodcut.__main__ import main
    case = inspection_inputs
    if variant == "unsubmitted":
        evidence = read_json(case["evidence"])
        for condition in evidence["conditions"]:
            condition["jobs"] = []
        _rewrite_fixture_json(case["evidence"], evidence)
    else:
        path = case["evidence"].parent / "receipt-0-0.json"
        receipt = read_json(path)
        receipt.update(schema_version="1.0", provider_cost_usd=None)
        receipt.pop("download_attempts")
        receipt.pop("download_redirect_attempts")
        if variant == "failed":
            receipt.update(status="failed", video_path=None)
        _rewrite_fixture_json(path, receipt)
    inspect_local(case)
    original = read_json(case["output"] / "records/block.json")
    report = _qualify_inspection(case)
    assert report["record_block"] == original and len(original["runs"]) == 3
    assert report["accounting_verified"] is True
    assert report["comparison_status"] == ("eligible" if variant == "unknown" else "ineligible")
    assert all(r["comparison_status"] in ("not_checked", "ineligible") for r in original["runs"])
    if variant != "unsubmitted":
        assert report["record_block"]["accounting"]["provider_cost_usd"] is None
        assert report["record_block"]["accounting"]["known_subtotals"]["provider_cost_usd"] == .21
    if variant == "failed":
        assert [r["comparison_status"] for r in report["conditions"]] == ["ineligible", "eligible", "eligible"]
        output = tmp_path / "failed-qualification"
        assert main(["qualify-generated-records", "--project-root", str(ROOT), "--records",
                     str(case["output"] / "records"), "--pricing-config", "configs/video.json",
                     "--output", str(output)]) == 1
        assert read_json(output / "qualification.json")["record_block"] == original


def test_offline_qualification_preserves_single_shot_original_seed(inspection_inputs):
    from test_video_generation import inspect_local, ROOT
    from moodcut.pipeline import prepare_generated_run, read_json
    case = inspection_inputs
    selected = case["bundle"]["conditions"][0]["jobs"][1]["shot_id"]
    case["prep"] = case["prep"].parent / "single-prepared"
    prepare_generated_run(case["source"], out_dir=case["prep"], shot_id=selected,
                          pricing_config=ROOT / "configs/video.json", project_root=ROOT)
    evidence = read_json(case["evidence"])
    for condition in evidence["conditions"]:
        condition["jobs"] = [j for j in condition["jobs"] if j["shot_id"] == selected]
    _rewrite_fixture_json(case["evidence"], evidence)
    inspect_local(case)
    report = _qualify_inspection(case)
    assert report["comparison_status"] == "eligible"
    assert report["record_block"]["selected_shot_ids"] == [selected]
    bundle = read_json(case["prep"] / "bundle.json")
    assert all(c["jobs"][0]["request"]["seed"] == bundle["settings"]["seed"] + 1 for c in bundle["conditions"])
    assert report["record_block"]["accounting"]["generation_posts"] == 1
    exported = _generated_export(case, case["output"].parent / "single-blind")
    summary = _generated_scores(case, [], exported["private_key_path"])
    assert exported["exported_clips"] == 3
    assert summary["generated_qualification"][0]["record_block"]["selected_shot_ids"] == [selected]
    assert summary["block_ledger_accounting"]["blocks"][0]["accounting"]["generation_posts"] == 1


def test_offline_qualification_missing_source_returns_diagnostics(tmp_path):
    from moodcut.evaluation import qualify_generated_records
    report = qualify_generated_records(tmp_path / "missing", pricing_config=tmp_path / "missing-price")
    assert report["comparison_status"] == "ineligible" and report["errors"]
    assert report["record_block"] is None and report["accounting_verified"] is False


def _generated_export(case, output, seed=17):
    from moodcut.evaluation import export_generated_blind_items
    from test_video_generation import ROOT
    return export_generated_blind_items([case["output"] / "records"], out_dir=output, seed=seed,
        pricing_config="configs/video.json", project_root=ROOT)


def _generated_scores(case, ratings, private_key=None):
    from moodcut.evaluation import summarize_generated_records
    from test_video_generation import ROOT
    return summarize_generated_records([case["output"] / "records"], ratings, private_key=private_key,
        pricing_config="configs/video.json", project_root=ROOT)


def test_generated_blind_export_and_rating_cli_preserve_sources(inspection_inputs, tmp_path, monkeypatch):
    from test_video_generation import inspect_local, ROOT
    from moodcut.pipeline import read_json
    from moodcut.__main__ import main
    from moodcut.evaluation import _read_evaluation_csv, RATING_FIELDS
    case = inspection_inputs
    inspect_local(case)
    original = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    monkeypatch.chdir(tmp_path)
    exported = _generated_export(case, tmp_path / "blind")
    key = _read_evaluation_csv(exported["private_key_path"])
    index = _read_evaluation_csv(exported["blind_items_path"])
    assert exported["exported_clips"] == 3 and exported["excluded_runs"] == 0
    assert exported["formal_inclusion_approved"] is False
    assert all(set(row) == {"item_id", "video_file"} for row in index)
    assert {p.relative_to(tmp_path / "blind/public").as_posix() for p in (tmp_path / "blind/public").rglob("*") if p.is_file()} == {
        "blind_items.csv", "ratings.csv", *[r["video_file"] for r in index]}
    template = _read_evaluation_csv(exported["ratings_path"])
    assert all(row[f] == "" for row in template for f in RATING_FIELDS if f != "item_id")
    records = read_json(case["output"] / "records/block.json")
    # Explicit synthetic arithmetic fixture; not independent human judgments.
    by_condition = {r["condition"]: r for r in key}
    tone = records["runs"][0]["tone"]
    votes = [rating(by_condition["generic_review"]["item_id"], tone),
             rating(by_condition["generic_review"]["item_id"], "uncertain", "fixture_b"),
             rating(by_condition["moodcut"]["item_id"], tone, value=5)]
    summary = _generated_scores(case, votes, exported["private_key_path"])
    assert summary["overall"]["coverage"]["planned_runs"] == 3
    assert summary["overall"]["coverage"]["missing_ratings"] == 1
    assert summary["overall"]["equal_clip_means"]["tone_accuracy"] == .75
    assert summary["common_moodcut_generic"]["mean_moodcut_minus_generic"]["tone_accuracy"] == .5
    assert summary["block_ledger_accounting"]["blocks"][0]["accounting"] == records["accounting"]
    assert records["accounting"]["generation_posts"] == 4  # Reused shots not billed twice.
    assert read_json(exported["summary_path"])["overall"]["coverage"]["rated_clips"] == 0
    diagnostic = read_json(exported["summary_path"])["overall"]["generation"]
    assert diagnostic["by_status"]["assembled_requires_manual_inspection"] == 3
    assert diagnostic["jobs"]["recorded_jobs"] == 6
    assert diagnostic["jobs"]["declared_reused_jobs"] == 2
    assert summary["overall"]["generation"] == diagnostic
    assert {p: p.read_bytes() for p in original} == original
    with pytest.raises(ValueError, match="export_generated"):
        export_blind_items(records["runs"], out_dir=tmp_path / "bypass", seed=0)
    with pytest.raises(ValueError, match="summarize_generated"):
        summarize(records["runs"], votes)
    with pytest.raises(ValueError, match="not exported"):
        _generated_scores(case, [rating(records["runs"][0]["run_id"])], exported["private_key_path"])
    with pytest.raises(ValueError):
        _generated_scores(case, template, exported["private_key_path"])
    with pytest.raises(FileExistsError):
        _generated_export(case, tmp_path / "blind")
    with Path(tmp_path / "synthetic-ratings.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=RATING_FIELDS)
        writer.writeheader()
        writer.writerows(votes)
    args = ["evaluate", "--project-root", str(ROOT), "--records", str(case["output"] / "records"),
            "--pricing-config", "configs/video.json"]
    assert main([*args, "--ratings", str(tmp_path / "synthetic-ratings.csv"), "--private-key",
                 exported["private_key_path"], "--output", str(tmp_path / "scores.json")]) == 0
    assert read_json(tmp_path / "scores.json") == summary
    assert main([*args, "--blind-output", str(tmp_path / "cli-blind"), "--seed", "17"]) == 0
    assert Path(exported["private_key_path"]).read_bytes() == (tmp_path / "cli-blind/PRIVATE/private_key.csv").read_bytes()
    assert {p: p.read_bytes() for p in original} == original


@pytest.mark.parametrize("mutation", ["copy", "key", "index", "block", "receipt", "source_video", "missing_manifest",
                                     "malformed_manifest", "key_rehashed", "subset_key_rehashed"])
def test_generated_rating_rechecks_all_exported_items(inspection_inputs, tmp_path, mutation):
    from test_video_generation import inspect_local
    from moodcut.pipeline import read_json
    case = inspection_inputs
    inspect_local(case)
    exported = _generated_export(case, tmp_path / "blind")
    # Empty scores still validate every exported clip and every mapping.
    if mutation == "copy":
        (tmp_path / "blind/public/videos/item_00003.mp4").write_bytes(b"replaced after export")
    elif mutation in ("key", "index", "key_rehashed", "subset_key_rehashed"):
        path = Path(exported["private_key_path"] if mutation == "key" else exported["blind_items_path"])
        if mutation.endswith("rehashed"):
            import hashlib
            path = Path(exported["private_key_path"])
            content = path.read_text(encoding="utf-8").splitlines(keepends=True)
            if mutation == "subset_key_rehashed":
                path.write_text("".join(content[:-1]), encoding="utf-8")
            else:
                path.write_text("".join(content).replace("item_00001", "item_99999"), encoding="utf-8")
            manifest = read_json(exported["manifest_path"])
            manifest["private_key_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            _rewrite_fixture_json(exported["manifest_path"], manifest)
        else:
            path.write_bytes(path.read_bytes().replace(b"item_00001", b"item_99999"))
    elif mutation == "missing_manifest":
        Path(exported["manifest_path"]).unlink()
    elif mutation == "malformed_manifest":
        _rewrite_fixture_json(exported["manifest_path"], [])
    else:
        block = read_json(case["output"] / "records/block.json")
        if mutation == "block":
            block["runs"][0]["shared_generation_sha256"] = "a" * 64
            _rewrite_fixture_json(case["output"] / "records/block.json", block)
        elif mutation == "receipt":
            path = Path(block["runs"][0]["generation_jobs"][0]["receipt_path"])
            receipt = read_json(path)
            receipt["job_id"] += "-changed"
            _rewrite_fixture_json(path, receipt)
        else:
            Path(block["runs"][0]["video_path"]).write_bytes(b"changed source")
    with pytest.raises((ValueError, OSError)):
        _generated_scores(case, [], exported["private_key_path"])


@pytest.mark.parametrize("variant", ["unknown", "failed", "unsubmitted"])
def test_generated_export_keeps_full_failure_and_unknown_ledgers(inspection_inputs, tmp_path, variant):
    from test_video_generation import inspect_local
    from moodcut.pipeline import read_json
    case = inspection_inputs
    if variant == "unsubmitted":
        evidence = read_json(case["evidence"])
        for condition in evidence["conditions"]:
            condition["jobs"] = []
        _rewrite_fixture_json(case["evidence"], evidence)
    else:
        path = case["evidence"].parent / "receipt-0-0.json"
        receipt = read_json(path)
        receipt.update(schema_version="1.0", provider_cost_usd=None)
        receipt.pop("download_attempts")
        receipt.pop("download_redirect_attempts")
        if variant == "failed":
            receipt.update(status="failed", video_path=None)
        _rewrite_fixture_json(path, receipt)
    inspect_local(case)
    block = read_json(case["output"] / "records/block.json")
    exported = _generated_export(case, tmp_path / "blind")
    assert exported["exported_clips"] == (3 if variant == "unknown" else 0)
    summary = _generated_scores(case, [], exported["private_key_path"])
    assert summary["overall"]["coverage"]["planned_runs"] == 3
    assert summary["overall"]["coverage"]["missing_ratings"] == 3
    assert summary["overall"]["equal_clip_means"]["tone_accuracy"] is None
    assert summary["common_moodcut_generic"]["common_evaluable_blocks"] == 0
    assert summary["block_ledger_accounting"]["blocks"][0]["accounting"] == block["accounting"]
    assert summary["block_ledger_accounting"]["complete"] is True
    states = summary["overall"]["generation"]["by_status"]
    if variant == "unknown":
        assert states["assembled_requires_manual_inspection"] == 3
    elif variant == "failed":
        assert states["failed"] == 1 and states["assembled_requires_manual_inspection"] == 2
    else:
        assert states["prepared_offline"] == 3
    if variant != "unsubmitted":
        assert block["accounting"]["provider_cost_usd"] is None
        assert block["accounting"]["known_subtotals"]["provider_cost_usd"] == .21


@pytest.mark.parametrize("mutation", ["destination_bytes", "source_receipt", "output_race"])
def test_generated_copy_boundary_does_not_publish_partial_package(inspection_inputs, tmp_path, monkeypatch, mutation):
    import shutil
    from test_video_generation import inspect_local
    from moodcut.pipeline import read_json
    case = inspection_inputs
    inspect_local(case)
    original = shutil.copyfileobj
    def changed(incoming, outgoing, *args, **kwargs):
        original(incoming, outgoing, *args, **kwargs)
        if mutation == "destination_bytes":
            outgoing.write(b"changed during copy")
        elif mutation == "output_race":
            (tmp_path / "blind").mkdir(exist_ok=True)
        else:
            path = case["evidence"].parent / "receipt-0-0.json"
            receipt = read_json(path)
            receipt["job_id"] += "-changed"
            _rewrite_fixture_json(path, receipt)
    monkeypatch.setattr(shutil, "copyfileobj", changed)
    with pytest.raises((ValueError, FileExistsError), match="changed|already exists"):
        _generated_export(case, tmp_path / "blind")
    if mutation == "output_race":
        assert (tmp_path / "blind").is_dir() and not list((tmp_path / "blind").iterdir())
    else:
        assert not (tmp_path / "blind").exists()
    assert not list(tmp_path.glob(".blind-export-*"))


def test_generated_evaluation_rejects_partial_and_duplicate_block_inputs(inspection_inputs, tmp_path):
    import shutil
    from test_video_generation import inspect_local, ROOT
    from moodcut.evaluation import export_generated_blind_items
    from moodcut.pipeline import read_json
    case = inspection_inputs
    inspect_local(case)
    directory = case["output"] / "records"
    options = dict(out_dir=tmp_path / "blind", seed=0, pricing_config="configs/video.json", project_root=ROOT)
    with pytest.raises(ValueError, match="complete final"):
        export_generated_blind_items([directory / "baseline/run.json"], **options)
    with pytest.raises(ValueError, match="Duplicate"):
        export_generated_blind_items([directory, directory / "block.json"], **options)
    other = tmp_path / "duplicate-ledger"
    shutil.copytree(directory, other)
    with pytest.raises(ValueError, match="duplicate"):
        export_generated_blind_items([directory, other], **options)
    assert not options["out_dir"].exists()
    # Matching hashes alone do not make a saved qualification report an input.
    _rewrite_fixture_json(tmp_path / "qualification.json", _qualify_inspection(case))
    with pytest.raises(ValueError, match="complete final"):
        export_generated_blind_items([tmp_path / "qualification.json"], **options)


def test_generated_multiple_blocks_keep_failed_block_in_denominators(inspection_inputs, tmp_path):
    """Two temporary software identities over the same patterns; not new study data."""
    from test_video_generation import inspect_local, script_source, ROOT
    from moodcut.pipeline import prepare_generated_run, read_json
    from moodcut.evaluation import export_generated_blind_items, summarize_generated_records
    first = inspection_inputs
    inspect_local(first)
    second_case = copy.deepcopy(first["case"])
    second_case[0]["scene_id"] = "software_second_block"
    for plan in [second_case[1], *second_case[2].values()]:
        plan["scene_id"] = "software_second_block"
    directory = tmp_path / "second"
    source, prepared = directory / "scripts", directory / "prepared"
    block = script_source(second_case, source)
    prepare_generated_run(source, out_dir=prepared, project_root=ROOT, pricing_config=ROOT / "configs/video.json")
    bundle = read_json(prepared / "bundle.json")
    evidence = copy.deepcopy(first["supplied"])
    evidence["block_id"] = block["block_id"]
    for ci, (condition, compiled) in enumerate(zip(evidence["conditions"], bundle["conditions"])):
        for si, (job, request) in enumerate(zip(condition["jobs"], compiled["jobs"])):
            if "reused_from" in job:
                job["reused_from"]["run_id"] = block["runs"][0]["run_id"]
            else:
                receipt = read_json(first["evidence"].parent / job["receipt_path"])
                receipt.update(request_sha256=request["request_sha256"], job_id=f"software-second-{ci}-{si}",
                               video_path=str(first["media"][si]))
                if ci == si == 0:
                    receipt.update(status="failed", video_path=None, provider_cost_usd=None)
                _rewrite_fixture_json(directory / job["receipt_path"], receipt)
    _rewrite_fixture_json(directory / "evidence.json", evidence)
    second = dict(prep=prepared, evidence=directory / "evidence.json", output=directory / "inspection")
    inspect_local(second)
    paths = [first["output"] / "records", second["output"] / "records"]
    options = dict(pricing_config="configs/video.json", project_root=ROOT)
    exported = export_generated_blind_items(paths, out_dir=tmp_path / "blind-multiple", seed=0, **options)
    assert exported["exported_clips"] == 3 and exported["excluded_runs"] == 3
    scores = summarize_generated_records(list(reversed(paths)), [], private_key=exported["private_key_path"], **options)
    assert scores["overall"]["coverage"]["planned_runs"] == 6
    assert scores["overall"]["coverage"]["missing_ratings"] == 6
    assert len(scores["block_ledger_accounting"]["blocks"]) == 2
    assert scores["block_ledger_accounting"]["complete"] is True
    assert scores["overall"]["usage"]["provider_cost_usd"]["total"] is None
    assert {r["record_block"]["block_id"] for r in scores["generated_qualification"]} == {read_json(p / "block.json")["block_id"] for p in paths}


def _generation_rows():
    """Existing protocol fixture only; synthetic states are not provider evidence."""
    import json
    root = Path(__file__).resolve().parents[1]
    return json.loads((root / "tests/fixtures/generated_contract.json").read_text(encoding="utf-8"))["run_records"]


@pytest.mark.parametrize("state", ["not_started", "prepared_offline", "in_progress",
    "assembled_requires_manual_inspection", "failed", "interrupted", None, "future_state", []])
def test_generation_status_summary_has_explicit_run_denominators(state):
    rows = _generation_rows()
    rows[0]["generation_status"] = state
    if state in ("failed", "interrupted"):
        rows[0].update(run_status="failed", failure_kind="generation", provider_cost_usd=None)
    before = copy.deepcopy(rows)
    result = summarize(rows, [])
    overall = result["overall"]
    generation = overall["generation"]
    key = state if isinstance(state, str) and state not in ("future_state",) else "unknown"
    assert generation["generated_runs"] == sum(generation["by_status"].values()) == 3
    assert generation["by_status"][key] == (3 if state == "not_started" else 1)
    assert generation["not_applicable_runs"] == 0
    assert generation["jobs"]["recorded_jobs"] == 0
    assert generation["runs_with_empty_job_records"] == 3
    assert overall["coverage"]["planned_runs"] == overall["coverage"]["missing_ratings"] == 3
    assert overall["equal_clip_means"]["tone_accuracy"] is None
    assert result["common_moodcut_generic"]["common_evaluable_blocks"] == 0
    for condition in ("baseline", "generic_review", "moodcut"):
        assert result["by_condition"][condition]["generation"]["generated_runs"] == 1
    if state in ("failed", "interrupted"):
        assert generation["failed_run_causes"] == {"generation": 1}
        assert overall["usage"]["provider_cost_usd"]["total"] is None
    assert rows == before


def test_generation_summary_keeps_mixed_job_states_reuse_and_raw_receipt_statuses():
    rows = _generation_rows()
    rows[0].update(generation_status="failed", run_status="failed", failure_kind="generation",
        provider_cost_usd=None, generation_jobs=[
            dict(status="failed", remote_status="expired"),
            dict(status="interrupted", remote_status="polling_timeout"),
            dict(status="prepared_offline"), dict(status="future_job_state")])
    rows[1].update(generation_status="in_progress", generation_jobs=[
        dict(status="downloaded", remote_status="downloaded"),
        dict(status="downloaded", reused_from=dict(run_id=rows[0]["run_id"], shot_id="s1"))])
    rows[2].update(generation_status="prepared_offline", generation_jobs=[dict(status="prepared_offline")])
    before = copy.deepcopy(rows)
    report = summarize(rows, [])
    g = report["overall"]["generation"]
    assert g["by_status"]["failed"] == g["by_status"]["in_progress"] == g["by_status"]["prepared_offline"] == 1
    assert g["awaiting_assembly_runs"] == 1
    assert g["runs_with_unsubmitted_jobs"] == 2
    assert g["failed_run_causes"] == {"generation": 1}
    assert g["jobs"]["by_status"] == dict(prepared_offline=2, submitting=0, in_progress=0,
        downloaded=2, failed=1, interrupted=1, unknown=1)
    assert g["jobs"]["recorded_jobs"] == 7
    assert g["jobs"]["remote_status_counts"] == dict(expired=1, polling_timeout=1, downloaded=1)
    assert g["jobs"]["jobs_without_remote_status"] == 4
    assert g["jobs"]["declared_reused_jobs"] == 1  # Recorded clips, not additional provider tasks.
    assert report["overall"]["coverage"]["render_pending_or_skipped_runs"] == 3
    assert report["overall"]["usage"]["provider_cost_usd"]["total"] is None
    assert rows == before


def test_generation_summary_separates_media_failure_from_pre_generation_failure():
    rows = _generation_rows()
    rows[0].update(generation_status="failed", run_status="failed", failure_kind="media", render_status="render_failed")
    rows[1].update(generation_status="not_started", run_status="failed", failure_kind="review", review_status="review_failed")
    rows[2].update(generation_status="in_progress", generation_jobs=[dict(status="in_progress", remote_status="completed")])
    result = summarize(rows, [])
    assert result["overall"]["generation"]["pre_generation_failed_runs"] == 1
    assert result["overall"]["generation"]["failed_run_causes"] == dict(media=1, review=1)
    assert result["overall"]["generation"]["awaiting_assembly_runs"] == 0  # Remote completed is not downloaded.
    assert result["overall"]["coverage"]["render_failed_runs"] == 1
    assert result["overall"]["coverage"]["review_failed_runs"] == 1


def test_generation_summary_does_not_infer_missing_jobs_or_legacy_states():
    rows = _generation_rows()
    rows[0].pop("generation_status")
    rows[0].pop("generation_jobs")
    rows[1]["generation_jobs"] = [None, {}]
    rows[2]["generation_jobs"] = []
    result = summarize(rows, [])["overall"]["generation"]
    assert result["by_status"]["unknown"] == 1
    assert result["runs_with_invalid_job_records"] == 2
    assert result["runs_with_empty_job_records"] == 1
    assert result["jobs"]["by_status"]["unknown"] == 2
    assert result["runs_with_unsubmitted_jobs"] == 0
    legacy = records_fixture()
    assert "generation" not in summarize(legacy, [])["overall"]
    legacy[0].update(output_mode="generated", generation_status="not_started", generation_jobs=[])
    report = summarize(legacy, [])
    assert report["overall"]["generation"]["generated_runs"] == 1
    assert report["overall"]["generation"]["not_applicable_runs"] == 5
    assert report["by_condition"]["moodcut"]["generation"]["generated_runs"] == 0
    assert sum(report["by_condition"]["moodcut"]["generation"]["by_status"].values()) == 0
    assert "generation" not in summarize([], [])["overall"]  # Empty legacy input carries no mode assertion.


if __name__ == "__main__":
    unittest.main()
