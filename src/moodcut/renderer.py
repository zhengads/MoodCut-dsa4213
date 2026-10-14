"""Static storyboard and MP4 rendering for MoodCut.

The renderer creates deterministic PNG animatic frames, a contact sheet,
a timeline and a silent H.264 MP4 assembled from the still frames.
"""

from __future__ import annotations

import hashlib
import json
import math
import shutil
import subprocess
from pathlib import Path
from typing import Any

try:  # pragma: no cover - exercised through render_plan's dependency check.
    from PIL import Image, ImageDraw, ImageFont, ImageOps
except ModuleNotFoundError:  # pragma: no cover
    Image = ImageDraw = ImageFont = ImageOps = None  # type: ignore[assignment]


WIDTH = 1280
HEIGHT = 720
FPS = 24
CONTAINER_TOLERANCE_S = 0.1
BACKGROUND = (34, 38, 42)
CARD_FILL = (244, 245, 246)
CARD_BORDER = (210, 214, 218)
TEXT = (244, 244, 240)
MUTED_TEXT = (196, 200, 204)
CAPTION_BOX = (23, 26, 30)


def render_plan(
    plan: dict,
    manifest: dict,
    *,
    project_root: str,
    out_dir: str,
    font_path: str,
) -> dict:
    """Render a ShotPlan as storyboard PNGs, timeline metadata and MP4."""

    try:
        if Image is None or ImageDraw is None or ImageFont is None or ImageOps is None:
            raise RuntimeError("Pillow is required for rendering PNG frames")

        root = Path(project_root).resolve()
        output_dir = Path(out_dir).resolve()
        _ensure_output_dir(output_dir)
        font = _load_font(font_path)
        small_font = _load_font(font_path, size=24)
        assets = _asset_index(manifest, root)
        shots = plan.get("shots")
        if not isinstance(shots, list) or not shots:
            raise ValueError("plan.shots must be a non-empty list")

        frame_dir = output_dir / "frames"
        frame_dir.mkdir(exist_ok=True)

        timeline_shots: list[dict[str, Any]] = []
        frame_paths: list[Path] = []
        cursor = 0.0
        for index, shot in enumerate(shots, start=1):
            frame = _render_shot(shot, assets, font, small_font)
            shot_id = _safe_id(shot.get("shot_id"), fallback=f"s{index}")
            frame_path = frame_dir / f"shot_{index:02d}_{shot_id}.png"
            frame.save(frame_path)
            frame_paths.append(frame_path)

            duration = _positive_number(shot.get("duration_s"), f"{shot_id}.duration_s")
            subtitles = _subtitles_for_timeline(shot)
            timeline_shots.append(
                {
                    "shot_id": shot_id,
                    "start_s": round(cursor, 3),
                    "end_s": round(cursor + duration, 3),
                    "duration_s": duration,
                    "frame_path": str(frame_path),
                    "subtitles": subtitles,
                }
            )
            cursor += duration

        contact_sheet_path = output_dir / "contact_sheet.png"
        _make_contact_sheet(frame_paths, contact_sheet_path, small_font)

        video_path = output_dir / "animatic.mp4"
        _make_video(frame_paths, timeline_shots, video_path)
        probe = _probe_video(video_path, expected_duration_s=cursor)

        timeline_path = output_dir / "timeline.json"
        timeline = {
            "schema_version": plan.get("schema_version", "1.0"),
            "scene_id": plan.get("scene_id"),
            "tone": plan.get("tone"),
            "width": WIDTH,
            "height": HEIGHT,
            "fps": FPS,
            "duration_s": round(cursor, 3),
            "video_path": str(video_path),
            "ffprobe": probe,
            "shots": timeline_shots,
        }
        timeline_path.write_text(
            json.dumps(timeline, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        return {
            "status": "rendered",
            "video_path": str(video_path),
            "contact_sheet_path": str(contact_sheet_path),
            "timeline_path": str(timeline_path),
            "duration_s": round(cursor, 3),
            "errors": [],
        }
    except Exception as exc:  # Keep the public renderer contract simple.
        return {
            "status": "render_failed",
            "video_path": None,
            "contact_sheet_path": None,
            "timeline_path": None,
            "duration_s": None,
            "errors": [str(exc)],
        }


def _ensure_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        if not output_dir.is_dir():
            raise ValueError(f"out_dir is not a directory: {output_dir}")
        if any(output_dir.iterdir()):
            raise FileExistsError(f"out_dir is not empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)


def _load_font(font_path: str, *, size: int = 30) -> Any:
    path = Path(font_path)
    if not path.is_file():
        raise FileNotFoundError(f"font_path does not exist: {font_path}")
    try:
        return ImageFont.truetype(str(path), size=size)
    except OSError as exc:
        raise ValueError(f"font_path is not a usable font: {font_path}") from exc


def _asset_index(manifest: dict, project_root: Path) -> dict[str, dict[str, Any]]:
    assets: dict[str, dict[str, Any]] = {}
    entries = manifest.get("assets")
    if not isinstance(entries, list):
        raise ValueError("manifest.assets must be a list")

    for entry in entries:
        asset_id = entry.get("asset_id")
        if not isinstance(asset_id, str) or not asset_id:
            raise ValueError("manifest asset has missing asset_id")
        path_value = entry.get("path")
        if not isinstance(path_value, str) or not path_value:
            raise ValueError(f"{asset_id}.path must be a non-empty string")
        path = (project_root / path_value).resolve()
        if not path.is_relative_to(project_root):
            raise ValueError(f"{asset_id}.path escapes project_root")
        if not path.is_file():
            raise FileNotFoundError(f"asset file does not exist: {path_value}")
        expected_hash = entry.get("sha256")
        if expected_hash:
            actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual_hash != expected_hash:
                raise ValueError(f"{asset_id}.sha256 mismatch")
        allowed_crops = entry.get("allowed_crops", [])
        if not isinstance(allowed_crops, list):
            raise ValueError(f"{asset_id}.allowed_crops must be a list")
        assets[asset_id] = {
            **entry,
            "path": path,
            "allowed_crops": set(allowed_crops),
        }
    return assets


def _render_shot(
    shot: dict,
    assets: dict[str, dict[str, Any]],
    font: Any,
    small_font: Any,
) -> Any:
    canvas = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, WIDTH, 50), fill=(28, 31, 35))
    shot_id = _safe_id(shot.get("shot_id"), fallback="shot")
    draw.text((48, 14), shot_id, fill=MUTED_TEXT, font=small_font)

    visuals = shot.get("visuals")
    if not isinstance(visuals, list) or not 1 <= len(visuals) <= 2:
        raise ValueError(f"{shot_id}.visuals must contain one or two entries")

    boxes = _visual_boxes(len(visuals))
    for visual, box in zip(visuals, boxes, strict=True):
        _draw_visual(canvas, visual, box, assets, small_font)

    _draw_subtitles(canvas, shot, font)
    return canvas


def _visual_boxes(count: int) -> list[tuple[int, int, int, int]]:
    if count == 1:
        return [(390, 78, 890, 498)]
    if count == 2:
        return [(136, 78, 576, 498), (704, 78, 1144, 498)]
    raise ValueError("only one or two visuals are supported")


def _draw_visual(
    canvas: Any,
    visual: dict,
    box: tuple[int, int, int, int],
    assets: dict[str, dict[str, Any]],
    small_font: Any,
) -> None:
    asset_id = visual.get("asset_id")
    crop = visual.get("crop")
    if asset_id not in assets:
        raise ValueError(f"unknown asset_id: {asset_id}")
    asset = assets[asset_id]
    if crop not in asset["allowed_crops"]:
        raise ValueError(f"crop {crop!r} is not allowed for asset {asset_id}")

    image = Image.open(asset["path"]).convert("RGB")
    if crop == "center_close":
        image = _center_crop(image, 0.6)
    elif crop != "full":
        raise ValueError(f"unsupported crop: {crop}")

    left, top, right, bottom = box
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(box, radius=0, fill=CARD_FILL, outline=CARD_BORDER, width=3)
    fitted = ImageOps.contain(image, (right - left - 32, bottom - top - 52))
    paste_x = left + (right - left - fitted.width) // 2
    paste_y = top + 20 + (bottom - top - 52 - fitted.height) // 2
    canvas.paste(fitted, (paste_x, paste_y))
    label = str(asset.get("character_id") or asset_id)
    draw.text((left + 18, bottom - 30), label, fill=(44, 49, 54), font=small_font)


def _center_crop(image: Any, ratio: float) -> Any:
    width, height = image.size
    crop_w = max(1, int(width * ratio))
    crop_h = max(1, int(height * ratio))
    left = (width - crop_w) // 2
    top = (height - crop_h) // 2
    return image.crop((left, top, left + crop_w, top + crop_h))


def _draw_subtitles(canvas: Any, shot: dict, font: Any) -> None:
    captions = _caption_lines(shot)
    draw = ImageDraw.Draw(canvas)
    box = (70, 528, WIDTH - 70, HEIGHT - 42)
    draw.rounded_rectangle(box, radius=0, fill=CAPTION_BOX)
    lines: list[str] = []
    for caption in captions:
        lines.extend(_wrap_text(caption, font, box[2] - box[0] - 52))
    line_height = _line_height(font)
    total_height = len(lines) * line_height + max(0, len(lines) - 1) * 8
    if total_height > (box[3] - box[1] - 36):
        shot_id = _safe_id(shot.get("shot_id"), fallback="shot")
        raise ValueError(f"{shot_id} subtitles overflow the frame")
    y = box[1] + 22
    for line in lines:
        draw.text((box[0] + 26, y), line, fill=TEXT, font=font)
        y += line_height + 8


def _caption_lines(shot: dict) -> list[str]:
    captions: list[str] = []
    dialogue = shot.get("dialogue", [])
    if not isinstance(dialogue, list):
        raise ValueError("shot.dialogue must be a list")
    for item in dialogue:
        character_id = item.get("character_id")
        text = item.get("text")
        if not character_id or not isinstance(text, str):
            raise ValueError("dialogue entries need character_id and text")
        captions.append(f"{character_id}: {text}")
    narration = shot.get("narration")
    if narration:
        captions.append(f"叙述: {narration}")
    if not captions:
        captions.append("叙述: ")
    return captions


def _subtitles_for_timeline(shot: dict) -> list[dict[str, str]]:
    subtitles: list[dict[str, str]] = []
    for item in shot.get("dialogue", []):
        subtitles.append(
            {
                "kind": "dialogue",
                "character_id": str(item.get("character_id", "")),
                "text": str(item.get("text", "")),
            }
        )
    narration = shot.get("narration")
    if narration:
        subtitles.append({"kind": "narration", "label": "叙述", "text": str(narration)})
    return subtitles


def _wrap_text(text: str, font: Any, max_width: int) -> list[str]:
    if _text_width(text, font) <= max_width:
        return [text]
    lines: list[str] = []
    current = ""
    for char in text:
        candidate = current + char
        if current and _text_width(candidate, font) > max_width:
            lines.append(current.rstrip())
            current = char
        else:
            current = candidate
    if current:
        lines.append(current.rstrip())
    return lines


def _text_width(text: str, font: Any) -> float:
    if hasattr(font, "getlength"):
        return float(font.getlength(text))
    bbox = font.getbbox(text)
    return float(bbox[2] - bbox[0])


def _line_height(font: Any) -> int:
    bbox = font.getbbox("Ag叙述")
    return bbox[3] - bbox[1] + 6


def _make_contact_sheet(frame_paths: list[Path], output_path: Path, font: Any) -> None:
    thumb_w, thumb_h = 320, 180
    label_h = 38
    columns = min(3, max(1, len(frame_paths)))
    rows = math.ceil(len(frame_paths) / columns)
    sheet = Image.new(
        "RGB",
        (columns * thumb_w, rows * (thumb_h + label_h)),
        (250, 251, 252),
    )
    draw = ImageDraw.Draw(sheet)
    for index, path in enumerate(frame_paths):
        row, col = divmod(index, columns)
        x = col * thumb_w
        y = row * (thumb_h + label_h)
        frame = Image.open(path).convert("RGB")
        thumb = ImageOps.contain(frame, (thumb_w, thumb_h))
        sheet.paste(thumb, (x + (thumb_w - thumb.width) // 2, y))
        draw.text((x + 12, y + thumb_h + 8), path.stem, fill=(42, 46, 50), font=font)
    sheet.save(output_path)


def _make_video(
    frame_paths: list[Path],
    timeline_shots: list[dict[str, Any]],
    video_path: Path,
) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is required to render MP4 output")

    command = [ffmpeg, "-hide_banner", "-loglevel", "error"]
    for frame_path, shot in zip(frame_paths, timeline_shots, strict=True):
        command.extend(
            [
                "-loop",
                "1",
                "-framerate",
                str(FPS),
                "-t",
                f"{shot['duration_s']:.6f}",
                "-i",
                str(frame_path),
            ]
        )

    filters = []
    concat_inputs = []
    for index in range(len(frame_paths)):
        filters.append(f"[{index}:v]fps={FPS},format=yuv420p[v{index}]")
        concat_inputs.append(f"[v{index}]")
    filter_complex = (
        ";".join(filters)
        + ";"
        + "".join(concat_inputs)
        + f"concat=n={len(frame_paths)}:v=1:a=0[v]"
    )
    command.extend(
        [
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
            "-r",
            str(FPS),
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(video_path),
        ]
    )
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"ffmpeg failed: {message}")


def _probe_video(video_path: Path, *, expected_duration_s: float) -> dict[str, Any]:
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        raise RuntimeError("ffprobe is required to verify MP4 output")

    command = [
        ffprobe,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,r_frame_rate,duration:format=duration",
        "-of",
        "json",
        str(video_path),
    ]
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"ffprobe failed: {message}")

    data = json.loads(completed.stdout)
    streams = data.get("streams") or []
    if not streams:
        raise ValueError("ffprobe found no video stream")
    stream = streams[0]
    width = int(stream.get("width", 0))
    height = int(stream.get("height", 0))
    if (width, height) != (WIDTH, HEIGHT):
        raise ValueError(f"ffprobe size mismatch: {width}x{height}")

    fps = _parse_rate(stream.get("r_frame_rate"))
    if abs(fps - FPS) > 0.01:
        raise ValueError(f"ffprobe frame rate mismatch: {fps}")

    duration = _probe_duration(stream, data)
    tolerance = (1 / FPS) + CONTAINER_TOLERANCE_S
    if abs(duration - expected_duration_s) > tolerance:
        raise ValueError(
            "ffprobe duration mismatch: "
            f"expected {expected_duration_s:.3f}s, got {duration:.3f}s"
        )

    return {
        "width": width,
        "height": height,
        "fps": fps,
        "duration_s": round(duration, 3),
    }


def _parse_rate(value: Any) -> float:
    if not isinstance(value, str) or not value:
        raise ValueError("ffprobe did not report r_frame_rate")
    numerator, _, denominator = value.partition("/")
    denominator_value = float(denominator or "1")
    if denominator_value == 0:
        raise ValueError("ffprobe reported invalid r_frame_rate")
    return float(numerator) / denominator_value


def _probe_duration(stream: dict[str, Any], data: dict[str, Any]) -> float:
    raw_duration = stream.get("duration") or data.get("format", {}).get("duration")
    if raw_duration is None:
        raise ValueError("ffprobe did not report duration")
    return float(raw_duration)


def _positive_number(value: Any, field: str) -> float:
    if not isinstance(value, (int, float)) or value <= 0:
        raise ValueError(f"{field} must be a positive number")
    return float(value)


def _safe_id(value: Any, *, fallback: str) -> str:
    if not isinstance(value, str) or not value:
        return fallback
    return "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in value)
