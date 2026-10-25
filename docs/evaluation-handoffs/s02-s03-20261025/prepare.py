"""Prepare this dated handoff locally; no network, client or live execution."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parents[2]
sys.path.insert(0, str(ROOT / "src"))
from moodcut.validation import validate_scene


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    out = (ROOT / args.output).resolve()
    if not out.is_relative_to((ROOT / "runs").resolve()) or out == (ROOT / "runs").resolve():
        parser.error("Choose a new child directory under runs/.")
    if out.exists():
        parser.error("Output already exists; nothing will be overwritten.")
    manifest = json.loads((PACKAGE / "handoff.json").read_text(encoding="utf-8"))
    prepared = []
    for row in manifest["stories"]:
        files = {}
        for name, base, source, digest in (
            ("scene.json", ROOT, row["scene_path"], row["scene_sha256"]),
            ("assets.json", ROOT, row["assets_path"], row["assets_sha256"]),
            ("generation_settings.json", PACKAGE, row["generation_settings_path"], row["generation_settings_sha256"]),
        ):
            raw = (base / source).read_bytes()
            if hashlib.sha256(raw).hexdigest() != digest:
                raise ValueError("Source checksum mismatch: " + source)
            files[name] = raw
        errors = validate_scene(json.loads(files["scene.json"]), json.loads(files["assets.json"]),
                                project_root=ROOT, output_mode="generated")
        if errors:
            raise ValueError("; ".join(errors))
        prepared.append((row["story_id"], files))
    price = manifest["text_price_snapshot"]
    price_bytes = (PACKAGE / price["path"]).read_bytes()
    if hashlib.sha256(price_bytes).hexdigest() != price["sha256"]:
        raise ValueError("Price snapshot checksum mismatch")
    out.mkdir(parents=True, exist_ok=False)
    for story_id, files in prepared:
        folder = out / story_id
        folder.mkdir()
        for name, raw in files.items():
            (folder / name).write_bytes(raw)
        print("Prepared " + story_id)
    (out / "text-models-price-snapshot.json").write_bytes(price_bytes)
    (out / "handoff.json").write_bytes((PACKAGE / "handoff.json").read_bytes())
    print("Offline preparation complete. V4 confirmation and paid-run approval remain required.")


if __name__ == "__main__":
    main()
