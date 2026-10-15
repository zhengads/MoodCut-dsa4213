"""Offline reference-to-video preparation and local synthetic media checks."""
from copy import deepcopy
from pathlib import Path
import json
import shutil
import subprocess

import pytest

from moodcut.video_generation import build_video_bundle, assemble_generated_clips
from moodcut.pipeline import json_hash

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def inputs():
    def read(path):
        return json.loads((ROOT / path).read_text(encoding="utf-8-sig"))
    scene = read("tests/fixtures/scene.json")
    initial = read("tests/fixtures/plan.json")
    revised = deepcopy(initial)
    revised["shots"][0]["dialogue"][0]["text"] = "这封信有些奇怪。"
    revised["shots"][2]["narration"] = "A new, excluded event."
    manifest = read("tests/fixtures/assets.json")
    for item in manifest["assets"]:
        item["source_url"] = "https://example.com/" + item["asset_id"] + ".png"
    config = read("configs/video.json")
    config["scene_id"] = scene["scene_id"]
    config["characters"][0]["asset_id"] = "dev_a"
    config["characters"][1]["asset_id"] = "dev_b"
    return scene, initial, revised, manifest, config


@pytest.fixture
def bundle(inputs):
    return build_video_bundle(*inputs, project_root=str(ROOT))


def test_requests_use_references_and_dialogue_only(bundle):
    before, after = bundle["conditions"]
    for original, edited in zip(before["jobs"], after["jobs"]):
        assert "frame_images" not in original["request"]
        assert len(original["request"]["input_references"]) == 2
        assert original["request"]["generate_audio"] is True
        assert original["request"]["seed"] == edited["request"]["seed"]
        assert original["direction"] == edited["direction"]
    assert bundle["duration_s_per_condition"] == 18
    assert bundle["estimated_cost_usd"] == "3.60"
    assert len(bundle["dialogue_changes"]) == 1
    assert bundle["ignored_non_dialogue_changes"] == ["shots.s3.narration"]
    assert "excluded event" not in str(after["jobs"])


def test_only_dialogue_varies_between_request_prompts(bundle):
    before, after = bundle["conditions"]
    for index in (1, 2):
        assert before["jobs"][index]["request"] == after["jobs"][index]["request"]
    first, second = [c["jobs"][0]["request"].copy() for c in (before, after)]
    assert first.pop("prompt") != second.pop("prompt")
    assert first == second


def test_inputs_unchanged(inputs):
    saved = deepcopy(inputs)
    build_video_bundle(*inputs, project_root=str(ROOT))
    assert saved == inputs


def load_command():
    import importlib.util
    spec = importlib.util.spec_from_file_location("moodcut_generate_video_command", ROOT / "scripts/generate_video.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare_command_root(inputs, tmp_path):
    scene, initial, revised, manifest, config = inputs
    shutil.copytree(ROOT / "tests/fixtures", tmp_path / "tests/fixtures")
    run = tmp_path / "runs/source"
    (run / "baseline").mkdir(parents=True)
    (run / "moodcut").mkdir()
    (tmp_path / "configs").mkdir()
    records = {"scene.json": scene, "assets.json": manifest, "baseline/initial.json": initial,
               "moodcut/final.json": revised,
               "baseline/run.json": {"initial_plan_sha256": json_hash(initial)},
               "moodcut/run.json": {"initial_plan_sha256": json_hash(initial), "final_plan_sha256": json_hash(revised),
                                    "run_status": "completed", "review_status": "applied"}}
    for path, data in records.items():
        (run / path).write_text(json.dumps(data), encoding="utf-8")
    (tmp_path / "configs/video.json").write_text(json.dumps(config), encoding="utf-8")
    return run


def test_command_defaults_to_offline_without_key(inputs, tmp_path, monkeypatch):
    command = load_command()
    prepare_command_root(inputs, tmp_path)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    def reject_network():
        raise AssertionError("Offline preparation must not fetch a catalogue or generate")
    monkeypatch.setattr(command, "fetch_video_models", reject_network)
    assert command.main(["--project-root", str(tmp_path), "--run", "runs/source", "--output", "runs/preview"]) == 0
    assert (tmp_path / "runs/preview/bundle.json").is_file()
    assert "离线请求预览" in (tmp_path / "runs/preview/preview.html").read_text(encoding="utf-8")
    assert not list((tmp_path / "runs/preview").rglob("*.mp4"))
    with pytest.raises(FileExistsError):
        command.main(["--project-root", str(tmp_path), "--run", "runs/source", "--output", "runs/preview"])


def test_command_rejects_old_budget_before_network(inputs, tmp_path, monkeypatch):
    command = load_command()
    prepare_command_root(inputs, tmp_path)
    monkeypatch.setattr(command, "fetch_video_models", lambda: pytest.fail("No network permitted"))
    from moodcut.client import BudgetError
    with pytest.raises(BudgetError):
        command.main(["--project-root", str(tmp_path), "--run", "runs/source", "--output", "runs/paid",
                      "--allow-paid", "--max-cost-usd", "0.10"])
    assert not (tmp_path / "runs/paid").exists()


def test_command_refuses_tampered_source(inputs, tmp_path):
    command = load_command()
    run = prepare_command_root(inputs, tmp_path)
    candidate = json.loads((run / "moodcut/final.json").read_text())
    candidate["shots"][0]["dialogue"][0]["text"] = "tampered"
    (run / "moodcut/final.json").write_text(json.dumps(candidate), encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        command.load_source(run)


def test_complete_command_with_synthetic_generated_media(inputs, tmp_path, monkeypatch):
    """Transport double + moving/sine fixture; not a real model demonstration."""
    from decimal import Decimal
    command = load_command()
    prepare_command_root(inputs, tmp_path)
    source = tmp_path / "synthetic-generated-fixture.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i",
                    "testsrc2=size=160x90:rate=24:duration=6", "-f", "lavfi", "-i",
                    "sine=frequency=440:duration=6", "-c:v", "libx264", "-c:a", "aac",
                    "-shortest", str(source)], check=True, capture_output=True)
    class SyntheticVideoTransport:
        credentials_available = True
        post_attempts = 0
        spent_usd = "0"
        def __init__(self, *args, **kwargs):
            pass
        def generate(self, request, *, out_dir):
            directory = Path(out_dir)
            directory.mkdir(parents=True)
            target = directory / "generated.mp4"
            shutil.copyfile(source, target)
            self.post_attempts += 1
            self.spent_usd = str(Decimal(self.spent_usd) + Decimal("0.60"))
            return {"status": "downloaded", "provider_cost_usd": "0.60", "video_path": str(target)}
    model = {"id": "alibaba/wan-2.7", "supported_resolutions": ["720p"],
             "supported_aspect_ratios": ["16:9"], "supported_durations": [6],
             "generate_audio": True, "seed": True, "pricing_skus": {"duration_seconds": "0.1"}}
    monkeypatch.setattr(command, "fetch_video_models", lambda: [model])
    monkeypatch.setattr(command, "OpenRouterVideoClient", SyntheticVideoTransport)
    assert command.main(["--project-root", str(tmp_path), "--run", "runs/source", "--output", "runs/generated",
                         "--allow-paid", "--max-cost-usd", "4.00"]) == 0
    result = json.loads((tmp_path / "runs/generated/generation.json").read_text())
    assert result["generation_posts"] == 4  # One dialogue change; two identical requests are reused.
    assert result["provider_cost_usd"] == "2.40"
    assert result["status"] == "assembled_requires_manual_inspection"
    assert sum(j.get("reused_identical_request", False) for c in result["conditions"] for j in c["jobs"]) == 2
    for condition in result["conditions"]:
        assert condition["media"]["has_audio"] is True
        assert abs(condition["media"]["duration_s"] - 18) < .5
    assert (tmp_path / "runs/generated/comparison.html").is_file()


@pytest.mark.parametrize("mutation", ["reorder", "missing", "speaker", "too_long", "url", "duration", "scene", "asset"])
def test_invalid_bundle_is_rejected(inputs, mutation):
    scene, initial, revised, manifest, config = inputs
    if mutation == "reorder":
        revised["shots"].reverse()
    elif mutation == "missing":
        revised["shots"].pop()
    elif mutation == "speaker":
        revised["shots"][0]["dialogue"][0]["character_id"] = "unknown"
    elif mutation == "too_long":
        revised["shots"][0]["dialogue"][0]["text"] = "长" * 500
    elif mutation == "url":
        manifest["assets"][0]["source_url"] = "file:///private.png"
    elif mutation == "duration":
        config["shots"][0]["duration_s"] = 25
    elif mutation == "scene":
        config["scene_id"] = "unrelated"
    elif mutation == "asset":
        config["characters"][0]["asset_id"] = "missing"
    with pytest.raises(ValueError):
        build_video_bundle(scene, initial, revised, manifest, config, project_root=str(ROOT))


def test_local_synthetic_video_and_audio_are_preserved(tmp_path):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.fail("FFmpeg/ffprobe are required for generated-media integration tests")
    clips = []
    for index in range(2):
        target = tmp_path / f"synthetic-{index}.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i",
                        "testsrc2=size=320x180:rate=24:duration=1", "-f", "lavfi", "-i",
                        f"sine=frequency={440+index*110}:duration=1", "-c:v", "libx264",
                        "-c:a", "aac", "-shortest", str(target)], check=True, capture_output=True)
        clips.append(str(target))
    result = assemble_generated_clips(clips, durations=[1, 1], out_path=str(tmp_path / "film.mp4"))
    assert result["has_audio"] is True
    assert abs(result["duration_s"] - 2) < .5
    assert result["width"] == 1280
    with pytest.raises(FileExistsError):
        assemble_generated_clips(clips, durations=[1, 1], out_path=str(tmp_path / "film.mp4"))
    silent = tmp_path / "silent.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-i", clips[0], "-an", "-c:v", "copy", str(silent)],
                   check=True, capture_output=True)
    with pytest.raises(ValueError, match="audio"):
        assemble_generated_clips([str(silent)], durations=[1], out_path=str(tmp_path / "reject.mp4"))
