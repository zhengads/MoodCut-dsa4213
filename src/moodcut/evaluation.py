"""Offline reporting and explicitly invoked local VBench CPU evaluation."""
import csv
import hashlib
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



def _file_hash(path):
    import hashlib
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write(path, text):
    import os
    import tempfile
    path = Path(path)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _save_json(path, data):
    _atomic_write(path, json.dumps(data, indent=2, allow_nan=False))


def _batch_engine(manifest, *, video_root, output_dir, config, evaluate_one, resume=False):
    """Checkpoint orchestration; callback returns native imaging_quality results.

    Finished failures are retained. Changed inputs/config require a new run.
    Ctrl+C preserves completed items; a hard kill can leave a lock for manual review.
    """
    import hashlib
    import io
    import os
    import tempfile
    import time
    summarize_vbench(manifest, [], dimensions=["imaging_quality"])
    root, out = Path(video_root).resolve(), Path(output_dir).resolve()
    if not root.is_dir():
        raise ValueError("Video root must exist")
    sources, paths, seen = [], [], set()
    for row in manifest:
        path = (root / row["video_path"]).resolve()
        if not path.is_relative_to(root) or path in seen:
            raise ValueError("Video paths must be unique and inside video root")
        seen.add(path)
        if path.exists() and not path.is_file():
            raise ValueError("Video path is not a regular file")
        paths.append(path)
        sources.append(dict(path=str(path), sha256=_file_hash(path) if path.is_file() else None))
    identity = dict(schema_version=1, manifest=manifest, sources=sources, config=config)
    fingerprint = hashlib.sha256(json.dumps(identity, sort_keys=True, allow_nan=False).encode()).hexdigest()
    if resume:
        if not out.is_dir():
            raise ValueError("Resume requires an existing output directory")
    else:
        out.mkdir(parents=True, exist_ok=False)
    lock = out / "batch.lock"
    with lock.open("x", encoding="utf-8") as handle:
        handle.write(str(os.getpid()))
    try:
        checkpoint = out / "checkpoint.json"
        if resume:
            state = json.loads(checkpoint.read_text(encoding="utf-8"))
            if state.get("fingerprint") != fingerprint or state.get("identity") != identity:
                raise ValueError("Inputs or configuration changed; use a new output directory")
            summarize_vbench(manifest, state.get("results"), dimensions=["imaging_quality"])
        else:
            state = dict(fingerprint=fingerprint, identity=identity, results=[])
            _save_json(checkpoint, state)
        completed = {r["video_id"] for r in state["results"]}

        def reports():
            summary = summarize_vbench(manifest, state["results"], dimensions=["imaging_quality"])
            _save_json(out / "normalized_results.json", state["results"])
            buffer = io.StringIO(newline="")
            writer = csv.DictWriter(buffer, fieldnames=list(summary[0]))
            writer.writeheader()
            writer.writerows(summary)
            _atomic_write(out / "summary.csv", buffer.getvalue())
            return summary

        reports()
        for index, (row, path, source) in enumerate(zip(manifest, paths, sources)):
            if row["video_id"] in completed:
                continue
            attempt = Path(tempfile.mkdtemp(prefix=f"item-{index:04d}-", dir=out))
            start = time.perf_counter()
            result = dict(video_id=row["video_id"], dimension="imaging_quality", status="failed", score=None)
            try:
                if source["sha256"] is None:
                    raise FileNotFoundError("Video file is missing")
                if _file_hash(path) != source["sha256"]:
                    raise ValueError("Video changed after snapshot")
                raw = evaluate_one(path, attempt)
                if _file_hash(path) != source["sha256"]:
                    raise ValueError("Video changed during evaluation")
                _save_json(attempt / "native_result.json", raw)
                result = normalize_imaging_quality(raw, [row], video_root=root)[0]
            except Exception as exc:
                result["error"] = f"{type(exc).__name__}: {exc}"
            result.update(attempt_dir=attempt.name, video_sha256=source["sha256"],
                          elapsed_s=time.perf_counter() - start)
            state["results"].append(result)
            _save_json(checkpoint, state)
            reports()
        return reports()
    finally:
        lock.unlink()


def _imaging_worker(video, output, upstream, cache):
    """Fresh process isolates decoder errors and provides per-video timeouts."""
    import os
    import sys
    os.environ["VBENCH_CACHE_DIR"] = cache
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    sys.path.insert(0, upstream)
    import torch
    from vbench import VBench
    torch.set_num_threads(2)
    torch.manual_seed(0)
    with torch.inference_mode():
        VBench(torch.device("cpu"), str(Path(upstream) / "vbench/VBench_full_info.json"), output).evaluate(
            video, name="batch", dimension_list=["imaging_quality"], mode="custom_input",
            imaging_quality_preprocessing_mode="longer")


def run_imaging_quality_batch(manifest, *, video_root, upstream_dir, cache_dir,
                              output_dir, resume=False, timeout_s=300):
    """Evaluate manifest sequentially on CPU using verified local weights."""
    import importlib.metadata
    import os
    import platform
    import subprocess
    import sys
    if type(timeout_s) not in (int, float) or not math.isfinite(timeout_s) or timeout_s <= 0:
        raise ValueError("Timeout must be finite and positive")
    upstream, cache = Path(upstream_dir).resolve(), Path(cache_dir).resolve()
    revision = subprocess.check_output(["git", "-C", str(upstream), "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(["git", "-C", str(upstream), "status", "--porcelain"], text=True).strip()
    if revision != VBENCH_REVISION or dirty:
        raise ValueError("Expected clean pinned VBench checkout")
    weight = cache / "pyiqa_model/musiq_spaq_ckpt-358bb6af.pth"
    if not weight.is_file() or _file_hash(weight) != MUSIQ_SHA256:
        raise ValueError("Missing or incorrect MUSIQ checkpoint")
    packages = {d.metadata["Name"].lower(): d.version for d in importlib.metadata.distributions()}
    config = dict(revision=revision, weight_sha256=MUSIQ_SHA256, module_sha256=_file_hash(__file__),
                  device="cpu", threads=2, seed=0, preprocessing="longer", timeout_s=timeout_s,
                  packages=packages, python=sys.version, executable=sys.executable, platform=platform.platform())

    def evaluate_one(path, attempt):
        code = "from moodcut.evaluation import _imaging_worker; import sys; _imaging_worker(*sys.argv[1:])"
        env = dict(os.environ)
        env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
        with (attempt / "worker.log").open("w", encoding="utf-8") as log:
            try:
                proc = subprocess.run([sys.executable, "-B", "-c", code, str(path), str(attempt),
                                       str(upstream), str(cache)], stdout=log, stderr=subprocess.STDOUT,
                                      timeout=timeout_s, env=env)
            except subprocess.TimeoutExpired:
                raise TimeoutError(f"Evaluation exceeded {timeout_s}s; see worker.log") from None
        if proc.returncode:
            raise RuntimeError(f"Evaluation exited {proc.returncode}; see worker.log")
        return json.loads((attempt / "batch_eval_results.json").read_text(encoding="utf-8"))

    return _batch_engine(manifest, video_root=video_root, output_dir=output_dir,
                         config=config, evaluate_one=evaluate_one, resume=resume)


PAIRED_TONES = ("affectionate", "suspicious", "hostile")
PAIRED_CONDITIONS = ("baseline", "generic_review", "moodcut")
RATING_FIELDS = ("rater_id", "item_id", "perceived_tone", "confidence",
                 "naturalness", "story_clarity", "overstatement")


def build_assignments(scenes, *, replicates, tones, conditions):
    """List planned runs only; does not choose scenes, call models or render clips.

    Replicates start at one. IDs depend on scene/tone/replicate, never list position,
    and condition IDs extend the block ID. Changing a model/prompt requires a new
    run directory; an assignment ID is not a content fingerprint.
    """
    import copy
    import hashlib
    if not isinstance(scenes, list):
        raise ValueError("Scenes must be a list")
    if type(replicates) is not int or replicates < 1:
        raise ValueError("replicates must be a positive integer")
    for values, allowed, label in ((tones, PAIRED_TONES, "tones"),
                                    (conditions, PAIRED_CONDITIONS, "conditions")):
        if (not isinstance(values, list) or not values
                or any(not isinstance(v, str) or v not in allowed for v in values)
                or len(set(values)) != len(values)):
            raise ValueError(f"Choose unique supported {label}")
    seen, result = set(), []
    for index, scene in enumerate(scenes, 1):
        if not isinstance(scene, dict) or not _text(scene.get("scene_id")):
            raise ValueError(f"Scene {index}: missing scene_id")
        scene_id = scene["scene_id"]
        if scene_id in seen:
            raise ValueError(f"Scene {index}: duplicate scene_id")
        seen.add(scene_id)
        for tone in tones:
            for replicate in range(1, replicates + 1):
                identity = json.dumps([scene_id, tone, replicate], ensure_ascii=False,
                                      separators=(",", ":")).encode("utf-8")
                block_id = "block_" + hashlib.sha256(identity).hexdigest()
                for condition in conditions:
                    row = dict(schema_version="1.0", run_id=f"{block_id}_{condition}",
                               block_id=block_id, scene_id=scene_id, tone=tone,
                               replicate=replicate, condition=condition)
                    for field in ("source_kind", "provenance"):
                        if field in scene:
                            row[field] = copy.deepcopy(scene[field])
                    result.append(row)
    return result


def _paired_records(records):
    """Reject ambiguous identities and comparisons from different initial plans."""
    if not isinstance(records, list):
        raise ValueError("Records must be a list")
    run_ids, slots, blocks, identities, hashes, item_ids = set(), set(), {}, {}, {}, set()
    kinds = set()
    for index, row in enumerate(records, 1):
        prefix = f"Record {index}"
        if not isinstance(row, dict):
            raise ValueError(f"{prefix}: expected an object")
        for field in ("run_id", "block_id", "scene_id"):
            if not _text(row.get(field)):
                raise ValueError(f"{prefix}: missing {field}")
        if row.get("tone") not in PAIRED_TONES or row.get("condition") not in PAIRED_CONDITIONS:
            raise ValueError(f"{prefix}: invalid tone or condition")
        if type(row.get("replicate")) is not int or row["replicate"] < 1:
            raise ValueError(f"{prefix}: replicate must be positive integer")
        run_id, block_id = row["run_id"], row["block_id"]
        identity = row["scene_id"], row["tone"], row["replicate"]
        slot = block_id, row["condition"]
        if run_id in run_ids or slot in slots:
            raise ValueError(f"{prefix}: duplicate run_id or block/condition")
        if block_id in blocks and blocks[block_id] != identity:
            raise ValueError(f"{prefix}: block identity changed")
        if identity in identities and identities[identity] != block_id:
            raise ValueError(f"{prefix}: scene/tone/replicate has multiple block IDs")
        blocks[block_id], identities[identity] = identity, block_id
        run_ids.add(run_id)
        slots.add(slot)
        digest = row.get("initial_plan_sha256")
        if digest is not None:
            if (not isinstance(digest, str) or len(digest) != 64
                    or any(c not in "0123456789abcdef" for c in digest)):
                raise ValueError(f"{prefix}: invalid initial_plan_sha256")
            if block_id in hashes and hashes[block_id] != digest:
                raise ValueError(f"{prefix}: initial_plan_sha256 mismatch within block")
            hashes[block_id] = digest
        if row.get("render_status") == "rendered" and digest is None:
            raise ValueError(f"{prefix}: rendered run requires initial_plan_sha256")
        if "item_id" in row:
            if not _text(row["item_id"]) or row["item_id"] in item_ids:
                raise ValueError(f"{prefix}: missing or duplicate item_id")
            item_ids.add(row["item_id"])
        kind = row.get("source_kind", "unspecified")
        if not _text(kind):
            raise ValueError(f"{prefix}: source_kind must be nonempty")
        kinds.add(kind)
        for field in ("input_tokens", "output_tokens", "estimated_cost_usd",
                      "provider_cost_usd", "elapsed_s"):
            value = row.get(field)
            if value is not None and (type(value) not in (int, float)
                                      or not math.isfinite(value) or value < 0):
                raise ValueError(f"{prefix}: invalid {field}")
            if field in ("input_tokens", "output_tokens") and value is not None and type(value) is not int:
                raise ValueError(f"{prefix}: {field} must be an integer or null")
        calls = row.get("calls")
        if calls is not None and not (isinstance(calls, list)
                                      or type(calls) is int and calls >= 0):
            raise ValueError(f"{prefix}: calls must be list, nonnegative integer or null")
    if len(kinds) > 1:
        raise ValueError("Do not mix source_kind values in one report/export")
    return records



def validate_generated_comparison(records, *, scene, initial, plans, manifest,
                                  settings, template_sha256, project_root=None):
    """Recompute one block's generated input/review identities (CONTRACTS 6.5).

    Returns diagnostic strings without mutating records or approving media,
    ratings, accounting, or formal inclusion. Local reference assets are checked
    by the public validator relative to project_root (or cwd when omitted). No network.
    """
    from .contracts import (CONDITIONS, _json_copy, json_hash,
                            assert_dialogue_only_revision, shared_generation_sha256)
    from .validation import validate_plan
    errors = []
    try:
        records, scene, initial, plans, manifest, settings = _json_copy(
            [records, scene, initial, plans, manifest, settings])
    except ValueError as exc:
        return [str(exc)]
    if not all(isinstance(x, dict) for x in (scene, initial, plans, manifest, settings)):
        return ["scene, initial, plans, manifest and settings must be objects"]
    if set(plans) != set(CONDITIONS):
        errors.append("plans must contain exactly baseline/generic_review/moodcut")
    if not isinstance(records, list):
        return errors + ["records must be a list"]
    if len(records) != 3:
        errors.append("records must contain exactly three conditions")
    initial_hash = json_hash(initial)
    expected_shared = None
    try:
        errors.extend("initial: " + e for e in validate_plan(
            scene, initial, manifest, project_root=project_root, output_mode="generated"))
        expected_shared = shared_generation_sha256(
            scene, initial, manifest, settings, template_sha256=template_sha256)
    except (ValueError, TypeError, KeyError, OSError) as exc:
        errors.append(f"initial inputs: {exc}")
    final_hashes = {}
    for condition in CONDITIONS:
        plan = plans.get(condition)
        if not isinstance(plan, dict):
            errors.append(f"{condition}: missing plan object")
            continue
        final_hashes[condition] = json_hash(plan)
        try:
            errors.extend(f"{condition}: {e}" for e in validate_plan(
                scene, plan, manifest, project_root=project_root, output_mode="generated"))
            assert_dialogue_only_revision(initial, plan)
            shared = shared_generation_sha256(scene, plan, manifest, settings,
                                              template_sha256=template_sha256)
            if expected_shared is not None and shared != expected_shared:
                errors.append(f"{condition}: recomputed shared identity differs")
        except (ValueError, TypeError, KeyError, OSError) as exc:
            errors.append(f"{condition}: {exc}")
    if final_hashes.get("baseline") != initial_hash:
        errors.append("baseline must equal the complete initial plan")

    run_ids, conditions, block_ids, replicates, kinds, models = set(), set(), set(), set(), set(), set()
    selected_scopes = []
    for index, row in enumerate(records):
        prefix = f"record {index + 1}"
        if not isinstance(row, dict):
            errors.append(f"{prefix}: must be an object")
            continue
        condition = row.get("condition")
        if not isinstance(condition, str) or condition not in CONDITIONS:
            errors.append(f"{prefix}: unknown condition")
            continue
        prefix = condition
        if condition in conditions:
            errors.append(f"{prefix}: duplicate condition")
        conditions.add(condition)
        for field, seen in (("run_id", run_ids), ("block_id", block_ids),
                            ("source_kind", kinds), ("model_id", models)):
            value = row.get(field)
            if not _text(value):
                errors.append(f"{prefix}: {field} must be nonempty")
            else:
                if field == "run_id" and value in seen:
                    errors.append(f"{prefix}: duplicate run_id")
                seen.add(value)
        replicate = row.get("replicate")
        if type(replicate) is not int or replicate < 1:
            errors.append(f"{prefix}: invalid replicate")
        else:
            replicates.add(replicate)
        for field, expected in (("schema_version", "1.1"), ("output_mode", "generated"),
                                ("scene_id", scene.get("scene_id")), ("tone", scene.get("tone")),
                                ("initial_plan_sha256", initial_hash),
                                ("final_plan_sha256", final_hashes.get(condition)),
                                ("shared_generation_sha256", expected_shared),
                                ("video_model_id", settings.get("model"))):
            if expected is None or row.get(field) != expected:
                errors.append(f"{prefix}: {field} mismatch")
        hashes = row.get("prompt_hashes")
        if not isinstance(hashes, dict) or hashes.get("video_template") != template_sha256:
            errors.append(f"{prefix}: video template identity mismatch")
        status = row.get("review_status")
        allowed = ("not_applicable",) if condition == "baseline" else ("applied", "unchanged")
        if status not in allowed:
            errors.append(f"{prefix}: invalid review source {status!r}")
        if status == "unchanged" and final_hashes.get(condition) != initial_hash:
            errors.append(f"{prefix}: unchanged requires the complete initial plan")
        if row.get("run_status") == "failed" or row.get("generation_status") in ("failed", "interrupted"):
            errors.append(f"{prefix}: failed/interrupted run is not a valid comparison source")
        selected = row.get("selected_shot_ids")
        # Omitted selection denotes the complete plan; explicit subsets retain order.
        shots = initial.get("shots")
        full_ids = [shot.get("shot_id") for shot in shots if isinstance(shot, dict)] if isinstance(shots, list) else []
        if selected is None:
            selected = full_ids
        if (not isinstance(selected, list) or not selected
                or any(not isinstance(x, str) for x in selected)
                or len(set(selected)) != len(selected)
                or selected != [x for x in full_ids if x in selected]):
            errors.append(f"{prefix}: invalid selected_shot_ids")
        else:
            selected_scopes.append(tuple(selected))
    if conditions != set(CONDITIONS):
        errors.append("missing required comparison conditions")
    for name, values in (("block_id", block_ids), ("replicate", replicates),
                         ("source_kind", kinds), ("model_id", models)):
        if len(values) != 1:
            errors.append(f"records must share one {name}")
    if len(set(selected_scopes)) > 1:
        errors.append("records must share the same selected shot scope")
    return list(dict.fromkeys(errors))



def validate_generated_media_file(record, *, project_root):
    """Check final-file bytes against a P1 record; not full media qualification.

    Relative paths resolve against project_root. No decoding, receipts, subjective
    checks or status mutation are performed. Call again at the export boundary.
    """
    if not isinstance(record, dict):
        return ["record must be an object"]
    errors = []
    for field, expected in (("schema_version", "1.1"), ("output_mode", "generated"),
                            ("run_status", "completed"),
                            ("generation_status", "assembled_requires_manual_inspection")):
        if record.get(field) != expected:
            errors.append(f"{field} must be {expected}")
    check = record.get("media_check")
    if not isinstance(check, dict):
        return errors + ["missing media_check object"]
    digest = check.get("sha256")
    if (not isinstance(digest, str) or len(digest) != 64
            or any(c not in "0123456789abcdef" for c in digest)):
        errors.append("invalid media_check sha256")
    paths = [record.get("video_path"), check.get("video_path")]
    if any(not _text(path) for path in paths):
        return errors + ["video_path is required in record and media_check"]
    try:
        root = Path(project_root).resolve()
        resolved = [(Path(path) if Path(path).is_absolute() else root / path).resolve()
                    for path in paths]
        if resolved[0] != resolved[1]:
            errors.append("record and media_check video_path mismatch")
        if not resolved[0].is_file():
            errors.append("video file is missing or not a regular file")
        elif _file_hash(resolved[0]) != digest:
            errors.append("video bytes differ from media_check sha256")
    except (OSError, ValueError) as exc:
        errors.append(f"cannot read video file: {exc}")
    return errors


def validate_generated_source_bindings(record, compiled_condition, *, project_root):
    """Recheck ordered request/clip bindings; no receipt or quality approval.

    compiled_condition must come from the independently validated P4 bundle.
    P1's final media_check identifies the saved assembly sidecar when present.
    """
    from .contracts import json_hash, _json_copy
    errors = validate_generated_media_file(record, project_root=project_root)
    try:
        _json_copy([record, compiled_condition])
        if not isinstance(record, dict) or not isinstance(compiled_condition, dict):
            raise ValueError("record and compiled_condition must be objects")
        if (not _text(record.get("condition"))
                or record.get("condition") != compiled_condition.get("condition")):
            raise ValueError("compiled condition mismatch")
        jobs, compiled = record.get("generation_jobs"), compiled_condition.get("jobs")
        if (not isinstance(jobs, list) or not jobs or not isinstance(compiled, list)
                or len(jobs) != len(compiled)):
            raise ValueError("missing or inconsistent generation jobs")
        bindings, seen = [], set()
        for index, (job, source) in enumerate(zip(jobs, compiled)):
            if not isinstance(job, dict) or not isinstance(source, dict):
                raise ValueError("jobs must be objects")
            shot = source.get("shot_id")
            if not _text(shot) or shot in seen or job.get("shot_id") != shot:
                raise ValueError("duplicate or out-of-order source shot")
            seen.add(shot)
            request = source.get("request")
            if not isinstance(request, dict) or not request:
                raise ValueError("missing compiled request")
            digest = json_hash(request)
            if source.get("request_sha256") != digest or job.get("request_sha256") != digest:
                errors.append(f"shot {index + 1}: request identity mismatch")
            if job.get("status") != "downloaded":
                errors.append(f"shot {index + 1}: source clip is not downloaded")
            # Reuse byte/path checking without mutating the original job or ledger.
            clip_record = {**record, "video_path": job.get("video_path"),
                           "media_check": job.get("media_check")}
            errors.extend(f"shot {index + 1}: {e}" for e in
                          validate_generated_media_file(clip_record, project_root=project_root))
            check = job.get("media_check")
            bindings.append({"shot_id": shot, "request_sha256": digest,
                             "sha256": check.get("sha256") if isinstance(check, dict) else None})
        if record.get("selected_shot_ids") != [b["shot_id"] for b in bindings]:
            errors.append("selected shot order differs from source jobs")
        check = record.get("media_check")
        if not isinstance(check, dict):
            raise ValueError("missing final media_check")
        sidecar = check.get("source_media_check_path")
        if sidecar is None:
            if len(bindings) != 1 or check.get("sha256") != bindings[0]["sha256"]:
                errors.append("assembly sidecar required unless final file equals the single source clip")
        else:
            if not _text(sidecar):
                raise ValueError("invalid assembly sidecar path")
            path = Path(sidecar)
            if not path.is_absolute():
                path = Path(project_root) / path
            saved = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(saved, dict):
                raise ValueError("assembly sidecar must be an object")
            if json_hash(saved) != check.get("source_media_check_sha256"):
                errors.append("assembly sidecar identity mismatch")
            if saved.get("source_clips") != bindings:
                errors.append("assembly source clip/request order mismatch")
            if saved.get("sha256") != check.get("sha256"):
                errors.append("assembly final-file identity mismatch")
    except (ValueError, TypeError, KeyError, OSError) as exc:
        errors.append(f"source bindings: {exc}")
    return list(dict.fromkeys(errors))


def validate_generated_receipt_binding(job, *, expected_model, project_root):
    """Recheck a saved P1 job's receipt identity, without polling or accounting.

    Request identity must already be checked against the validated P4 bundle.
    Reused jobs retain the owner's receipt; this does not validate reuse ownership.
    """
    from .contracts import json_hash, _json_copy
    import re
    errors = []
    try:
        _json_copy(job)
        if not isinstance(job, dict):
            raise ValueError("job must be an object")
        if not _text(expected_model):
            raise ValueError("expected_model is required")
        if not _text(job.get("receipt_path")):
            raise ValueError("receipt_path is required")
        root = Path(project_root).resolve()
        path = Path(job["receipt_path"])
        path = (path if path.is_absolute() else root / path).resolve()
        receipt = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(receipt, dict):
            raise ValueError("receipt must be an object")
        if json_hash(receipt) != job.get("receipt_sha256"):
            errors.append("saved receipt identity mismatch")
        if receipt.get("schema_version") not in ("1.0", "1.1"):
            errors.append("unsupported receipt schema_version")
        request_hash = job.get("request_sha256")
        if (not isinstance(request_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", request_hash)
                or receipt.get("request_sha256") != request_hash):
            errors.append("receipt request identity mismatch")
        if receipt.get("model") != expected_model:
            errors.append("receipt model mismatch")
        job_id = job.get("job_id")
        if (not isinstance(job_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,160}", job_id)
                or receipt.get("job_id") != job_id):
            errors.append("receipt job_id mismatch")
        if job.get("status") != "downloaded" or receipt.get("status") != "downloaded":
            errors.append("job and receipt must both be downloaded")
        if not _text(receipt.get("video_path")) or not _text(job.get("video_path")):
            errors.append("receipt and job video_path are required")
        else:
            saved_video, job_video = Path(receipt["video_path"]), Path(job["video_path"])
            saved_video = (saved_video if saved_video.is_absolute() else path.parent / saved_video).resolve()
            job_video = (job_video if job_video.is_absolute() else root / job_video).resolve()
            if saved_video != job_video:
                errors.append("receipt video_path mismatch")
    except (ValueError, TypeError, KeyError, OSError) as exc:
        errors.append(f"receipt binding: {exc}")
    return errors


def validate_generated_media_evidence(record, compiled_condition, *, project_root):
    """Combine file, source and receipt checks for one validated P4 condition.

    Returns all available diagnostics without filtering records or approving
    comparison eligibility. This is not the block input or reuse/accounting check.
    """
    errors = validate_generated_source_bindings(
        record, compiled_condition, project_root=project_root)
    if not isinstance(record, dict) or not isinstance(compiled_condition, dict):
        return errors
    jobs, compiled = record.get("generation_jobs"), compiled_condition.get("jobs")
    if not isinstance(jobs, list) or not isinstance(compiled, list):
        return errors
    # Source validation checks ordering and count; continue matching pairs to
    # collect receipt errors even when a file or request check already failed.
    for index, (job, source) in enumerate(zip(jobs, compiled)):
        request = source.get("request") if isinstance(source, dict) else None
        model = request.get("model") if isinstance(request, dict) else None
        if not _text(model) or record.get("video_model_id") != model:
            errors.append(f"shot {index + 1}: compiled model differs from video_model_id")
        errors.extend(f"shot {index + 1}: {error}" for error in
                      validate_generated_receipt_binding(
                          job, expected_model=model, project_root=project_root))
    return list(dict.fromkeys(errors))


def qualify_generated_records(records, *, pricing_config, project_root="."):
    """Report offline evidence eligibility; never mutate records or release export.

    P1 replays its own source/reuse/accounting computation and P4 recompiles saved
    requests. Unknown spending is retained, not a quality score or automatic veto.
    An eligible report is point-in-time software evidence, not formal inclusion.
    """
    import subprocess
    from .contracts import CONDITIONS, json_hash, _json_copy
    from .pipeline import read_json, recheck_generated_records
    path = Path(records).resolve()
    path = path / "block.json" if path.is_dir() else path
    block, context = None, None
    errors, per_condition = [], {c: [] for c in CONDITIONS}
    try:
        block = _json_copy(read_json(path))
        context = recheck_generated_records(path, pricing_config=pricing_config, project_root=project_root)
        block = context["block"]  # Report the exact snapshot that P1 verified.
        errors.extend(context["errors"])
        for condition in CONDITIONS:
            per_condition[condition].extend(context["condition_errors"][condition])
        source = context["source"]
        input_errors = validate_generated_comparison(block["runs"], **source, project_root=project_root)
        for error in input_errors:
            condition, separator, detail = error.partition(": ")
            if separator and condition in per_condition:
                per_condition[condition].append(detail)
            else:
                errors.append(error)
        compiled = {c["condition"]: c for c in context["bundle"]["conditions"]}
        for row in block["runs"]:
            per_condition[row["condition"]].extend(validate_generated_media_evidence(
                row, compiled[row["condition"]], project_root=project_root))
    except (ValueError, TypeError, KeyError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
        errors.append(f"source/evidence recheck: {type(exc).__name__}: {exc}")
    conditions = []
    for condition in CONDITIONS:
        diagnostics = list(dict.fromkeys([*errors, *per_condition[condition]]))
        conditions.append(dict(condition=condition,
            comparison_status="ineligible" if diagnostics else "eligible", errors=diagnostics))
    return dict(schema_version="1.1", output_mode="generated", kind="generated_qualification_report",
                comparison_status="eligible" if all(not c["errors"] for c in conditions) else "ineligible",
                records_sha256=json_hash(block) if block is not None else None,
                record_block=block, conditions=conditions, errors=list(dict.fromkeys(errors)),
                accounting_verified=context is not None and not context["errors"]
                    and all(not e for e in context["condition_errors"].values()),
                formal_inclusion_approved=False, speech_and_visual_quality="not_reviewed",
                export_enabled=False,
                activity=dict(real_http_calls=0, generation_posts=0, video_get_calls=0, provider_cost_usd=0.0))


def export_blind_items(records, *, out_dir, seed):
    """Export legacy animatics; generated media require the rechecking entrypoint."""
    if any(row.get("output_mode") == "generated" for row in records):
        raise ValueError("Generated export requires export_generated_blind_items with final block paths")
    return _export_blind_items(records, out_dir=out_dir, seed=seed)


def _export_blind_items(records, *, out_dir, seed, expected_video_hashes=None):
    """Copy existing rendered MP4s under anonymous names and create empty ratings.

    Only ``public/`` is for raters. ``PRIVATE/`` contains the answer key and must
    stay private. Existence/nonempty bytes are checked; this is not a decoder or
    proof a clip plays correctly. Inspect clips before distributing them. No
    rater schedule is invented: the coordinator must avoid adjacent story variants.
    """
    import random
    import shutil
    _paired_records(records)
    if type(seed) is not int:
        raise ValueError("seed must be an integer")
    out = Path(out_dir).resolve()
    if out.exists():
        raise FileExistsError(f"Blind export output already exists: {out}")
    eligible = []
    for index, row in enumerate(records, 1):
        if row.get("render_status") != "rendered":
            continue
        path = row.get("video_path")
        if not _text(path):
            raise ValueError(f"Record {index}: rendered run requires video_path")
        source = Path(path).resolve()
        if (source.suffix.lower() != ".mp4" or not source.is_file()
                or source.stat().st_size == 0):
            raise ValueError(f"Record {index}: missing/nonempty MP4 required")
        if source.is_relative_to(out):
            raise ValueError(f"Record {index}: input video must be outside export output")
        eligible.append((row, source))
    eligible.sort(key=lambda pair: pair[0]["run_id"])
    random.Random(seed).shuffle(eligible)
    out.mkdir(parents=True, exist_ok=False)
    public, private = out / "public", out / "PRIVATE"
    videos = public / "videos"
    videos.mkdir(parents=True)
    private.mkdir()
    blind, keys, record_items = [], [], []
    for number, (row, source) in enumerate(eligible, 1):
        item_id = f"item_{number:05d}"
        video_file = f"videos/{item_id}.mp4"
        destination = public / video_file
        expected = expected_video_hashes[row["run_id"]] if expected_video_hashes is not None else None
        if expected is not None and _file_hash(source) != expected:
            raise ValueError("Generated source video changed before copying")
        # Exclusive creation avoids silent replacement even if another process interferes.
        with source.open("rb") as incoming, destination.open("xb") as outgoing:
            shutil.copyfileobj(incoming, outgoing)
        copied_hash = _file_hash(destination)
        if expected is not None and (copied_hash != expected or _file_hash(source) != expected):
            raise ValueError("Generated source/export video changed during copying")
        blind.append(dict(item_id=item_id, video_file=video_file))
        keys.append(dict(item_id=item_id, run_id=row["run_id"], block_id=row["block_id"],
                         scene_id=row["scene_id"], replicate=row["replicate"],
                         condition=row["condition"], target_tone=row["tone"],
                         initial_plan_sha256=row["initial_plan_sha256"],
                         video_sha256=copied_hash,
                         source_kind=row.get("source_kind", "unspecified"),
                         provenance=json.dumps(row.get("provenance"), ensure_ascii=False)))
        record_items.append(dict(run_id=row["run_id"], item_id=item_id))

    def write_csv(path, fieldnames, rows):
        with path.open("x", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    write_csv(public / "blind_items.csv", ("item_id", "video_file"), blind)
    # Empty fields are intentional, not synthetic human responses.
    write_csv(public / "ratings.csv", RATING_FIELDS,
              [dict.fromkeys(RATING_FIELDS, "") | {"item_id": row["item_id"]} for row in blind])
    key_fields = ("item_id", "run_id", "block_id", "scene_id", "replicate", "condition",
                  "target_tone", "initial_plan_sha256", "video_sha256", "source_kind", "provenance")
    write_csv(private / "private_key.csv", key_fields, keys)
    return dict(public_dir=str(public), blind_items_path=str(public / "blind_items.csv"),
                ratings_path=str(public / "ratings.csv"),
                private_key_path=str(private / "private_key.csv"),
                record_items=record_items, exported_clips=len(blind),
                excluded_runs=len(records) - len(blind), seed=seed,
                source_kind=records[0].get("source_kind", "unspecified") if records else None,
                video_check="existing_nonempty_mp4_only_not_decoder_verified",
                scheduling_note="Assign raters separately; avoid adjacent variants of one story.")


def _generated_evaluation_inputs(record_paths, *, pricing_config, project_root):
    """Load final ledgers once and qualify that exact snapshot, including failures."""
    from .contracts import CONDITIONS, json_hash
    from .pipeline import read_json
    if not record_paths or not pricing_config:
        raise ValueError("Generated evaluation requires final block paths and explicit pricing_config")
    root, paths, reports, records = Path(project_root).resolve(), [], [], []
    pricing_config = (root / pricing_config).resolve()
    for value in record_paths:
        path = (root / value).resolve()
        path = path / "block.json" if path.is_dir() else path
        if path in paths:
            raise ValueError("Duplicate final block path")
        block = read_json(path)
        if (not isinstance(block, dict) or block.get("kind") != "generated_record_block"
                or block.get("schema_version") != "1.1" or block.get("output_mode") != "generated"
                or not isinstance(block.get("runs"), list)
                or not all(isinstance(r, dict) for r in block["runs"])
                or [r.get("condition") for r in block.get("runs", [])] != list(CONDITIONS)):
            raise ValueError("Generated evaluation accepts complete final generated_record_block files only")
        report = qualify_generated_records(path, pricing_config=pricing_config, project_root=root)
        if report["records_sha256"] != json_hash(block):
            raise ValueError("Final block changed during qualification")
        paths.append(path)
        reports.append(report)
        records.extend(block["runs"])
    _paired_records(records)
    return paths, reports, records


def _generated_evaluation_summary(reports, records, ratings):
    """Reuse score arithmetic and retain original once-per-block ledgers verbatim."""
    result = _summarize(records, ratings)
    ledgers = [dict(block_id=r["record_block"]["block_id"],
                    accounting_verified=r["accounting_verified"],
                    accounting=r["record_block"]["accounting"]) for r in reports]
    result.update(generated_qualification=reports,
                  formal_inclusion_approved=False, speech_and_visual_quality="not_reviewed",
                  block_ledger_accounting=dict(blocks=ledgers,
                      complete=all(r["accounting_verified"] for r in reports),
                      note="Original final ledgers, each block once including shared planning and reuse; preflight excluded."))
    result["interpretation"]["validity"] = (
        "Offline qualification checks saved software evidence, not provider authenticity, speech/visual quality or formal inclusion.")
    result["interpretation"]["confounds"] = (
        "Human allocation, missing ratings, software eligibility and development/synthetic source limitations require disclosure.")
    return result


def _read_evaluation_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def export_generated_blind_items(record_paths, *, out_dir, seed, pricing_config, project_root="."):
    """Requalify, copy anonymously, bind actual bytes and publish only a complete package.

    Only whole software-eligible blocks are copied. Every input remains in the
    private diagnostic summary; this is not approval of a formal inclusion rule.
    """
    import tempfile
    from .pipeline import write_json
    paths, reports, records = _generated_evaluation_inputs(
        record_paths, pricing_config=pricing_config, project_root=project_root)
    eligible_blocks = {r["record_block"]["block_id"] for r in reports if r["comparison_status"] == "eligible"}
    selected = [r for r in records if r["block_id"] in eligible_blocks]
    # Resolve only a copy; never retag original records or overwrite source paths.
    selected = [dict(r, video_path=str((Path(project_root) / r["video_path"]).resolve())) for r in selected]
    expected = {r["run_id"]: r["media_check"]["sha256"] for r in selected}
    out = Path(out_dir).resolve()
    if out.exists() or out.is_symlink():
        raise FileExistsError(f"Blind export output already exists: {out}")
    out.parent.mkdir(parents=True, exist_ok=True)
    # A failed copy/recheck never exposes a public directory at the requested path.
    with tempfile.TemporaryDirectory(prefix=".blind-export-", dir=out.parent) as temporary:
        staged = Path(temporary) / "package"
        exported = _export_blind_items(selected, out_dir=staged, seed=seed, expected_video_hashes=expected)
        _, after, _ = _generated_evaluation_inputs(paths, pricing_config=pricing_config, project_root=project_root)
        if after != reports:
            raise ValueError("Generated evidence changed during blind export")
        summary = _generated_evaluation_summary(reports, records, [])
        write_json(staged / "PRIVATE/summary.json", summary)
        manifest = dict(kind="generated_blind_export", schema_version="1.1", seed=seed,
            records=[dict(path=str(p), sha256=r["records_sha256"]) for p, r in zip(paths, reports)],
            items=[dict(row, video_sha256=expected[row["run_id"]]) for row in exported["record_items"]],
            private_key_sha256=_file_hash(staged / "PRIVATE/private_key.csv"),
            blind_items_sha256=_file_hash(staged / "public/blind_items.csv"),
            formal_inclusion_approved=False, eligibility_scope="whole offline-qualified blocks only")
        write_json(staged / "PRIVATE/generated_export.json", manifest)
        for item in manifest["items"]:
            if _file_hash(staged / "public/videos" / f"{item['item_id']}.mp4") != item["video_sha256"]:
                raise ValueError("Exported video changed before publication")
        if out.exists() or out.is_symlink():
            raise FileExistsError(f"Blind export output already exists: {out}")
        staged.rename(out)
    # Return final paths rather than temporary staging paths.
    for field in ("public_dir", "blind_items_path", "ratings_path", "private_key_path"):
        exported[field] = str(out / Path(exported[field]).relative_to(staged))
    exported.update(excluded_runs=len(records) - len(selected),
        summary_path=str(out / "PRIVATE/summary.json"), manifest_path=str(out / "PRIVATE/generated_export.json"),
        formal_inclusion_approved=False, video_check="offline_qualified_source_and_export_byte_hashes",
        speech_and_visual_quality="not_reviewed",
        source_kind=records[0]["source_kind"],
        eligibility_scope="whole offline-qualified blocks only; all input records retained privately")
    return exported


def summarize_generated_records(record_paths, ratings, *, private_key=None, pricing_config, project_root="."):
    """Recheck current sources AND exported bytes before joining supplied ratings."""
    from .pipeline import read_json
    paths, reports, records = _generated_evaluation_inputs(
        record_paths, pricing_config=pricing_config, project_root=project_root)
    if private_key is None:
        if ratings:
            raise ValueError("Generated ratings require the matching private key")
        return _generated_evaluation_summary(reports, records, [])
    key_path = Path(private_key).resolve()
    package = key_path.parent.parent
    manifest = read_json(key_path.parent / "generated_export.json")
    if not isinstance(manifest, dict):
        raise ValueError("Invalid generated export manifest")
    current = {str(p): r["records_sha256"] for p, r in zip(paths, reports)}
    saved = manifest.get("records", [])
    if (not isinstance(saved, list) or not all(isinstance(r, dict) and
            isinstance(r.get("path"), str) and isinstance(r.get("sha256"), str) for r in saved)):
        raise ValueError("Invalid generated export record identities")
    if (manifest.get("kind") != "generated_blind_export" or manifest.get("schema_version") != "1.1"
            or len(saved) != len(current) or {r["path"]: r["sha256"] for r in saved} != current):
        raise ValueError("Generated export does not match all supplied final blocks")
    index_path = package / "public/blind_items.csv"
    if (_file_hash(key_path) != manifest.get("private_key_sha256")
            or _file_hash(index_path) != manifest.get("blind_items_sha256")):
        raise ValueError("Generated private key or public index changed after export")
    keys, index = _read_evaluation_csv(key_path), _read_evaluation_csv(index_path)
    eligible = {r["record_block"]["block_id"] for r in reports if r["comparison_status"] == "eligible"}
    expected_runs = {r["run_id"] for r in records if r["block_id"] in eligible}
    # Exact bijection, including currently unrated exports; no silent subset key.
    items = manifest.get("items", [])
    if (not isinstance(items, list) or not all(isinstance(i, dict) and all(
            isinstance(i.get(f), str) for f in ("run_id", "item_id", "video_sha256")) for i in items)):
        raise ValueError("Invalid generated export item identities")
    if (len(items) != len(expected_runs) or {i["run_id"] for i in items} != expected_runs
            or len({i["item_id"] for i in items}) != len(items)
            or len(keys) != len(items) or len(index) != len(items)):
        raise ValueError("Generated export mapping is incomplete or software eligibility changed")
    by_run = {r["run_id"]: r for r in records}
    mapping = {}
    for key, public, item in zip(keys, index, items):
        record = by_run[item["run_id"]]
        item_id = item["item_id"]
        # Anonymous IDs are generated locally, never interpreted as arbitrary paths.
        if (item_id != f"item_{len(mapping) + 1:05d}"
                or public != dict(item_id=item_id, video_file=f"videos/{item_id}.mp4")):
            raise ValueError("Generated public mapping has invalid anonymous IDs/paths")
        expected_key = {field: str(record[field]) for field in
                        ("run_id", "block_id", "scene_id", "replicate", "condition", "initial_plan_sha256", "source_kind")}
        expected_key.update(item_id=item_id, target_tone=record["tone"],
            video_sha256=record["media_check"]["sha256"],
            provenance=json.dumps(record.get("provenance"), ensure_ascii=False))
        if (key != expected_key or item["video_sha256"] != record["media_check"]["sha256"]
                or _file_hash(package / "public" / public["video_file"]) != item["video_sha256"]):
            raise ValueError("Generated private mapping/exported video does not match current source evidence")
        mapping[item["run_id"]] = item_id
    # Reject run_id fallback votes: generated scores must reference actual exports.
    if any(r.get("item_id") not in set(mapping.values()) for r in ratings):
        raise ValueError("Generated rating item_id was not exported")
    mapped = [dict(r, item_id=mapping[r["run_id"]]) if r["run_id"] in mapping else dict(r) for r in records]
    return _generated_evaluation_summary(reports, mapped, ratings)


def _paired_total(rows, field):
    values = [row.get(field) for row in rows]
    known = [value for value in values if value is not None]
    return dict(total=math.fsum(known) if len(known) == len(values) else None,
                known_subtotal=math.fsum(known), unknown_runs=len(values) - len(known))


def summarize(records, ratings):
    """Keep generated ratings behind source/export validation; diagnostics stay readable."""
    if ratings and any(row.get("output_mode") == "generated" for row in records):
        raise ValueError("Generated ratings require summarize_generated_records and the exported private key")
    return _summarize(records, ratings)


def _generation_coverage(rows):
    """Count saved run/job states without inferring submission, calls or quality.

    These are overlapping diagnostic axes, not extra runs or provider tasks.
    Unknown/missing states stay unknown; receipt availability is not submission.
    """
    generated = [r for r in rows if r.get("output_mode") == "generated"]
    run_states = ("not_started", "prepared_offline", "in_progress",
                  "assembled_requires_manual_inspection", "failed", "interrupted", "unknown")
    job_states = ("prepared_offline", "submitting", "in_progress", "downloaded", "failed", "interrupted", "unknown")
    runs, jobs = dict.fromkeys(run_states, 0), dict.fromkeys(job_states, 0)
    causes, remote = defaultdict(int), defaultdict(int)
    awaiting, unsubmitted, empty, invalid, reused, missing_remote, before_generation = (0,) * 7
    for row in generated:
        state = row.get("generation_status")
        runs[state if isinstance(state, str) and state in runs else "unknown"] += 1
        if row.get("run_status") == "failed":
            cause = row.get("failure_kind")
            causes[cause if _text(cause) else "unspecified"] += 1
            before_generation += state == "not_started"
        entries = row.get("generation_jobs")
        if not isinstance(entries, list):
            invalid += 1
            continue
        empty += not entries
        invalid += any(not isinstance(j, dict) for j in entries)
        statuses = []
        for job in entries:
            job = job if isinstance(job, dict) else {}
            value = job.get("status")
            status = value if isinstance(value, str) and value in jobs else "unknown"
            statuses.append(status)
            jobs[status] += 1
            value = job.get("remote_status")
            if _text(value):
                remote[value] += 1
            else:
                missing_remote += 1
            reused += job.get("reused_from") is not None
        unsubmitted += "prepared_offline" in statuses
        awaiting += (state == "in_progress" and row.get("render_status") != "rendered"
                     and bool(statuses) and all(s == "downloaded" for s in statuses))
    return dict(generated_runs=len(generated), not_applicable_runs=len(rows) - len(generated),
                by_status=runs, pre_generation_failed_runs=before_generation,
                failed_run_causes=dict(sorted(causes.items())), awaiting_assembly_runs=awaiting,
                runs_with_unsubmitted_jobs=unsubmitted, runs_with_empty_job_records=empty,
                runs_with_invalid_job_records=invalid,
                jobs=dict(recorded_jobs=sum(jobs.values()), by_status=jobs,
                          remote_status_counts=dict(sorted(remote.items())),
                          jobs_without_remote_status=missing_remote, declared_reused_jobs=reused))


def _summarize(records, ratings):
    """Summarize supplied human ratings with equal clip weight and full coverage.

    Ratings join via records.item_id (from PRIVATE/private_key.csv); unexported
    callers may explicitly use run_id as item_id. Unknown/duplicate rows are
    errors, including blank template rows. Model verification is never a rating.
    Failures stay in coverage/cost denominators, but unrendered clips cannot get
    human scores. Common-block differences describe the jointly rated subset.
    """
    records = _paired_records(records)
    has_generated = any(row.get("output_mode") == "generated" for row in records)
    if not isinstance(ratings, list):
        raise ValueError("Ratings must be a list")
    by_item = {}
    for row in records:
        item_id = row.get("item_id", row["run_id"])
        if item_id in by_item:
            raise ValueError("Ambiguous item_id/run_id mapping")
        by_item[item_id] = row
    seen, grouped = set(), defaultdict(list)
    for index, rating in enumerate(ratings, 2):
        prefix = f"Rating CSV row {index}"
        if not isinstance(rating, dict) or any(field not in rating for field in RATING_FIELDS):
            raise ValueError(f"{prefix}: missing required fields")
        if not _text(rating["rater_id"]) or not _text(rating["item_id"]):
            raise ValueError(f"{prefix}: rater_id and item_id must be nonempty")
        item_id = rating["item_id"]
        if item_id not in by_item:
            raise ValueError(f"{prefix}: unknown item_id")
        row = by_item[item_id]
        if row.get("render_status") != "rendered":
            raise ValueError(f"{prefix}: ratings require a rendered clip")
        key = rating["rater_id"], item_id
        if key in seen:
            raise ValueError(f"{prefix}: duplicate rater/item pair")
        seen.add(key)
        if rating["perceived_tone"] not in (*PAIRED_TONES, "uncertain"):
            raise ValueError(f"{prefix}: invalid perceived_tone")
        normalized = dict(rating)
        for field in RATING_FIELDS[3:]:
            value = rating[field]
            if isinstance(value, str) and value in ("1", "2", "3", "4", "5"):
                value = int(value)
            if type(value) is not int or not 1 <= value <= 5:
                raise ValueError(f"{prefix}: {field} must be integer 1..5")
            normalized[field] = value
        grouped[row["run_id"]].append(normalized)

    clip_scores = {}
    for row in records:
        votes = grouped.get(row["run_id"], [])
        if votes:
            clip_scores[row["run_id"]] = dict(
                tone_accuracy=sum(v["perceived_tone"] == row["tone"] for v in votes) / len(votes),
                **{field: math.fsum(v[field] for v in votes) / len(votes)
                   for field in RATING_FIELDS[3:]})

    def aggregate(rows):
        scored = [clip_scores[row["run_id"]] for row in rows if row["run_id"] in clip_scores]
        votes = [(row["tone"], vote) for row in rows for vote in grouped.get(row["run_id"], [])]
        confusion = {tone: {predicted: 0 for predicted in (*PAIRED_TONES, "uncertain")}
                     for tone in PAIRED_TONES}
        for target, vote in votes:
            confusion[target][vote["perceived_tone"]] += 1
        rendered = sum(row.get("render_status") == "rendered" for row in rows)
        call_counts = []
        for row in rows:
            calls = row.get("calls")
            call_counts.append(len(calls) if isinstance(calls, list) else calls)
        known_calls = [n for n in call_counts if n is not None]
        return dict(
            **({"generation": _generation_coverage(rows)} if has_generated else {}),
            coverage=dict(planned_runs=len(rows), rendered_runs=rendered,
                          render_failed_runs=sum(row.get("render_status") == "render_failed" for row in rows),
                          render_pending_or_skipped_runs=sum(row.get("render_status") not in
                              ("rendered", "render_failed") for row in rows),
                          review_failed_runs=sum(row.get("review_status") == "review_failed" for row in rows),
                          review_rejected_runs=sum(row.get("review_status") == "rejected" for row in rows),
                          review_applied_runs=sum(row.get("review_status") == "applied" for row in rows),
                          review_unchanged_runs=sum(row.get("review_status") == "unchanged" for row in rows),
                          review_not_applicable_runs=sum(row.get("review_status") == "not_applicable" for row in rows),
                          review_unknown_status_runs=sum(row.get("review_status") not in
                              ("applied", "unchanged", "not_applicable", "review_failed", "rejected") for row in rows),
                          rendered_review_failure_runs=sum(row.get("render_status") == "rendered" and
                              row.get("review_status") in ("review_failed", "rejected") for row in rows),
                          no_rendered_video_runs=len(rows) - rendered,
                          timeout_runs=sum(row.get("failure_kind") == "timeout" for row in rows),
                          budget_refused_runs=sum(row.get("failure_kind") == "budget" for row in rows),
                          known_zero_call_runs=sum(n == 0 for n in call_counts),
                          rated_clips=len(scored), ratings=len(votes),
                          missing_ratings=len(rows) - len(scored),
                          rendered_but_unrated_clips=rendered - len(scored),
                          independent_scenes=len({row["scene_id"] for row in rows}),
                          rated_independent_scenes=len({row["scene_id"] for row in rows
                                                       if row["run_id"] in clip_scores}),
                          uncertain_ratings=sum(v["perceived_tone"] == "uncertain" for _, v in votes)),
            equal_clip_means={field: math.fsum(s[field] for s in scored) / len(scored) if scored else None
                              for field in ("tone_accuracy", *RATING_FIELDS[3:])},
            confusion_rating_counts=confusion,
            usage=dict(calls=dict(total=sum(known_calls) if len(known_calls) == len(rows) else None,
                                  known_subtotal=sum(known_calls), unknown_runs=len(rows) - len(known_calls)),
                       **{field: _paired_total(rows, field) for field in
                          ("input_tokens", "output_tokens", "estimated_cost_usd", "provider_cost_usd", "elapsed_s")}))

    blocks = defaultdict(dict)
    for row in records:
        blocks[row["block_id"]][row["condition"]] = row
    candidate = {block_id: conditions for block_id, conditions in blocks.items()
                 if all(c in conditions for c in ("generic_review", "moodcut"))}
    common = {block_id: conditions for block_id, conditions in candidate.items()
              if all(conditions[c]["run_id"] in clip_scores for c in ("generic_review", "moodcut"))}
    fields = ("tone_accuracy", *RATING_FIELDS[3:])
    differences = {field: math.fsum(
        clip_scores[c["moodcut"]["run_id"]][field] - clip_scores[c["generic_review"]["run_id"]][field]
        for c in common.values()) / len(common) if common else None for field in fields}
    return dict(schema_version="1.0", source_kind=records[0].get("source_kind", "unspecified") if records else None,
                usage_scope="condition_run_records_only", planning_costs_included=False,
                overall=aggregate(records),
                by_condition={condition: aggregate([r for r in records if r["condition"] == condition])
                              for condition in PAIRED_CONDITIONS},
                common_moodcut_generic=dict(planned_paired_blocks=len(candidate),
                    all_planned_blocks=len(blocks), common_evaluable_blocks=len(common),
                    block_ids=sorted(common),
                    common_coverage=len(common) / len(candidate) if candidate else None,
                    common_coverage_of_all_blocks=len(common) / len(blocks) if blocks else None,
                    blocks_missing_comparator=len(blocks) - len(candidate),
                    mean_moodcut_minus_generic=differences),
                interpretation=dict(weighting="equal rated clip means; common contrasts equal block means",
                    uncertain="counted as a tone-recognition miss",
                    coverage="Human scores describe rendered and rated clips only; failures remain in coverage and usage.",
                    common_subset="Paired differences describe jointly evaluable blocks, not unconditional improvement.",
                    validity="Rendering status and model verification do not establish emotion accuracy or semantic fidelity.",
                    confounds="Human allocation, missing ratings, reused development stories and static-image limitations require disclosure."))


if __name__ == "__main__":
    import argparse
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "batch":
        batch = argparse.ArgumentParser(description="Batch VBench imaging_quality evaluation on CPU")
        batch.add_argument("--manifest", required=True)
        batch.add_argument("--video-root", required=True)
        batch.add_argument("--upstream", required=True)
        batch.add_argument("--cache", required=True)
        batch.add_argument("--output", required=True)
        batch.add_argument("--resume", action="store_true")
        batch.add_argument("--timeout", type=float, default=300)
        args = batch.parse_args(sys.argv[2:])
        try:
            summary = run_imaging_quality_batch(
                json.loads(Path(args.manifest).read_text(encoding="utf-8-sig")),
                video_root=args.video_root, upstream_dir=args.upstream, cache_dir=args.cache,
                output_dir=args.output, resume=args.resume, timeout_s=args.timeout)
            print(json.dumps(summary, indent=2))
            raise SystemExit(2 if any(r["failed"] or r["missing"] for r in summary) else 0)
        except (ValueError, OSError) as exc:
            batch.exit(1, f"Batch failed: {exc}\n")
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
