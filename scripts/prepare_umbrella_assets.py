"""Prepare the two explicitly selected sigils portraits; default is local only.

--fetch downloads only hash-pinned public sources, using the existing reference
downloader. No model APIs, uploads or request execution. --check never writes.
"""

import argparse
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import sys

from PIL import Image, PngImagePlugin

# Reuse the existing path guard, manifest builder and pinned-file downloader.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_assets import _relative, prepare_assets
from prepare_references import download, verify


ROOT = Path(__file__).resolve().parents[1]
LOCK = "assets/pilots/umbrella-sigils.lock.json"


def encode_png(data, *, credit, source_url, source_sha256):
    """Losslessly encode decoded RGB pixels, preserving XMP/ICC if supplied."""
    with Image.open(io.BytesIO(data)) as original:
        if original.format != "AVIF":
            raise ValueError("Expected the pinned original AVIF, not a renamed image")
        original.load()
        rgb = original.convert("RGB")
        metadata = PngImagePlugin.PngInfo()
        metadata.add_itxt("Attribution", credit)
        metadata.add_itxt("Source", source_url)
        metadata.add_itxt("SourceSHA256", source_sha256)
        metadata.add_itxt("Modification", "AVIF decoded to RGB PNG; no crop, resize or retouch")
        metadata.add_itxt("License", "CC BY 4.0; see the pinned LICENSE-PORTRAITS and credits")
        metadata.add_itxt("DigitalSourceType", "trainedAlgorithmicMedia; synthetic person")
        xmp = original.info.get("xmp")
        if xmp:
            metadata.add_itxt("XML:com.adobe.xmp", xmp.decode("utf-8") if isinstance(xmp, bytes) else xmp)
        output = io.BytesIO()
        rgb.save(output, format="PNG", pnginfo=metadata, compress_level=9,
                 optimize=False, icc_profile=original.info.get("icc_profile"))
        return output.getvalue(), hashlib.sha256(rgb.tobytes()).hexdigest(), list(rgb.size)


def prepare(lock, *, root=ROOT, fetch=False, check=False):
    root = Path(root).resolve()
    if lock.get("schema_version") != 1 or len(lock["portraits"]) != 2:
        raise ValueError("Expected the two-portrait pilot lock")
    if fetch and check:
        raise ValueError("--check cannot fetch")
    pending_sources = []
    sources = {}
    # Check every existing source before downloading anything; never repair it.
    for entry in lock["sources"]:
        target = _relative(root, entry["path"], raw=True)
        expected_prefix = f"https://raw.githubusercontent.com/ambravo/sigils-people/{lock['revision']}/"
        if not entry["url"].startswith(expected_prefix):
            raise ValueError("Source URL is outside the pinned sigils revision")
        if target.exists():
            data = target.read_bytes()
            verify(data, entry)
            sources[entry["path"]] = data
        else:
            pending_sources.append((entry, target))
    if pending_sources and not fetch:
        raise ValueError("Pinned sources missing; explicit --fetch is required")
    for entry, target in pending_sources:
        sources[entry["path"]] = download(entry)
    writes = [(target, sources[entry["path"]]) for entry, target in pending_sources]
    source_entries = {entry["path"]: entry for entry in lock["sources"]}
    for portrait in lock["portraits"]:
        raw = sources[portrait["original_path"]]
        source_entry = source_entries[portrait["original_path"]]
        if (source_entry["url"] != portrait["origin_url"]
                or source_entry["sha256"] != portrait["original_sha256"]):
            raise ValueError("Portrait origin URL/hash differs from its pinned source")
        expected = portrait["converted"]
        png, pixels, size = encode_png(raw, credit=lock["credit"],
            source_url=portrait["origin_url"], source_sha256=hashlib.sha256(raw).hexdigest())
        if (len(png) != expected["size_bytes"] or hashlib.sha256(png).hexdigest() != expected["sha256"]
                or pixels != expected["decoded_rgb_sha256"] or size != expected["dimensions"]):
            raise ValueError("Conversion differs from the lock; check Pillow/AVIF decoder versions, do not overwrite")
        target = _relative(root, expected["path"], raw=True)
        if target.exists():
            if target.read_bytes() != png:
                raise ValueError("Converted image differs; existing file preserved")
        elif check:
            raise ValueError("Converted image missing")
        else:
            writes.append((target, png))
    # All validation above precedes any writes; exclusive creation protects races.
    for target, data in writes:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as handle:
            handle.write(data)
    manifest = prepare_assets(lock["selection"], project_root=root)
    if manifest != lock["offline_manifest"]:
        raise ValueError("Prepared manifest differs from the reviewed offline manifest")
    return {"portraits_verified": 2, "source_files_verified": len(sources),
            "files_written": len(writes), "network_enabled": fetch,
            "delivery_urls_verified": False, "execution_enabled": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=str(ROOT))
    parser.add_argument("--lock", default=LOCK)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--fetch", action="store_true", help="Fetch missing pinned public files, then convert locally")
    modes.add_argument("--check", action="store_true", help="Local verification only, no writes or network")
    args = parser.parse_args(argv)
    try:
        root = Path(args.project_root).resolve()
        lock = json.loads(_relative(root, args.lock).read_text(encoding="utf-8"))
        result = prepare(lock, root=root, fetch=args.fetch, check=args.check)
        # The proposal contains the full hand-written fixture, so this check is
        # reproducible without the developer's ignored historical run directory.
        from moodcut.video_generation import build_generated_video_bundle, get_video_template_sha256
        proposal = json.loads((root / "docs/pilots/umbrella-single-shot.proposal.json").read_text(encoding="utf-8"))
        adaptation = proposal["offline_adaptation"]
        selection = proposal["selection"]
        if (selection["original_shot_index"] != 0 or selection["shot_id"] != "return-umbrella"
                or proposal["candidate_initial_plan"]["shots"][0]["shot_id"] != selection["shot_id"]):
            raise ValueError("This adapter checks only the original umbrella first shot")
        if proposal["execution_enabled"] or any(proposal["approval"].values()):
            raise ValueError("This lock is an unapproved offline proposal, not a runtime configuration")
        if adaptation["manifest"] != lock["offline_manifest"]:
            raise ValueError("Proposal manifest differs from the asset lock")
        plans = {c: deepcopy(proposal["candidate_initial_plan"]) for c in proposal["selection"]["conditions"]}
        for condition, plan in plans.items():
            plan["shots"][0]["dialogue"] = proposal["candidate_dialogues"][condition]
        bundle = build_generated_video_bundle(proposal["candidate_scene"], proposal["candidate_initial_plan"],
            plans, adaptation["manifest"], proposal["proposed_generation_settings"], project_root=root,
            template_sha256=get_video_template_sha256(), pricing_config=proposal["video_pricing"])
        if bundle["shared_generation_sha256"] != adaptation["offline_shared_generation_sha256"]:
            raise ValueError("Offline shared identity differs; review and recompile the proposal")
        fingerprints = {c["condition"]: c["jobs"][0]["request_sha256"] for c in bundle["conditions"]}
        if fingerprints != adaptation["selected_request_sha256"] or len(set(fingerprints.values())) != 3:
            raise ValueError("Selected request identities differ")
        common = []
        for condition in bundle["conditions"]:
            request = deepcopy(condition["jobs"][0]["request"])
            shared, dialogue = request["prompt"].split("SHARED_REQUIREMENTS_JSON:\n", 1)[1].split("\n\nDIALOGUE_JSON:\n", 1)
            if json.loads(dialogue) != proposal["candidate_dialogues"][condition["condition"]]:
                raise ValueError("Compiled dialogue differs")
            request["prompt"] = json.loads(shared)
            common.append(request)
        if not common[0] == common[1] == common[2]:
            raise ValueError("Three-condition common inputs differ")
        result["common_inputs_verified"] = True
        result["unique_selected_requests"] = len(set(fingerprints.values()))
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
        print(f"Pilot asset preparation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
