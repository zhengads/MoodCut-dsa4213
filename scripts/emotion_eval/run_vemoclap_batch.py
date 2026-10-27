"""Run the per-modality VEMOCLAP ablation (vemoclap_ablate.py) for every video in video_manifest.json.

Videos are looked up as <MOODCUT_EVAL_WORK>/videos/<video_id with '/' kept>.mp4 unless --video-root is given.
Identical files (same_file_as) are only run once. Results go to <MOODCUT_EVAL_WORK>/<result_dir>.
Each video takes a few minutes on CPU.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import STUDY, work_dir  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, default=STUDY / "video_manifest.json")
    ap.add_argument("--video-root", type=Path, help="folder holding <video_id>.mp4 files (default: <work>/videos)")
    ap.add_argument("--only", nargs="*", help="video_id prefixes to run, e.g. s09 s15")
    ap.add_argument("--skip-existing", action="store_true")
    a = ap.parse_args()
    work = work_dir()
    root = a.video_root or work / "videos"
    for m in json.loads(a.manifest.read_text(encoding="utf-8")):
        if m.get("same_file_as") or not m.get("result_dir"):
            continue
        if a.only and not any(m["video_id"].startswith(p) for p in a.only):
            continue
        video = root / f"{m['video_id']}.mp4"
        out = work / m["result_dir"]
        if a.skip_existing and (out / "ablation.json").exists():
            continue
        if not video.exists():
            print("MISSING", video, flush=True)
            continue
        if m.get("sha256") and sha256(video) != m["sha256"]:
            print("HASH MISMATCH (not the delivered file)", video, flush=True)
            continue
        subprocess.run([sys.executable, str(Path(__file__).with_name("vemoclap_ablate.py")), "--video", str(video), "--out", str(out)], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
