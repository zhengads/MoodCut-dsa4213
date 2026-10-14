import json
import shutil
import subprocess
from pathlib import Path

from PIL import Image

from moodcut.renderer import render_plan


def test_render_plan_writes_verified_mp4(tmp_path):
    project_root = Path(__file__).resolve().parents[1]
    plan = json.loads((project_root / "tests/fixtures/plan.json").read_text())
    manifest = json.loads((project_root / "tests/fixtures/assets.json").read_text())

    result = render_plan(
        plan,
        manifest,
        project_root=str(project_root),
        out_dir=str(tmp_path / "render"),
        font_path=_font_path(),
    )

    assert result["status"] == "rendered"
    assert Path(result["video_path"]).is_file()
    timeline = json.loads(Path(result["timeline_path"]).read_text(encoding="utf-8"))
    assert timeline["ffprobe"]["width"] == 1280
    assert timeline["ffprobe"]["height"] == 720
    assert timeline["ffprobe"]["fps"] == 24.0
    assert abs(timeline["ffprobe"]["duration_s"] - 60.0) <= (1 / 24) + 0.1


def test_crop_dialogue_and_duration_changes_are_visible(tmp_path):
    project_root = Path(__file__).resolve().parents[1]
    plan = json.loads((project_root / "tests/fixtures/plan.json").read_text())
    manifest = json.loads((project_root / "tests/fixtures/assets.json").read_text())
    changed_plan = json.loads(json.dumps(plan))
    changed_plan["shots"][1]["duration_s"] = 25
    changed_plan["shots"][1]["visuals"][0]["crop"] = "center_close"
    changed_plan["shots"][1]["dialogue"][0]["text"] = "Where did you get this letter?"

    base_result = render_plan(
        plan,
        manifest,
        project_root=str(project_root),
        out_dir=str(tmp_path / "base"),
        font_path=_font_path(),
    )
    changed_result = render_plan(
        changed_plan,
        manifest,
        project_root=str(project_root),
        out_dir=str(tmp_path / "changed"),
        font_path=_font_path(),
    )

    assert base_result["status"] == "rendered"
    assert changed_result["status"] == "rendered"
    base_frame = tmp_path / "base" / "frames" / "shot_02_s2.png"
    changed_frame = tmp_path / "changed" / "frames" / "shot_02_s2.png"
    assert _mean_abs_pixel_difference(base_frame, changed_frame) > 0.5

    base_timeline = json.loads(Path(base_result["timeline_path"]).read_text())
    changed_timeline = json.loads(Path(changed_result["timeline_path"]).read_text())
    assert base_timeline["shots"][2]["start_s"] == 40.0
    assert changed_timeline["shots"][2]["start_s"] == 45.0
    assert changed_result["duration_s"] == 65.0


def test_render_plan_refuses_non_empty_output_dir(tmp_path):
    project_root = Path(__file__).resolve().parents[1]
    plan = json.loads((project_root / "tests/fixtures/plan.json").read_text())
    manifest = json.loads((project_root / "tests/fixtures/assets.json").read_text())
    out_dir = tmp_path / "render"
    out_dir.mkdir()
    (out_dir / "existing.txt").write_text("keep me", encoding="utf-8")

    result = render_plan(
        plan,
        manifest,
        project_root=str(project_root),
        out_dir=str(out_dir),
        font_path=_font_path(),
    )

    assert result["status"] == "render_failed"
    assert "out_dir is not empty" in result["errors"][0]
    assert (out_dir / "existing.txt").read_text(encoding="utf-8") == "keep me"


def test_ffprobe_reports_mp4_has_no_audio_stream(tmp_path):
    project_root = Path(__file__).resolve().parents[1]
    plan = json.loads((project_root / "tests/fixtures/plan.json").read_text())
    manifest = json.loads((project_root / "tests/fixtures/assets.json").read_text())

    result = render_plan(
        plan,
        manifest,
        project_root=str(project_root),
        out_dir=str(tmp_path / "render"),
        font_path=_font_path(),
    )

    assert result["status"] == "rendered"
    command = [
        shutil.which("ffprobe") or "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a",
        "-show_entries",
        "stream=index",
        "-of",
        "json",
        result["video_path"],
    ]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    assert json.loads(completed.stdout)["streams"] == []


def _mean_abs_pixel_difference(first_path, second_path):
    with Image.open(first_path) as first, Image.open(second_path) as second:
        first_bytes = first.convert("RGB").tobytes()
        second_bytes = second.convert("RGB").tobytes()
        total = sum(
            abs(first_value - second_value)
            for first_value, second_value in zip(first_bytes, second_bytes, strict=True)
        )
        return total / len(first_bytes)


def _font_path():
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]
    for candidate in candidates:
        if Path(candidate).is_file():
            return candidate
    raise AssertionError("test needs a local TrueType/OpenType font")
