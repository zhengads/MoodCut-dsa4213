"""Consistency checks for the committed emotion-evaluation results (offline, no models)."""
import json
import re
import unittest
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1] / "docs" / "studies" / "emotion-evaluation-20261027"
LABELS = ("anger", "disgust", "fear", "joy", "sadness", "surprise")


def load(name):
    return json.loads((STUDY / name).read_text(encoding="utf-8"))


class EmotionEvaluationResultsTest(unittest.TestCase):
    def test_manifest_and_results_agree(self):
        manifest, results = load("video_manifest.json"), load("results/vemoclap_all.json")
        ids = [m["video_id"] for m in manifest]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(ids, [r["video_id"] for r in results])
        by_id = set(ids)
        for m in manifest:
            if m.get("same_file_as"):
                self.assertIn(m["same_file_as"], by_id)
            if m.get("sha256"):
                self.assertRegex(m["sha256"], r"^[0-9a-f]{64}$")

    def test_probabilities_are_distributions(self):
        for r in load("results/vemoclap_all.json"):
            self.assertEqual(tuple(r["full"]), LABELS, r["video_id"])
            self.assertAlmostEqual(sum(r["full"].values()), 1.0, places=3, msg=r["video_id"])

    def test_identical_files_have_identical_results(self):
        results = {r["video_id"]: r for r in load("results/vemoclap_all.json")}
        for r in results.values():
            if r.get("same_file_as"):
                self.assertEqual(r["full"], results[r["same_file_as"]]["full"], r["video_id"])

    def test_vbench_scores_match_manifest_hashes(self):
        hashes = {m["video_id"]: m["sha256"] for m in load("video_manifest.json")}
        for vid, s in load("results/vbench_scores.json").items():
            self.assertIn(vid, hashes)
            self.assertEqual(s["video_sha256"], hashes[vid], vid)
            self.assertTrue(0.0 <= s["score"] <= 1.0)

    def test_no_private_paths_in_study_files(self):
        pattern = re.compile(r"[A-Za-z]:[\/]|/Users/|/home/\w+")
        for path in list(STUDY.rglob("*.md")) + list(STUDY.rglob("*.json")):
            if path.name == "fear_feature_swap_s09_s15.txt":
                continue
            self.assertIsNone(pattern.search(path.read_text(encoding="utf-8")), str(path.name))


if __name__ == "__main__":
    unittest.main()
