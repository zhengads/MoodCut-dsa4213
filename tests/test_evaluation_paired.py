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


if __name__ == "__main__":
    unittest.main()
