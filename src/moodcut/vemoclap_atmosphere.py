"""Diagnostic mapping from VEMOCLAP six-class probabilities to MoodCut atmospheres (rule grouped).

Offline and dependency-free. It reads probabilities only; it never runs a model and is not an
independent experiment result or a replacement for human ratings.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path

EMOTIONS = ("anger", "disgust", "fear", "joy", "sadness", "surprise")
RULE_VERSION = "grouped"
# Insertion order is the tie-break order.
GROUPS: dict[str, tuple[str, ...]] = {
    "hostile": ("anger", "disgust"),
    "tense": ("fear",),
    "affectionate": ("joy", "sadness", "surprise"),
}


def validate_probabilities(probabilities: Mapping[str, float]) -> dict[str, float]:
    """Return a float copy; require exactly the six labels, finite values in [0, 1] summing to ~1."""
    if set(probabilities) != set(EMOTIONS):
        raise ValueError("probabilities must contain exactly: " + ", ".join(EMOTIONS))
    values = {}
    for name in EMOTIONS:
        value = probabilities[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"probability for {name} must be a finite number")
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"probability for {name} must be within [0, 1]")
        values[name] = float(value)
    if abs(sum(values.values()) - 1.0) > 0.01:
        raise ValueError("probabilities must sum to 1 within 0.01")
    return values


def group_scores(probabilities: Mapping[str, float]) -> dict[str, float]:
    values = validate_probabilities(probabilities)
    return {group: sum(values[name] for name in names) for group, names in GROUPS.items()}


def classify(probabilities: Mapping[str, float]) -> str:
    """Highest group score; ties go to the earlier group in GROUPS. No abstention in grouped."""
    scores = group_scores(probabilities)
    best = max(scores.values())
    return next(group for group, score in scores.items() if score == best)


def intended_score(probabilities: Mapping[str, float], intended: str) -> float:
    if intended not in GROUPS:
        raise ValueError("intended atmosphere must be one of: " + ", ".join(GROUPS))
    return group_scores(probabilities)[intended]


def score_records(records: Iterable[Mapping]) -> list[dict]:
    """Per-record group scores and hit flag; records without an atmosphere label get hit=None."""
    rows = []
    for record in records:
        scores = group_scores(record["probabilities"])
        label = classify(record["probabilities"])
        intended = record.get("intended_atmosphere")
        rows.append({
            "id": record["id"], "intended": intended, "scores": scores, "predicted": label,
            "hit": None if intended is None else label == intended,
            "intended_score": None if intended is None else scores[intended],
        })
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path, help="results JSON with a 'records' list")
    args = parser.parse_args(argv)
    data = json.loads(args.results.read_text(encoding="utf-8"))
    rows = score_records(data["records"])
    print(f"rule {RULE_VERSION}: hostile=anger+disgust, tense=fear, affectionate=joy+sadness+surprise")
    for row in rows:
        s = row["scores"]
        mark = "-" if row["hit"] is None else ("hit" if row["hit"] else "miss")
        print(f"{row['id']:<46} hostile={s['hostile']*100:5.1f} tense={s['tense']*100:5.1f} "
              f"affectionate={s['affectionate']*100:5.1f} -> {row['predicted']:<12} intended={row['intended']} {mark}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
