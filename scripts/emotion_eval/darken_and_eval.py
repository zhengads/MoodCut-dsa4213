"""Brightness control experiment: darken a video with ffmpeg (audio copied unchanged) and run the VEMOCLAP ablation.

ffmpeg must be on PATH. Example:
  python scripts/emotion_eval/darken_and_eval.py --video s09/baseline --level 0.30
The level is subtracted from normalised luma by ffmpeg's eq filter (0.30 already takes the mean luma of these
videos from ~90 to ~20 of 255; 0.50 is nearly black). Output: <work>/dark/<name>_dark<level>.mp4 and result folder.
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import work_dir  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True, help="video_id such as s09/baseline (file: <work>/videos/<id>.mp4)")
    ap.add_argument("--level", required=True, help="brightness reduction, e.g. 0.30")
    a = ap.parse_args()
    work = work_dir()
    src = work / "videos" / f"{a.video}.mp4"
    name = f"{a.video.replace('/', '_')}_dark{a.level}"
    out_mp4 = work / "dark" / f"{name}.mp4"
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-vf", f"eq=brightness=-{a.level}",
                    "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "copy", str(out_mp4)], check=True)
    subprocess.run([sys.executable, str(Path(__file__).with_name("vemoclap_ablate.py")), "--video", str(out_mp4),
                    "--out", str(work / "dark" / "results" / name)], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
