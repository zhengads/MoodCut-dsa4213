"""Synthetic offline checks for the VEMOCLAP atmosphere grouping; not model or effect evidence."""
import json
from pathlib import Path
import tempfile
import unittest

from moodcut import vemoclap_atmosphere as va


def probs(**kw):
    base = {name: 0.0 for name in va.EMOTIONS}
    base.update(kw)
    return base


class AtmosphereGroupingTests(unittest.TestCase):
    def test_hand_calculated_group_sums(self):
        p = probs(anger=.5, disgust=.1, fear=.1, joy=.05, sadness=.2, surprise=.05)
        s = va.group_scores(p)
        self.assertAlmostEqual(s["hostile"], .6)
        self.assertAlmostEqual(s["tense"], .1)
        self.assertAlmostEqual(s["affectionate"], .3)
        self.assertEqual(va.classify(p), "hostile")
        self.assertAlmostEqual(va.intended_score(p, "tense"), .1)

    def test_surprise_counts_toward_affectionate_without_abstention(self):
        self.assertEqual(va.classify(probs(surprise=.9, anger=.1)), "affectionate")

    def test_sadness_and_fear_split_goes_to_the_larger_group(self):
        self.assertEqual(va.classify(probs(fear=.565, sadness=.424, anger=.011)), "tense")

    def test_tie_goes_to_the_earlier_group(self):
        self.assertEqual(va.classify(probs(anger=.5, fear=.5)), "hostile")

    def test_rejects_bad_probabilities(self):
        bad = [
            {"anger": 1.0},
            probs(anger=1.2, fear=-.2),
            probs(anger=.5),
            probs(anger=float("nan"), fear=1.0),
            dict(probs(anger=1.0), extra=0.0),
            probs(anger=True),
        ]
        for case in bad:
            with self.subTest(case=case), self.assertRaises(ValueError):
                va.group_scores(case)
        with self.assertRaises(ValueError):
            va.intended_score(probs(anger=1.0), "unknown")

    def test_score_records_marks_hits_and_unlabelled(self):
        rows = va.score_records([
            {"id": "a", "intended_atmosphere": "hostile", "probabilities": probs(anger=.9, joy=.1)},
            {"id": "b", "intended_atmosphere": "tense", "probabilities": probs(sadness=1.0)},
            {"id": "c", "intended_atmosphere": None, "probabilities": probs(fear=1.0)},
        ])
        self.assertEqual([r["hit"] for r in rows], [True, False, None])
        self.assertIsNone(rows[2]["intended_score"])

    def test_cli_prints_every_record(self):
        data = {"records": [{"id": "x", "intended_atmosphere": "hostile", "probabilities": probs(anger=1.0)}]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "r.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            self.assertEqual(va.main([str(path)]), 0)


if __name__ == "__main__":
    unittest.main()
