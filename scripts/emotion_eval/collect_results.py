"""Collect per-video VEMOCLAP ablation outputs and VBench scores into the committed result files.

Reads  <study>/video_manifest.json and the result folders under MOODCUT_EVAL_WORK.
Writes <study>/results/vemoclap_all.json, vbench_scores.json, dark_experiment.json and film_clips_vemoclap.json.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import STUDY, work_dir  # noqa: E402

LABELS = ("anger", "disgust", "fear", "joy", "sadness", "surprise")


def r6(d):
    return {k: round(float(v), 6) for k, v in d.items()}


def load_ablation(path: Path) -> dict:
    d = json.loads(path.read_text(encoding="utf-8"))
    return {"full": r6(d["full"]), "missing_modalities": d["missing"],
            "drop_one": {k: r6(v) for k, v in d["drop_one"].items()},
            "keep_one": {k: r6(v) for k, v in d["keep_one"].items()}, "all_zero": r6(d["all_zero"])}


def main() -> int:
    work = work_dir()
    manifest = json.loads((STUDY / "video_manifest.json").read_text(encoding="utf-8"))
    scores = {}
    for f in sorted((work / "vbench" / "runs").glob("*/normalized_results.json")):
        rows = json.loads(f.read_text(encoding="utf-8"))
        for r in (rows if isinstance(rows, list) else rows.get("results", [])):
            if r.get("dimension") == "imaging_quality" and r.get("status") == "success":
                scores[r["video_id"]] = {"score": round(r["score"], 6), "batch": f.parent.name, "video_sha256": r.get("video_sha256")}
    out = []
    for m in manifest:
        rec = {k: v for k, v in m.items() if k not in ("probabilities_only", "result_dir")}
        if m.get("probabilities_only"):
            rec["full"] = r6(m["probabilities_only"]); rec["ablation"] = None
        else:
            rec.update(load_ablation(work / m["result_dir"] / "ablation.json"))
        out.append(rec)
    res = STUDY / "results"
    res.mkdir(parents=True, exist_ok=True)
    (res / "vemoclap_all.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    (res / "vbench_scores.json").write_text(json.dumps(scores, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    dark = {}
    for f in sorted((work / "dark" / "results").glob("*/ablation.json")):
        dark[f.parent.name] = load_ablation(f)
    (res / "dark_experiment.json").write_text(json.dumps(dark, ensure_ascii=False, indent=1), encoding="utf-8")
    film = []
    for sub in ("results2", "results_fresh"):
        for f in sorted((work / sub).glob("*/ablation.json")):
            name = f.parent.name
            film.append({"clip": name, "set": sub, "intended": {"A": "affectionate", "H": "hostile", "T": "tense"}[name.lstrip("F")[0]], **load_ablation(f)})
    (res / "film_clips_vemoclap.json").write_text(json.dumps(film, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(out), "videos;", len(scores), "VBench scores;", len(dark), "dark runs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
