"""Offline adapter tests. Worker probabilities are synthetic software fixtures."""
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from moodcut import vemoclap as v


PROBABILITIES = dict(zip(v.LABELS, (0.03, 0.07, 0.1, 0.6, 0.15, 0.05)))


@pytest.mark.parametrize("bad", [
    {}, {**PROBABILITIES, "affectionate": 0}, {**PROBABILITIES, "anger": True},
    {**PROBABILITIES, "anger": -0.1}, {**PROBABILITIES, "anger": 1.1},
    {**PROBABILITIES, "anger": math.nan}, {**PROBABILITIES, "anger": math.inf},
    {**PROBABILITIES, "anger": "0.03"}, {**PROBABILITIES, "anger": 0.04},
])
def test_reject_invalid_probability_distribution(bad):
    with pytest.raises(ValueError):
        v.validate_probabilities(bad)


def test_preserve_native_labels_and_precision():
    p = {**PROBABILITIES, "anger": 0.030000123, "disgust": 0.069999877}
    assert v.validate_probabilities(p) == p
    assert tuple(v.validate_probabilities(p)) == v.LABELS


@pytest.fixture
def case(tmp_path, monkeypatch):
    upstream = tmp_path / "upstream with spaces"
    upstream.mkdir()
    for name in ("video_emotion_classifier.py", "src/models_.py", "src/utils.py", "LICENSE.md",
                 *v.LOCAL_WEIGHTS):
        path = upstream / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("synthetic test fixture\n", encoding="utf-8")
    def git(*args):
        return subprocess.check_output(["git", "-C", str(upstream), *args], text=True).strip()
    git("init", "--quiet")
    git("add", ".")
    git("-c", "user.name=Software Fixture", "-c", "user.email=fixture@example.invalid",
        "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "synthetic fixture")
    monkeypatch.setattr(v, "REVISION", git("rev-parse", "HEAD"))
    video = tmp_path / "上游 film.mp4"
    video.write_bytes(b"software fixture; mocked ffprobe, not playable media")
    real_run = subprocess.run
    worker = tmp_path / "synthetic_worker.py"
    worker.write_text(
        "import json,os,sys\n"
        "assert os.environ['CUDA_VISIBLE_DEVICES'] == ''\n"
        "assert os.environ['HF_HUB_OFFLINE'] == '1'\n"
        "assert 'EXAMPLE_API_KEY' not in os.environ\n"
        "result=" + repr(dict(probabilities=PROBABILITIES, missing_features=[], packages={})) + "\n"
        "with open(sys.argv[sys.argv.index('--output')+1], 'x', encoding='utf-8') as f:\n"
        "    json.dump(result,f)\n", encoding="utf-8")
    monkeypatch.setenv("EXAMPLE_API_KEY", "synthetic-not-a-secret")
    def run(command, **kwargs):
        if command[0] == "ffprobe":
            return subprocess.CompletedProcess(command, 0, json.dumps({
                "streams": [{"codec_type": "video"}, {"codec_type": "audio"}],
                "format": {"duration": "5.26"}}))
        if len(command) > 1 and command[1].endswith("vemoclap_worker.py"):
            command = [command[0], str(worker), *command[2:]]
        return real_run(command, **kwargs)
    monkeypatch.setattr(v.subprocess, "run", run)
    monkeypatch.setattr(v, "check_environment", lambda *_: {
        "basic_checks_passed": True, "feature_model_caches_verified": False})
    return dict(video_path=video, upstream_dir=upstream, output_dir=tmp_path / "result",
                source_kind="synthetic"), worker, git


def test_default_check_has_no_inference_or_scores(case):
    args, worker, _ = case
    worker.write_text("raise AssertionError('must not run')", encoding="utf-8")
    result = v.evaluate_video(**args)
    assert result["status"] == "checked_not_run"
    assert result["probabilities"] is None
    assert not result["inference_attempted"]
    assert not (args["output_dir"] / "worker-result.json").exists()


def test_software_worker_end_to_end_preserves_input(case):
    args, _, git = case
    before = args["video_path"].read_bytes()
    result = v.evaluate_video(**args, run=True)
    assert result["status"] == "success"
    assert result["probabilities"] == PROBABILITIES
    assert result["top_emotion"] == "joy"
    assert result["human_ratings"] == 0 and not result["formal_inclusion_approved"]
    assert args["video_path"].read_bytes() == before
    assert git("status", "--porcelain") == ""
    assert json.loads((args["output_dir"] / "result.json").read_text("utf-8")) == result
    with pytest.raises(FileExistsError):
        v.evaluate_video(**args, run=True)


def test_relative_interpreter_resolved_before_worker_cwd(case):
    args, _, _ = case
    try:
        python = os.path.relpath(sys.executable)
    except ValueError:
        pytest.skip("Interpreter and checkout on different Windows drives")
    result = v.evaluate_video(**args, python_executable=python, run=True)
    assert result["status"] == "success"


@pytest.mark.parametrize("duration", ["0", "3", "nan"])
def test_invalid_duration_does_not_reach_worker(case, monkeypatch, duration):
    args, _, _ = case
    real_run = v.subprocess.run
    def run(command, **kwargs):
        if command[0] == "ffprobe":
            return subprocess.CompletedProcess(command, 0, json.dumps({
                "streams": [{"codec_type": "video"}, {"codec_type": "audio"}],
                "format": {"duration": duration}}))
        return real_run(command, **kwargs)
    monkeypatch.setattr(v.subprocess, "run", run)
    result = v.evaluate_video(**args, run=True)
    assert result["status"] == "failed" and not result["inference_attempted"]


def test_cli_reports_blocked_nonzero(case, monkeypatch):
    args, _, _ = case
    monkeypatch.setattr(v, "check_environment", lambda *_: {"basic_checks_passed": False})
    code = v.main(["--video", str(args["video_path"]), "--upstream", str(args["upstream_dir"]),
                   "--output", str(args["output_dir"]), "--source-kind", "synthetic", "--check"])
    assert code == 1
    assert json.loads((args["output_dir"] / "result.json").read_text("utf-8"))["probabilities"] is None


def test_missing_dependencies_block_without_fake_probabilities(case, monkeypatch):
    args, worker, _ = case
    monkeypatch.setattr(v, "check_environment", lambda *_: {
        "basic_checks_passed": False, "missing_modules": ["torch"]})
    worker.write_text("raise AssertionError('must not run')", encoding="utf-8")
    result = v.evaluate_video(**args, run=True)
    assert result["status"] == "blocked" and result["probabilities"] is None
    assert not result["inference_attempted"]


@pytest.mark.parametrize("failure", ["crash", "timeout", "bad_json", "bad_distribution", "changed_video"])
def test_worker_failures_are_retained(case, failure):
    args, worker, _ = case
    if failure == "crash":
        worker.write_text("raise RuntimeError('synthetic failure')", encoding="utf-8")
    elif failure == "timeout":
        worker.write_text("import time; time.sleep(10)", encoding="utf-8")
    elif failure == "changed_video":
        with worker.open("a", encoding="utf-8") as handle:
            handle.write("\nopen(sys.argv[sys.argv.index('--video')+1], 'wb').write(b'changed')\n")
    else:
        text = worker.read_text("utf-8")
        text = text.replace("json.dump(result,f)",
                            "f.write('bad json')" if failure == "bad_json" else
                            "json.dump({'probabilities': {'joy': 1}}, f)")
        worker.write_text(text, encoding="utf-8")
    result = v.evaluate_video(**args, run=True, timeout_s=0.2 if failure == "timeout" else 30)
    assert result["status"] == "failed" and result["probabilities"] is None
    assert result["inference_attempted"] and result["error"]


def test_dirty_or_wrong_upstream_rejected(case, monkeypatch):
    args, _, _ = case
    (args["upstream_dir"] / "src/models_.py").write_text("modified", encoding="utf-8")
    result = v.evaluate_video(**args, run=True)
    assert result["status"] == "failed" and not result["inference_attempted"]
    monkeypatch.setattr(v, "REVISION", "0" * 40)
    with pytest.raises(ValueError, match="revision"):
        v.inspect_source(args["upstream_dir"])


def test_output_cannot_modify_upstream(case):
    args, _, _ = case
    args["output_dir"] = args["upstream_dir"] / "results"
    with pytest.raises(ValueError, match="outside"):
        v.evaluate_video(**args)


def test_offline_network_guard():
    from moodcut.vemoclap_worker import _deny_network
    for event in ("socket.connect", "socket.getaddrinfo", "socket.sendto"):
        with pytest.raises(RuntimeError, match="offline"):
            _deny_network(event, ())


def test_real_ffmpeg_video_preflight(tmp_path):
    if not all(shutil.which(tool) for tool in ("ffmpeg", "ffprobe")):
        pytest.skip("FFmpeg required for real software-media preflight")
    video = tmp_path / "software clip.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=s=64x64:r=4:d=4",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=4", "-c:v", "libx264",
                    "-c:a", "aac", "-shortest", str(video)], check=True, capture_output=True)
    metadata = v.inspect_video(video)
    assert metadata["duration_s"] == 4 and metadata["sha256"] == v.file_sha256(video)
    silent = tmp_path / "silent.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-an", "-c:v", "copy", str(silent)],
                   check=True, capture_output=True)
    with pytest.raises(ValueError, match="audio stream"):
        v.inspect_video(silent)


def test_environment_check_does_not_import_models(tmp_path):
    result = v.check_environment(tmp_path, sys.executable)
    assert not result["basic_checks_passed"]
    assert result["missing_local_weights"] == list(v.LOCAL_WEIGHTS)
    assert not result["feature_model_caches_verified"]
