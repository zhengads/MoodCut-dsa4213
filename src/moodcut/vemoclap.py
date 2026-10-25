"""Explicit local VEMOCLAP adapter; independent of human ratings and VBench.

姓名: FANXUYANG
日期: 2026-10-25
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

REVISION = "312f80204f001d611564a2c8405999080829cae3"
SOURCE_URL = "https://github.com/serkansulun/video-emotion"
LABELS = ("anger", "disgust", "fear", "joy", "sadness", "surprise")
MODULES = ("torch", "torchaudio", "torchvision", "transformers", "clip", "surya",
           "numpy", "scipy", "ffmpeg", "gdown", "yt_dlp", "matplotlib",
           "ipywidgets", "IPython", "requests", "cv2", "pandas", "yaml", "tqdm",
           "PIL", "thop", "seaborn", "accelerate")
LOCAL_WEIGHTS = ("weights/classifier/model.pt", "weights/classifier/model_config.pt",
                 "stats.pt", "weights/yolov5m-face.pt",
                 "src/beats/pretrained_models_labels/BEATs_iter3_plus_AS2M_finetuned_on_AS2M_cpt2.pt")


def file_sha256(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def validate_probabilities(value):
    """Keep full precision and exact native labels; never repair/renormalize."""
    if not isinstance(value, dict) or set(value) != set(LABELS):
        raise ValueError("Expected exactly the six VEMOCLAP labels")
    if any(type(p) not in (int, float) or not math.isfinite(p) or not 0 <= p <= 1
           for p in value.values()):
        raise ValueError("Probabilities must be finite numbers in [0, 1]")
    if not math.isclose(math.fsum(value.values()), 1.0, rel_tol=0, abs_tol=1e-5):
        raise ValueError("Probabilities must sum to 1; rounded percentages are not accepted")
    return {label: value[label] for label in LABELS}


def _json_write(path, value):
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")


def inspect_source(upstream):
    """Require the reviewed checkout and preserve its tracked files."""
    command = ["git", "-C", str(upstream)]
    revision = subprocess.check_output(command + ["rev-parse", "HEAD"], text=True).strip()
    if revision != REVISION:
        raise ValueError("Unexpected VEMOCLAP revision; use the documented pinned checkout")
    dirty = subprocess.check_output(command + ["diff", "HEAD", "--name-only"], text=True)
    if dirty.strip():
        raise ValueError("VEMOCLAP tracked files differ from the pinned version")
    files = ("video_emotion_classifier.py", "src/models_.py", "src/utils.py", "LICENSE.md",
             *LOCAL_WEIGHTS[:3])
    return {"repository": SOURCE_URL, "revision": revision,
            "files_sha256": {name: file_sha256(upstream / name) for name in files}}


def inspect_video(video):
    if not video.is_file() or not video.stat().st_size:
        raise ValueError("Input must be an existing nonempty local video file")
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video)],
        capture_output=True, text=True, timeout=30, check=True)
    metadata = json.loads(probe.stdout)
    streams = metadata.get("streams", [])
    if not any(s.get("codec_type") == "video" for s in streams):
        raise ValueError("No video stream")
    if not any(s.get("codec_type") == "audio" for s in streams):
        raise ValueError("This multimodal adapter requires an audio stream")
    duration = float(metadata["format"]["duration"])
    if not math.isfinite(duration) or duration <= 3:
        raise ValueError("This adapter requires duration > 3 seconds for BEATs audio chunks")
    return {"file_name": video.name, "sha256": file_sha256(video),
            "bytes": video.stat().st_size, "duration_s": duration}


def check_environment(upstream, python):
    # No torch/upstream imports, installation, model loading or downloads.
    code = ("import importlib.util,json; names=" + repr(MODULES) + "; "
            "print(json.dumps([n for n in names if importlib.util.find_spec(n) is None]))")
    result = subprocess.run([str(python), "-c", code], capture_output=True,
                            text=True, check=True, timeout=30)
    missing_modules = json.loads(result.stdout)
    missing_weights = [name for name in LOCAL_WEIGHTS if not (upstream / name).is_file()]
    missing_tools = [name for name in ("ffmpeg", "ffprobe") if not shutil.which(name)]
    return {"missing_modules": missing_modules, "missing_local_weights": missing_weights,
            "missing_tools": missing_tools,
            "basic_checks_passed": not (missing_modules or missing_weights or missing_tools),
            "feature_model_caches_verified": False,
            "note": "Module presence is not version/import compatibility. CLIP, Hugging Face and Surya caches are checked only when loading offline."}


def evaluate_video(*, video_path, upstream_dir, output_dir, source_kind,
                   python_executable=sys.executable, run=False, timeout_s=600, cache_dir=None):
    """Check or explicitly infer one local clip in a fresh CPU-only worker.

    Does not load/alter a RunRecord, establish eligibility, or generate ratings.
    Output is a new directory; failure has null probabilities and a nonzero CLI exit.
    """
    if source_kind not in ("synthetic", "provided_local"):
        raise ValueError("Declare source_kind synthetic or provided_local")
    if not math.isfinite(timeout_s) or timeout_s <= 0:
        raise ValueError("timeout_s must be positive and finite")
    video, upstream, out = (Path(p).resolve() for p in (video_path, upstream_dir, output_dir))
    # Resolve before changing the worker cwd (important for a relative Windows venv).
    python = Path(shutil.which(str(python_executable)) or python_executable).resolve()
    if out == upstream or out.is_relative_to(upstream):
        raise ValueError("Output must be outside the upstream checkout")
    out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    report = {"schema_version": "1.0", "kind": "vemoclap_video_emotion",
              "status": "failed", "source_kind": source_kind, "device": "cpu",
              "labels": list(LABELS), "probabilities": None, "top_emotion": None,
              "inference_attempted": False, "human_ratings": 0,
              "formal_inclusion_approved": False}
    try:
        report["upstream"] = inspect_source(upstream)
        report["environment"] = check_environment(upstream, python)
        report["video"] = inspect_video(video)
        if not report["environment"]["basic_checks_passed"]:
            report.update(status="blocked", error="Missing dependencies/weights/tools; see environment")
        elif not run:
            report["status"] = "checked_not_run"
        else:
            env = os.environ.copy()
            cache = Path(cache_dir or env.get("MOODCUT_VEMOCLAP_CACHE")
                         or out.parent / "vemoclap-cache").resolve()
            for name in ("tmp", "hf", "torch", "surya", "clip", "matplotlib", "pycache",
                         "xdg", "appdata", "localappdata", "numba"):
                (cache / name).mkdir(parents=True, exist_ok=True)
            model_manifest = cache / "model-revisions.json"
            report["model_cache_manifest_sha256"] = (
                file_sha256(model_manifest) if model_manifest.is_file() else None)
            env.update(MOODCUT_VEMOCLAP_CACHE=str(cache), HF_HOME=str(cache / "hf"),
                       HF_HUB_CACHE=str(cache / "hf/hub"), TORCH_HOME=str(cache / "torch"),
                       MODEL_CACHE_DIR=str(cache / "surya"), XDG_CACHE_HOME=str(cache / "xdg"),
                       MPLCONFIGDIR=str(cache / "matplotlib"), NUMBA_CACHE_DIR=str(cache / "numba"),
                       PYTHONPYCACHEPREFIX=str(cache / "pycache"), TEMP=str(cache / "tmp"),
                       TMP=str(cache / "tmp"), APPDATA=str(cache / "appdata"),
                       LOCALAPPDATA=str(cache / "localappdata"))
            env.update(CUDA_VISIBLE_DEVICES="", TORCH_DEVICE="cpu", HF_HUB_OFFLINE="1",
                       TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1",
                       MPLBACKEND="Agg", PYTHONDONTWRITEBYTECODE="1")
            # Do not pass service credentials to the optional model process.
            for key in list(env):
                if any(word in key.upper() for word in ("API_KEY", "TOKEN", "SECRET", "PASSWORD")):
                    del env[key]
            raw_path = out / "worker-result.json"
            report["inference_attempted"] = True
            with (out / "worker.log").open("x", encoding="utf-8") as log:
                result = subprocess.run(
                    [str(python), str(Path(__file__).with_name("vemoclap_worker.py")),
                     "--upstream", str(upstream), "--video", str(video), "--output", str(raw_path)],
                    cwd=out, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=timeout_s)
            if result.returncode:
                raise RuntimeError("VEMOCLAP worker failed; inspect local worker.log")
            raw = json.loads(raw_path.read_text(encoding="utf-8"))
            probabilities = validate_probabilities(raw["probabilities"])
            if file_sha256(video) != report["video"]["sha256"]:
                raise ValueError("Input video changed during evaluation")
            if inspect_source(upstream) != report["upstream"]:
                raise ValueError("Upstream changed during evaluation")
            report.update(status="success", probabilities=probabilities,
                          top_emotion=max(probabilities, key=probabilities.get),
                          missing_features=raw["missing_features"], packages=raw["packages"])
    except (Exception, KeyboardInterrupt) as exc:
        report.update(status="failed", error=f"{type(exc).__name__}: {exc}")
    report["elapsed_s"] = round(time.monotonic() - started, 3)
    _json_write(out / "result.json", report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, help="Existing upstream film.mp4 or generated.mp4")
    parser.add_argument("--upstream", required=True, help="Pinned external video-emotion checkout")
    parser.add_argument("--output", required=True, help="New result directory")
    parser.add_argument("--source-kind", required=True, choices=("synthetic", "provided_local"))
    parser.add_argument("--python", default=sys.executable, help="Separate VEMOCLAP Python interpreter")
    parser.add_argument("--cache-dir", help="Model/cache/temp root; defaults beside output, never user home")
    parser.add_argument("--timeout", type=float, default=600, help="Worker timeout in seconds")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--run", action="store_true", help="Explicitly run local CPU inference, offline")
    modes.add_argument("--check", action="store_true", help="Preflight only (default); no model imports")
    args = parser.parse_args(argv)
    try:
        result = evaluate_video(video_path=args.video, upstream_dir=args.upstream,
                                output_dir=args.output, source_kind=args.source_kind,
                                python_executable=args.python, run=args.run, timeout_s=args.timeout,
                                cache_dir=args.cache_dir)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if result["status"] in ("success", "checked_not_run") else 1


if __name__ == "__main__":
    raise SystemExit(main())
