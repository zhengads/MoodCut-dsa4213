"""Does any rule over the six VEMOCLAP probabilities separate affectionate / hostile / tense?

Reads only the committed results (docs/studies/emotion-evaluation-20261027/results/vemoclap_all.json); no models needed.
It reports: per-atmosphere probability profile, single-feature separability (AUC) between hostile and tense inside the
conflict class, and a leave-one-group-out check of a "conflict gate + disgust threshold" rule. The thresholds are
chosen after looking at the data, so the numbers describe the data and are not a validated rule.
"""
import json
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import STUDY  # noqa: E402

LAB = ("anger", "disgust", "fear", "joy", "sadness", "surprise")
FILM = {"S01": "Frozen", "S03": "Frozen", "Anna/Elsa": "Frozen", "S04": "Nezha2", "S06": "Nezha2", "S05": "other"}


def load():
    rows = []
    for r in json.loads((STUDY / "results" / "vemoclap_all.json").read_text(encoding="utf-8")):
        if r["label_system"] != "atmosphere3":
            continue
        q = {k: r["full"][k] * 100 for k in LAB}
        rows.append(dict(group=r["group"], story=r["story"], tone=r["target"], fr=FILM[r["story"]], cond=r["condition"],
                         **q, C=q["anger"] + q["disgust"] + q["fear"]))
    return rows


def auc(pos, neg):
    t = n = 0
    for a in pos:
        for b in neg:
            t += 1
            n += 1 if a > b else (0.5 if a == b else 0)
    return n / t


def rule(d, thr):
    if d["C"] < 50:
        return "affectionate"
    return "hostile" if d["disgust"] >= thr else "tense"


def fit_thr(train):
    best = None
    for thr in (0.5, 1, 1.5, 2, 3, 4, 5, 8, 10, 15, 20, 30):
        acc = sum(rule(d, thr) == d["tone"] for d in train) / len(train)
        if best is None or acc > best[0] or (acc == best[0] and thr > best[1]):
            best = (acc, thr)
    return best[1]


def grouped(d):
    h, t, a = d["anger"] + d["disgust"], d["fear"], d["joy"] + d["sadness"] + d["surprise"]
    return max((("hostile", h), ("tense", t), ("affectionate", a)), key=lambda x: x[1])[0]


def main():
    D = load()
    print("records", len(D))
    print("\n== six-emotion profile by target atmosphere (mean [min-max], %)")
    for tone in ("affectionate", "hostile", "tense"):
        xs = [d for d in D if d["tone"] == tone]
        print(tone, len(xs), " ".join(f"{k[:3]}={st.mean(d[k] for d in xs):5.1f}[{min(d[k] for d in xs):.1f}-{max(d[k] for d in xs):.1f}]" for k in LAB))
    conf = [d for d in D if d["C"] >= 50]
    hs = [d for d in conf if d["tone"] == "hostile"]
    ts = [d for d in conf if d["tone"] == "tense"]
    print("\nconflict class (anger+disgust+fear >= 50%):", len(conf), "tense", len(ts), "hostile", len(hs),
          "affectionate", sum(d["tone"] == "affectionate" for d in conf))
    for d in conf:
        for k in ("anger", "disgust", "fear"):
            d[k + "_share"] = d[k] / d["C"] * 100
    print("\n== hostile vs tense inside the conflict class: AUC (0.5 = no separation, >0.5 = hostile higher)")
    for f in list(LAB) + ["anger_share", "disgust_share", "fear_share"]:
        print(f"  {f:14} AUC={auc([d[f] for d in hs], [d[f] for d in ts]):.2f}  hostile {min(d[f] for d in hs):.1f}-{max(d[f] for d in hs):.1f}  tense {min(d[f] for d in ts):.1f}-{max(d[f] for d in ts):.1f}")
    print("\n== conflict gate + disgust threshold, leave-one-group-out")
    hit = tot = 0
    for g in sorted({d["group"] for d in D}):
        thr = fit_thr([d for d in D if d["group"] != g])
        test = [d for d in D if d["group"] == g]
        h = sum(rule(d, thr) == d["tone"] for d in test)
        hit += h
        tot += len(test)
        print(f"  hold out {g:16} target={test[0]['tone']:12} thr={thr:>4}  {h}/{len(test)}")
    print("  total", hit, "/", tot)
    thr = fit_thr(D)
    print(f"  threshold fitted on all data: {thr} -> {sum(rule(d, thr) == d['tone'] for d in D)}/{len(D)} (in-sample)")
    print("\ngrouped three-class (hostile=anger+disgust, tense=fear, affectionate=joy+sadness+surprise):", sum(grouped(d) == d["tone"] for d in D), "/", len(D))
    print("\n== same franchise (Nezha2): tense S04 vs hostile S06")
    for d in D:
        if d["fr"] == "Nezha2":
            print(f"  {d['tone']:8} {d['group']:16} {d['cond']:28} disgust={d['disgust']:5.1f} anger={d['anger']:5.1f}")


if __name__ == "__main__":
    main()
