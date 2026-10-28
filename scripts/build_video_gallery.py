"""Build the static gallery from a verified release archive, without network access."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile


def build(archive: Path, output: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    web = root / "web/video-review"
    index = json.loads((root / "docs/studies/six-story-clear-emotions-20261024/release-index.json").read_text(encoding="utf-8"))
    if output.exists():
        raise ValueError("Output must be a new directory to exclude stale media")
    if hashlib.sha256(archive.read_bytes()).hexdigest() != index["archive_sha256"]:
        raise ValueError("Release archive checksum mismatch")
    expected = {}
    media = {}
    with zipfile.ZipFile(archive) as bundle:
        for story in index["scenarios"]:
            for video in story["files"]:
                relative = f"media/{story['number']}-{video['condition']}.mp4"
                content = bundle.read(story["archive_directory"] + "/" + video["file"])
                if len(content) != video["bytes"] or hashlib.sha256(content).hexdigest() != video["sha256"]:
                    raise ValueError(f"Video checksum mismatch: {relative}")
                expected[relative] = video["sha256"]
                media[relative] = content
    listed = {name: digest for digest, name in (line.split("  ", 1) for line in (web / "media.sha256").read_text().splitlines())}
    data = json.loads((web / "data.json").read_text(encoding="utf-8"))
    paths = [c["video"] for s in data["scenarios"] for c in s["conditions"]]
    if listed != expected or len(paths) != 36 or set(paths) != set(expected):
        raise ValueError("Gallery data, checksums and release index disagree")
    if [s["number"] for s in data["scenarios"]] != [f"{n:02}" for n in range(1, 13)]:
        raise ValueError("Gallery requires twelve consecutively numbered stories")
    (output / "media").mkdir(parents=True)
    for name in ("index.html", "site.css", "app.js", "data.json", "media.sha256"):
        shutil.copyfile(web / name, output / name)
    for relative, content in media.items():
        (output / relative).write_bytes(content)
    (output / ".nojekyll").touch()
    print(f"Built {len(data['scenarios'])} stories and {len(media)} verified videos")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    build(args.archive, args.output)
