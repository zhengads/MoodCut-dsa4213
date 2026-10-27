"""Write a VBench imaging_quality batch manifest (moodcut.evaluation format) from video_manifest.json.

Video files are expected at <video-root>/<video_id>.mp4 (e.g. s09/baseline.mp4). Identical files are listed once.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import STUDY  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--groups", nargs="*", help="limit to these groups, e.g. s07 s08 (default: all with a local video)")
    a = ap.parse_args()
    rows = []
    for m in json.loads((STUDY / "video_manifest.json").read_text(encoding="utf-8")):
        if not m.get("sha256") or m.get("same_file_as") or (a.groups and m["group"] not in a.groups):
            continue
        rows.append({"video_id": m["video_id"], "story_id": f"{m['story']}/{m['group']}", "method": m["video_id"],
                     "prompt": f"{m['story']} {m['group']} {m['condition']} ({m['duration_s']}s, {m['language']}); development video, prompt text is not scored",
                     "video_path": f"{m['video_id']}.mp4", "seed": None, "evaluation_unit": "shot", "source_kind": "development"})
    a.out.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(rows), "videos ->", a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
