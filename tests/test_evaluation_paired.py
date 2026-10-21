"""Synthetic arithmetic and temporary media test the protocol, not emotion quality."""
import copy
import csv
import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
