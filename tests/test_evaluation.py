"""Synthetic offline checks; no video quality claims."""
import copy
import csv
from pathlib import Path
import tempfile
import unittest
from moodcut.evaluation import summarize_vbench, export_vbench_summary, validate_video_manifest

D = "imaging_quality"


def manifest():
    return [dict(video_id=f"v{i}", story_id="story", method="baseline", prompt="Test",
                 video_path=f"videos/v{i}.mp4", source_kind="synthetic",
                 evaluation_unit="shot", seed=None) for i in range(4)]


def result(vid, score):
    return dict(video_id=vid, dimension=D, status="success", score=score)


class EvaluationTests(unittest.TestCase):
    def test_hand_calculated_mean_and_coverage(self):
        rows = [result("v0", .2), result("v1", .8),
                dict(video_id="v2", dimension=D, status="failed", score=None, error="decode")]
        original = copy.deepcopy(rows)
        summary = summarize_vbench(manifest(), rows, dimensions=[D])[0]
        self.assertEqual(summary["mean_score"], .5)
        self.assertEqual([summary[k] for k in ("planned", "succeeded", "failed", "missing")], [4, 2, 1, 1])
        self.assertEqual(rows, original)

    def test_zero_success_is_null(self):
        self.assertIsNone(summarize_vbench(manifest(), [], dimensions=[D])[0]["mean_score"])

    def test_invalid_scores(self):
        for score in (True, float("nan"), float("inf"), -1, 2, "0.5", None):
            with self.subTest(score=score), self.assertRaises(ValueError):
                summarize_vbench(manifest(), [result("v0", score)], dimensions=[D])

    def test_duplicate_and_unknown_results(self):
        for rows in ([result("v0", .5)] * 2, [result("unknown", .5)],
                     [dict(video_id="v0", dimension=D, status="failed", score=0, error="bad")]):
            with self.assertRaises(ValueError):
                summarize_vbench(manifest(), rows, dimensions=[D])

    def test_metadata_errors(self):
        for field, value in (("video_path", "../bad.mp4"), ("video_path", "C:/bad.mp4"),
                             ("seed", True), ("prompt", ""), ("source_kind", "unknown")):
            rows = manifest()
            rows[0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_video_manifest(rows)
        with self.assertRaises(ValueError):
            validate_video_manifest([manifest()[0]] * 2)

    def test_mixed_sources_and_units_rejected(self):
        for field, value in (("source_kind", "formal"), ("evaluation_unit", "film")):
            rows = manifest()
            rows[0][field] = value
            with self.assertRaises(ValueError):
                summarize_vbench(rows, [], dimensions=[D])

    def test_methods_kept_separate(self):
        rows = manifest()
        rows[1]["method"] = "alternative"
        summary = summarize_vbench(rows, [result("v0", .2), result("v1", .8)], dimensions=[D])
        self.assertEqual([r["mean_score"] for r in summary], [.8, .2])

    def test_csv_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "summary.csv"
            export_vbench_summary(manifest(), [], dimensions=[D], output_path=path)
            with path.open(newline="", encoding="utf-8") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(row["mean_score"], "")
            self.assertEqual(row["missing"], "4")
            with self.assertRaises(FileExistsError):
                export_vbench_summary(manifest(), [], dimensions=[D], output_path=path)

    def test_invalid_dimension_and_empty_manifest(self):
        for dimensions in ([D, D], ["unknown"], []):
            with self.assertRaises(ValueError):
                summarize_vbench(manifest(), [], dimensions=dimensions)
        with self.assertRaises(ValueError):
            summarize_vbench([], [], dimensions=[D])


class NativeResultTests(unittest.TestCase):
    def test_native_scale_conversion(self):
        from moodcut.evaluation import normalize_imaging_quality
        with tempfile.TemporaryDirectory() as directory:
            rows = manifest()
            raw = {D: [.5, [dict(video_path="videos/v0.mp4", video_results=20),
                             dict(video_path="videos/v1.mp4", video_results=80)]]}
            result_rows = normalize_imaging_quality(raw, rows, video_root=directory)
            self.assertEqual([r["score"] for r in result_rows], [.2, .8])
            summary = summarize_vbench(rows, result_rows, dimensions=[D])[0]
            self.assertEqual(summary["missing"], 2)
            self.assertEqual(summary["mean_score"], .5)

    def test_native_unknown_duplicate_invalid_and_mismatch(self):
        from moodcut.evaluation import normalize_imaging_quality
        entry = dict(video_path="videos/v0.mp4", video_results=50)
        cases = [{D: [.5, [entry, entry]]},
                 {D: [.5, [dict(entry, video_path="outside.mp4")]]},
                 {D: [.5, [dict(entry, video_results=float("nan"))]]},
                 {D: [.8, [entry]]}, {D: [.5, []]}, {D: [True, [entry]]}]
        with tempfile.TemporaryDirectory() as directory:
            for raw in cases:
                with self.subTest(raw=raw), self.assertRaises(ValueError):
                    normalize_imaging_quality(raw, manifest(), video_root=directory)
