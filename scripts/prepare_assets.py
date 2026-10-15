"""Build an AssetManifest from explicitly selected, already local images.

No network access or image copying. Download pinned reference images with the
separate prepare_references.py --assets command, then select suitable crops.
"""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
from urllib.parse import urlparse

from PIL import Image, UnidentifiedImageError


ROOT = Path(__file__).resolve().parents[1]
MAX_IMAGE_BYTES = 32 * 1024 * 1024


def _relative(root, value, *, raw=False):
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise ValueError("path must be project-root-relative with forward slashes")
    relative = PurePosixPath(value)
    if (relative.is_absolute() or ".." in relative.parts
            or relative.as_posix() != value or value == "."):
        raise ValueError("unsafe project-relative path")
    if raw and not value.startswith("assets/raw/"):
        raise ValueError("selected image path must be inside assets/raw/")
    target = root.joinpath(*relative.parts)
    if target.is_symlink() or not target.resolve().is_relative_to(root):
        raise ValueError("path escapes project root or uses a symlink")
    return target


def prepare_assets(selection: dict, *, project_root=ROOT) -> dict:
    """Validate all selected images and return a deterministic manifest.

    Selection schema: {schema_version:'1.0', assets:[{asset_id, character_id,
    path, source_url, revision, rights_note, allowed_crops, [sha256]}]}.
    Crops and rights must be explicitly supplied; no face detection or license
    inference is performed. source_url/revision may both be null for team art.
    Optional sha256 pins the expected downloaded image and is checked first.
    """
    root = Path(project_root).resolve()
    if (not isinstance(selection, dict) or selection.get("schema_version") != "1.0"
            or not isinstance(selection.get("assets"), list) or not selection["assets"]):
        raise ValueError("selection must contain schema_version 1.0 and non-empty assets")
    assets, identifiers = [], set()
    for index, selected in enumerate(selection["assets"]):
        if not isinstance(selected, dict):
            raise ValueError(f"assets[{index}] must be an object")
        for field in ("asset_id", "character_id", "rights_note"):
            if not isinstance(selected.get(field), str) or not selected[field].strip():
                raise ValueError(f"assets[{index}].{field} must be explicitly supplied")
        aid = selected["asset_id"]
        if aid in identifiers:
            raise ValueError(f"duplicate asset_id: {aid}")
        identifiers.add(aid)
        crops = selected.get("allowed_crops")
        if (not isinstance(crops, list) or not crops
                or any(c not in ("full", "center_close") for c in crops)
                or len(crops) != len(set(crops))):
            raise ValueError(f"{aid}: explicitly select allowed_crops (full, center_close)")
        if "source_url" not in selected or "revision" not in selected:
            raise ValueError(f"{aid}: source_url and revision must be explicitly supplied")
        url, revision = selected["source_url"], selected["revision"]
        if url is None:
            if revision is not None:
                raise ValueError(f"{aid}: a revision requires source_url")
        else:
            if not isinstance(url, str):
                raise ValueError(f"{aid}: source_url must be https or null")
            parsed = urlparse(url)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError(f"{aid}: source_url must be a public https URL")
            if not isinstance(revision, str) or not revision.strip():
                raise ValueError(f"{aid}: record the source revision")
        target = _relative(root, selected.get("path"), raw=True)
        if not target.is_file() or not 0 < target.stat().st_size <= MAX_IMAGE_BYTES:
            raise ValueError(f"{aid}: missing image or image exceeds 32 MiB")
        data = target.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if "sha256" in selected and selected["sha256"] != digest:
            raise ValueError(f"{aid}: SHA-256 mismatch; existing file preserved")
        try:
            with Image.open(target) as image:
                if image.format not in ("PNG", "JPEG", "WEBP"):
                    raise ValueError(f"{aid}: unsupported image format")
                width, height = image.size
                image.verify()
        except (UnidentifiedImageError, OSError, SyntaxError) as exc:
            raise ValueError(f"{aid}: invalid image") from exc
        assets.append({"asset_id": aid, "character_id": selected["character_id"],
                       "path": selected["path"], "width": width, "height": height,
                       "sha256": digest, "source_url": url, "revision": revision,
                       "rights_note": selected["rights_note"], "allowed_crops": crops.copy()})
    return {"schema_version": "1.0", "assets": assets}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", required=True, help="Local explicit selection JSON")
    parser.add_argument("--output", required=True, help="New manifest path relative to project root")
    parser.add_argument("--project-root", default=str(ROOT))
    parser.add_argument("--check", action="store_true", help="Verify the existing manifest and local images without writing")
    args = parser.parse_args(argv)
    try:
        root = Path(args.project_root).resolve()
        output = _relative(root, args.output)
        if output.exists() and not args.check:
            raise ValueError("Output already exists; choose a new path (no overwrites)")
        selection = json.loads(Path(args.selection).read_text(encoding="utf-8-sig"))
        manifest = prepare_assets(selection, project_root=root)
        if args.check:
            existing = json.loads(output.read_text(encoding="utf-8-sig"))
            if existing != manifest:
                raise ValueError("Existing manifest does not match selected local images; files preserved")
            print(f"Verified {len(manifest['assets'])} selected local assets and manifest: {args.output}")
            return 0
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(manifest, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"Asset preparation failed: {exc}", file=sys.stderr)
        return 1
    print(f"Prepared {len(manifest['assets'])} explicitly selected local assets: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
