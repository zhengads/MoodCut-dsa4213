"""Fetch pinned reading material; never import or execute upstream source."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 64 * 1024 * 1024
HOSTS = {"raw.githubusercontent.com", "arxiv.org", "export.arxiv.org"}
PREFIXES = {"core": "references/upstream/", "papers": "references/papers/",
            "assets": "assets/raw/movieagent/"}


def load_manifest(path: Path) -> list[dict]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or not isinstance(manifest.get("files"), list):
        raise ValueError("Unsupported reference manifest")
    entries = manifest["files"]
    seen = set()
    for entry in entries:
        relative = entry["path"]
        group = entry["group"]
        parts = PurePosixPath(relative).parts
        if (group not in PREFIXES or not relative.startswith(PREFIXES[group])
                or ".." in parts or "\\" in relative or ":" in relative
                or PurePosixPath(relative).is_absolute()
                or PurePosixPath(relative).as_posix() != relative):
            raise ValueError(f"Invalid reference path: {relative}")
        if relative.casefold() in seen:
            raise ValueError(f"Duplicate reference path: {relative}")
        seen.add(relative.casefold())
        if not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]):
            raise ValueError(f"Invalid hash: {relative}")
        size = entry["size_bytes"]
        if type(size) is not int or not 0 < size <= MAX_BYTES:
            raise ValueError(f"Invalid size: {relative}")
        url = urlparse(entry["url"])
        if (url.scheme != "https" or url.hostname not in HOSTS
                or url.username or url.password or url.port not in (None, 443)
                or url.query or url.fragment):
            raise ValueError(f"Invalid source URL: {relative}")
        revision = entry["revision"]
        if url.hostname == "raw.githubusercontent.com":
            if not re.fullmatch(r"[0-9a-f]{40}", revision) or f"/{revision}/" not in url.path:
                raise ValueError(f"Source must use a commit SHA: {relative}")
        elif not re.fullmatch(r"\d{4}\.\d{4,5}v\d+", revision) or not url.path.endswith("/" + revision):
            raise ValueError(f"Paper must use an arXiv version: {relative}")
    return entries


def target_path(root: Path, entry: dict) -> Path:
    root = root.resolve()
    target = root.joinpath(*PurePosixPath(entry["path"]).parts)
    if target.is_symlink() or not target.resolve().is_relative_to(root):
        raise ValueError(f"Reference path escapes project or is a symlink: {entry['path']}")
    return target


def verify(data: bytes, entry: dict) -> None:
    if len(data) != entry["size_bytes"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
        raise ValueError(f"Size/hash mismatch: {entry['path']}; existing files are never overwritten")


def download(entry: dict) -> bytes:
    request = Request(entry["url"], headers={"User-Agent": "MoodCut-reference-reader/1.0"})
    with urlopen(request, timeout=45) as response:
        final_url = urlparse(response.geturl())
        if final_url.scheme != "https" or final_url.hostname not in HOSTS:
            raise ValueError("Unexpected download redirect")
        data = response.read(entry["size_bytes"] + 1)
    verify(data, entry)
    return data


def prepare(root: Path, entries: list[dict], *, check: bool = False,
            fetch=download) -> tuple[int, int]:
    cached = fetched = 0
    # Validate every destination and existing copy before downloading anything.
    missing = []
    for entry in entries:
        target = target_path(root, entry)
        if target.exists():
            if not target.is_file() or target.stat().st_size != entry["size_bytes"]:
                raise ValueError(f"Invalid existing reference: {entry['path']}")
            verify(target.read_bytes(), entry)
            cached += 1
        else:
            missing.append(entry)
    if check and missing:
        raise ValueError("Missing references: " + ", ".join(e["path"] for e in missing)
                         + "; rerun without --check to download")
    for entry in missing:
        print(f"Fetching {entry['path']}", flush=True)
        data = fetch(entry)
        verify(data, entry)
        target = target_path(root, entry)
        target.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation prevents accidental replacement of local annotations.
        with target.open("xb") as handle:
            handle.write(data)
        fetched += 1
    return cached, fetched


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify local files without network access")
    parser.add_argument("--papers", action="store_true", help="Include the two paper PDFs (about 57 MB)")
    parser.add_argument("--assets", action="store_true", help="Include two character images and captions (about 1.2 MB)")
    args = parser.parse_args(argv)
    groups = {"core"} | ({"papers"} if args.papers else set()) | ({"assets"} if args.assets else set())
    try:
        entries = [e for e in load_manifest(ROOT / "references/sources.lock.json") if e["group"] in groups]
        print(f"Selected {len(entries)} files, {sum(e['size_bytes'] for e in entries)} bytes")
        cached, fetched = prepare(ROOT, entries, check=args.check)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Reference preparation failed: {exc}", file=sys.stderr)
        return 1
    print(f"Verified {cached + fetched} references ({cached} cached, {fetched} downloaded). No upstream code executed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
