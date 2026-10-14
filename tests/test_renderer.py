import hashlib
import json
from pathlib import Path

from PIL import Image

from moodcut.renderer import HEIGHT, WIDTH, render_plan


def test_render_plan_outputs_frames_contact_sheet_and_timeline(tmp_path):
    project_root, manifest = _make_project(tmp_path)
    plan = _plan()
    out_dir = project_root / "runs" / "render"

    result = render_plan(
        plan,
        manifest,
        project_root=str(project_root),
        out_dir=str(out_dir),
        font_path=_font_path(),
    )

    assert result["status"] == "rendered"
    assert Path(result["video_path"]).is_file()
    assert result["duration_s"] == 60.0

    frame_paths = sorted((out_dir / "frames").glob("shot_*.png"))
    assert len(frame_paths) == 3
    for path in frame_paths:
        with Image.open(path) as image:
            assert image.size == (WIDTH, HEIGHT)

    with Image.open(result["contact_sheet_path"]) as image:
        assert image.size[0] > 0
        assert image.size[1] > 0

    timeline = json.loads(Path(result["timeline_path"]).read_text(encoding="utf-8"))
    assert timeline["fps"] == 24
    assert timeline["shots"][0]["start_s"] == 0.0
    assert timeline["shots"][0]["end_s"] == 20.0
    assert timeline["shots"][2]["start_s"] == 40.0
    assert timeline["shots"][2]["end_s"] == 60.0
    assert timeline["shots"][1]["subtitles"][0]["character_id"] == "b"


def test_render_plan_accepts_shared_fixture_plan(tmp_path):
    project_root = Path(__file__).resolve().parents[1]
    plan = json.loads((project_root / "tests/fixtures/plan.json").read_text())
    manifest = json.loads((project_root / "tests/fixtures/assets.json").read_text())

    result = render_plan(
        plan,
        manifest,
        project_root=str(project_root),
        out_dir=str(tmp_path / "shared-render"),
        font_path=_font_path(),
    )

    assert result["status"] == "rendered"
    assert result["duration_s"] == 60.0
    timeline = json.loads(Path(result["timeline_path"]).read_text(encoding="utf-8"))
    assert [shot["shot_id"] for shot in timeline["shots"]] == ["s1", "s2", "s3"]


def test_center_close_crop_changes_rendered_frame(tmp_path):
    project_root, manifest = _make_project(tmp_path)
    full_plan = _plan()
    close_plan = _plan()
    close_plan["shots"][0]["visuals"][0]["crop"] = "center_close"

    full_result = render_plan(
        full_plan,
        manifest,
        project_root=str(project_root),
        out_dir=str(project_root / "runs" / "full"),
        font_path=_font_path(),
    )
    close_result = render_plan(
        close_plan,
        manifest,
        project_root=str(project_root),
        out_dir=str(project_root / "runs" / "close"),
        font_path=_font_path(),
    )

    assert full_result["status"] == "rendered"
    assert close_result["status"] == "rendered"
    full_frame = next((project_root / "runs" / "full" / "frames").glob("shot_01_*.png"))
    close_frame = next((project_root / "runs" / "close" / "frames").glob("shot_01_*.png"))
    assert full_frame.read_bytes() != close_frame.read_bytes()


def test_render_plan_rejects_crop_not_allowed_by_manifest(tmp_path):
    project_root, manifest = _make_project(tmp_path)
    manifest["assets"][0]["allowed_crops"] = ["full"]
    plan = _plan()
    plan["shots"][0]["visuals"][0]["crop"] = "center_close"

    result = render_plan(
        plan,
        manifest,
        project_root=str(project_root),
        out_dir=str(project_root / "runs" / "bad-crop"),
        font_path=_font_path(),
    )

    assert result["status"] == "render_failed"
    assert "not allowed" in result["errors"][0]


def test_render_plan_rejects_asset_hash_mismatch(tmp_path):
    project_root, manifest = _make_project(tmp_path)
    manifest["assets"][0]["sha256"] = "0" * 64

    result = render_plan(
        _plan(),
        manifest,
        project_root=str(project_root),
        out_dir=str(project_root / "runs" / "bad-hash"),
        font_path=_font_path(),
    )

    assert result["status"] == "render_failed"
    assert "sha256 mismatch" in result["errors"][0]


def test_render_plan_reports_missing_font(tmp_path):
    project_root, manifest = _make_project(tmp_path)

    result = render_plan(
        _plan(),
        manifest,
        project_root=str(project_root),
        out_dir=str(project_root / "runs" / "missing-font"),
        font_path=str(project_root / "missing.ttf"),
    )

    assert result["status"] == "render_failed"
    assert "font_path does not exist" in result["errors"][0]


def test_render_plan_reports_subtitle_overflow(tmp_path):
    project_root, manifest = _make_project(tmp_path)
    plan = _plan()
    plan["shots"][0]["dialogue"][0]["text"] = "这是一句非常长的字幕。" * 120

    result = render_plan(
        plan,
        manifest,
        project_root=str(project_root),
        out_dir=str(project_root / "runs" / "overflow"),
        font_path=_font_path(),
    )

    assert result["status"] == "render_failed"
    assert "subtitles overflow" in result["errors"][0]


def _make_project(tmp_path):
    project_root = tmp_path / "project"
    image_dir = project_root / "assets"
    image_dir.mkdir(parents=True)
    a_path = image_dir / "a.png"
    b_path = image_dir / "b.png"
    _write_gradient(a_path, left=(210, 48, 64), right=(38, 112, 218))
    _write_gradient(b_path, left=(42, 157, 143), right=(232, 174, 52))
    manifest = {
        "schema_version": "1.0",
        "assets": [
            {
                "asset_id": "dev_a",
                "character_id": "a",
                "path": "assets/a.png",
                "width": 320,
                "height": 240,
                "sha256": _sha256(a_path),
                "source_url": None,
                "revision": None,
                "rights_note": "test asset",
                "allowed_crops": ["full", "center_close"],
            },
            {
                "asset_id": "dev_b",
                "character_id": "b",
                "path": "assets/b.png",
                "width": 320,
                "height": 240,
                "sha256": _sha256(b_path),
                "source_url": None,
                "revision": None,
                "rights_note": "test asset",
                "allowed_crops": ["full", "center_close"],
            },
        ],
    }
    return project_root, manifest


def _plan():
    return {
        "schema_version": "1.0",
        "scene_id": "dev_letter_01",
        "tone": "suspicious",
        "shots": [
            {
                "shot_id": "s1",
                "beat_ids": ["b1"],
                "duration_s": 20,
                "visuals": [{"asset_id": "dev_a", "crop": "full"}],
                "dialogue": [{"character_id": "a", "text": "这封信给你。"}],
                "narration": "A将信交给B。",
            },
            {
                "shot_id": "s2",
                "beat_ids": ["b2"],
                "duration_s": 20,
                "visuals": [{"asset_id": "dev_b", "crop": "center_close"}],
                "dialogue": [{"character_id": "b", "text": "你从哪里拿到的？"}],
                "narration": "B读信，随后把信收起来。",
            },
            {
                "shot_id": "s3",
                "beat_ids": ["b3"],
                "duration_s": 20,
                "visuals": [
                    {"asset_id": "dev_a", "crop": "full"},
                    {"asset_id": "dev_b", "crop": "full"},
                ],
                "dialogue": [],
                "narration": "两人离开。",
            },
        ],
    }


def _write_gradient(path, *, left, right):
    image = Image.new("RGB", (320, 240))
    pixels = image.load()
    for x in range(320):
        weight = x / 319
        color = tuple(int(left[i] * (1 - weight) + right[i] * weight) for i in range(3))
        for y in range(240):
            pixels[x, y] = color
    image.save(path)


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
