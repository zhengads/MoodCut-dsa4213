"""Offline VBench reporting helpers. No model imports or network requests."""
import csv
import json
import math
from collections import defaultdict
from pathlib import Path, PurePosixPath

CUSTOM_DIMENSIONS = (
    "subject_consistency", "background_consistency", "motion_smoothness",
    "dynamic_degree", "aesthetic_quality", "imaging_quality",
)


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def validate_video_manifest(rows):
    """Validate proposed metadata only; does not certify video existence/decoding."""
    if not isinstance(rows, list) or not rows:
        raise ValueError("Manifest must be a nonempty list")
    seen = set()
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            raise ValueError(f"Row {index}: expected an object")
        for field in ("video_id", "story_id", "method", "prompt", "video_path"):
            if not _text(row.get(field)):
                raise ValueError(f"Row {index}: missing {field}")
        if row["video_id"] in seen:
            raise ValueError(f"Row {index}: duplicate video_id")
        seen.add(row["video_id"])
        path = row["video_path"]
        parsed = PurePosixPath(path)
        if (parsed.is_absolute() or ".." in parsed.parts or ":" in path
                or "\\" in path or parsed.as_posix() != path
                or parsed.suffix.lower() != ".mp4"):
            raise ValueError(f"Row {index}: expected a relative MP4 path without traversal")
        if row.get("source_kind") not in ("synthetic", "development", "formal"):
            raise ValueError(f"Row {index}: invalid source_kind")
        if row.get("evaluation_unit") not in ("shot", "film"):
            raise ValueError(f"Row {index}: invalid evaluation_unit")
        seed = row.get("seed")
        if seed is not None and (type(seed) is not int or seed < 0):
            raise ValueError(f"Row {index}: seed must be a nonnegative integer or null")
    return rows


def summarize_vbench(manifest, results, *, dimensions):
    """Equal-video means per method/dimension; retain every planned video's coverage.

    Results use our normalized schema, NOT raw VBench output. Missing rows are
    counted separately from explicitly failed evaluations. No composite score.
    """
    validate_video_manifest(manifest)
    if (not dimensions or len(set(dimensions)) != len(dimensions)
            or any(d not in CUSTOM_DIMENSIONS for d in dimensions)):
        raise ValueError("Choose unique supported custom-input dimensions")
    if not isinstance(results, list):
        raise ValueError("Results must be a list")
    kinds = {r["source_kind"] for r in manifest}
    units = {r["evaluation_unit"] for r in manifest}
    if len(kinds) != 1 or len(units) != 1:
        raise ValueError("Do not mix source kinds or evaluation units")
    videos = {r["video_id"]: r for r in manifest}
    lookup = {}
    for index, row in enumerate(results, 1):
        if not isinstance(row, dict):
            raise ValueError(f"Result {index}: expected an object")
        vid, dim = row.get("video_id"), row.get("dimension")
        if not isinstance(vid, str) or vid not in videos or dim not in dimensions:
            raise ValueError(f"Result {index}: unknown video or dimension")
        key = (vid, dim)
        if key in lookup:
            raise ValueError(f"Result {index}: duplicate video/dimension")
        score = row.get("score")
        status = row.get("status")
        if status == "success":
            if type(score) not in (int, float) or not math.isfinite(score) or not 0 <= score <= 1:
                raise ValueError(f"Result {index}: expected finite score in [0, 1]")
        elif status == "failed":
            if score is not None or not _text(row.get("error")):
                raise ValueError(f"Result {index}: failure requires null score and error")
        else:
            raise ValueError(f"Result {index}: invalid status")
        lookup[key] = row
    groups = defaultdict(list)
    for row in manifest:
        groups[row["method"]].append(row["video_id"])
    summary = []
    for method, ids in sorted(groups.items()):
        for dim in dimensions:
            entries = [lookup.get((vid, dim)) for vid in ids]
            scores = [r["score"] for r in entries if r and r["status"] == "success"]
            summary.append({
                "method": method, "dimension": dim,
                "source_kind": next(iter(kinds)), "evaluation_unit": next(iter(units)),
                "planned": len(ids), "succeeded": len(scores),
                "failed": sum(r is not None and r["status"] == "failed" for r in entries),
                "missing": sum(r is None for r in entries),
                "mean_score": math.fsum(scores) / len(scores) if scores else None,
            })
    return summary


def export_vbench_summary(manifest, results, *, dimensions, output_path):
    """Create a new CSV; never replace an existing result file."""
    rows = summarize_vbench(manifest, results, dimensions=dimensions)
    with Path(output_path).open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return rows



def normalize_imaging_quality(raw, manifest, *, video_root):
    """Adapt pinned original VBench output; raw per-video MUSIQ scores use 0..100.

    Missing planned videos remain missing. Unknown or repeated paths are errors.
    Resolving full paths avoids silently matching two clips with the same filename.
    """
    validate_video_manifest(manifest)
    root = Path(video_root).resolve()
    paths = {}
    for row in manifest:
        path = (root / row["video_path"]).resolve()
        if not path.is_relative_to(root) or path in paths:
            raise ValueError("Video path escapes root or is duplicated")
        paths[path] = row["video_id"]
    if not isinstance(raw, dict) or set(raw) != {"imaging_quality"}:
        raise ValueError("Expected only imaging_quality in native results")
    value = raw["imaging_quality"]
    if not isinstance(value, list) or len(value) != 2 or not isinstance(value[1], list):
        raise ValueError("Expected [aggregate, per-video results]")
    aggregate, entries = value
    if type(aggregate) not in (int, float) or not math.isfinite(aggregate) or not 0 <= aggregate <= 1:
        raise ValueError("Invalid aggregate score")
    normalized, seen = [], set()
    for entry in entries:
        if not isinstance(entry, dict) or not _text(entry.get("video_path")):
            raise ValueError("Invalid native video entry")
        path = Path(entry["video_path"])
        path = (path if path.is_absolute() else root / path).resolve()
        if path not in paths or path in seen:
            raise ValueError("Unknown or duplicate native video path")
        seen.add(path)
        score = entry.get("video_results")
        if type(score) not in (int, float) or not math.isfinite(score) or not 0 <= score <= 100:
            raise ValueError("Expected native imaging-quality score in [0, 100]")
        normalized.append(dict(video_id=paths[path], dimension="imaging_quality",
                               status="success", score=score / 100.0))
    if not normalized or not math.isclose(
            math.fsum(r["score"] for r in normalized) / len(normalized), aggregate,
            rel_tol=1e-6, abs_tol=1e-8):
        raise ValueError("Native aggregate does not match per-video scores")
    return normalized



VBENCH_REVISION = "fd18b3d055cb0fc6f066ca90fe2c3c8cbb698490"
MUSIQ_SHA256 = "358bb6af275e28ea56821d44fb55c6cb83645db11f394d3ad65b2d149965ab50"


def run_imaging_quality_smoke(*, upstream_dir, cache_dir, output_dir):
    """Run an explicitly requested, CPU-only metric check on a generated 1s clip.

    Requires preinstalled dependencies and downloaded weights. No auto-downloads.
    Use a fresh Python process: upstream import paths and cache environment are set.
    """
    import hashlib
    import importlib.metadata
    import os
    import platform
    import subprocess
    import sys
    import time
    upstream, cache, out = map(lambda p: Path(p).resolve(),
                               (upstream_dir, cache_dir, output_dir))
    revision = subprocess.check_output(
        ["git", "-C", str(upstream), "rev-parse", "HEAD"], text=True).strip()
    if revision != VBENCH_REVISION:
        raise ValueError("Unexpected VBench revision")
    dirty = subprocess.check_output(
        ["git", "-C", str(upstream), "status", "--porcelain", "--untracked-files=no"], text=True)
    if dirty.strip():
        raise ValueError("Tracked VBench source files have local modifications")
    weight = cache / "pyiqa_model/musiq_spaq_ckpt-358bb6af.pth"
    if not weight.is_file() or hashlib.sha256(weight.read_bytes()).hexdigest() != MUSIQ_SHA256:
        raise ValueError("Missing or incorrect MUSIQ-SPAQ checkpoint")
    out.mkdir(parents=True, exist_ok=False)
    record = dict(status="started", source_kind="synthetic", device="cpu",
                  benchmark_revision=revision, weight_sha256=MUSIQ_SHA256,
                  preprocessing="longer", frames=8, fps=8, width=256, height=256,
                  python=platform.python_version(), platform=platform.platform())
    start = time.perf_counter()
    try:
        os.environ["VBENCH_CACHE_DIR"] = str(cache)
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        sys.path.insert(0, str(upstream))
        import cv2
        import numpy as np
        import torch
        from vbench import VBench
        record["packages"] = {n: importlib.metadata.version(n) for n in
            ("torch", "torchvision", "pyiqa", "timm", "numpy", "decord", "transformers")}
        torch.set_num_threads(2)
        torch.manual_seed(0)
        record["torch_threads"] = 2
        video = out / "procedural_test.mp4"
        writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"mp4v"), 8, (256, 256))
        if not writer.isOpened():
            raise RuntimeError("Could not create MP4 test video")
        try:
            for i in range(8):
                frame = np.zeros((256, 256, 3), dtype=np.uint8)
                frame[:, :, 0] = np.arange(256, dtype=np.uint8)[None, :]
                frame[:, :, 1] = np.arange(256, dtype=np.uint8)[:, None]
                frame[:, :, 2] = 80
                cv2.circle(frame, (48 + i * 20, 128), 24, (40, 220, 240), -1)
                writer.write(frame)
        finally:
            writer.release()
        record["video_sha256"] = hashlib.sha256(video.read_bytes()).hexdigest()
        manifest = [dict(video_id="procedural_001", story_id="test_only",
                         method="procedural_fixture", prompt="A circle moves over a gradient.",
                         video_path=video.name, seed=0, source_kind="synthetic", evaluation_unit="shot")]
        (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        evaluator = VBench(torch.device("cpu"), str(upstream / "vbench/VBench_full_info.json"), str(out))
        with torch.inference_mode():
            evaluator.evaluate(str(video), name="smoke", dimension_list=["imaging_quality"],
                               mode="custom_input", imaging_quality_preprocessing_mode="longer")
        raw = json.loads((out / "smoke_eval_results.json").read_text(encoding="utf-8"))
        normalized = normalize_imaging_quality(raw, manifest, video_root=out)
        (out / "normalized_results.json").write_text(json.dumps(normalized, indent=2), encoding="utf-8")
        export_vbench_summary(manifest, normalized, dimensions=["imaging_quality"],
                              output_path=out / "summary.csv")
        record.update(status="success", score=normalized[0]["score"])
    except Exception as exc:
        record.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        record["elapsed_s"] = time.perf_counter() - start
        (out / "run.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Summarize normalized VBench results offline")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--results", required=True)
    parser.add_argument("--dimensions", nargs="+", required=True, choices=CUSTOM_DIMENSIONS)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        export_vbench_summary(
            json.loads(Path(args.manifest).read_text(encoding="utf-8")),
            json.loads(Path(args.results).read_text(encoding="utf-8")),
            dimensions=args.dimensions, output_path=args.output)
    except (ValueError, OSError) as exc:
        parser.exit(1, f"Evaluation summary failed: {exc}\n")
