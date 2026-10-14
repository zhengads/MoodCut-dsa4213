"""Structural validation for MoodCut scene, shot plan, and asset manifest.

This module checks schema, references, duration, and local image integrity.
It does not assess story semantics or emotional quality.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError

SCHEMA_VERSION = "1.0"
ALLOWED_TONES = frozenset({"affectionate", "suspicious", "hostile"})
ALLOWED_CROPS = frozenset({"full", "center_close"})


def _identifier(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _positive_number(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def _entries(value: Any, name: str, errors: list[str]) -> list[dict]:
    if not isinstance(value, list):
        errors.append(f"{name} must be a list")
        return []
    result = []
    for index, entry in enumerate(value):
        if not isinstance(entry, dict):
            errors.append(f"{name}[{index}] must be an object")
        else:
            result.append(entry)
    return result


def _unique_ids(items: list[dict], field: str, name: str, errors: list[str]) -> set[str]:
    seen: set[str] = set()
    for index, item in enumerate(items):
        value = item.get(field)
        if not _identifier(value):
            errors.append(f"{name}[{index}]: invalid {field}")
        elif value in seen:
            errors.append(f"{name}: duplicate {field}: {value}")
        else:
            seen.add(value)
    return seen


def _validate_asset_file(asset: dict, index: int, root: Path, errors: list[str]) -> None:
    name = f"manifest.assets[{index}]"
    raw_path = asset.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        errors.append(f"{name}: invalid path")
        return
    relative = Path(raw_path)
    if relative.is_absolute() or ".." in relative.parts:
        errors.append(f"{name}: unsafe asset path")
        return
    try:
        resolved = (root / relative).resolve(strict=False)
        resolved.relative_to(root)
    except (ValueError, OSError, RuntimeError):
        errors.append(f"{name}: asset path escapes project root")
        return
    if not resolved.is_file():
        errors.append(f"{name}: asset file does not exist: {raw_path}")
        return
    try:
        with Image.open(resolved) as image:
            if image.format not in {"PNG", "JPEG", "WEBP"}:
                errors.append(f"{name}: unsupported image format")
            size = image.size
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
        errors.append(f"{name}: invalid image file")
        return
    if size != (asset.get("width"), asset.get("height")):
        errors.append(f"{name}: image dimensions do not match manifest")
    expected_hash = asset.get("sha256")
    if not isinstance(expected_hash, str) or len(expected_hash) != 64 or any(c not in "0123456789abcdef" for c in expected_hash):
        errors.append(f"{name}: invalid sha256")
    else:
        try:
            actual_hash = hashlib.sha256(resolved.read_bytes()).hexdigest()
        except OSError:
            errors.append(f"{name}: cannot read asset file")
        else:
            if actual_hash != expected_hash:
                errors.append(f"{name}: SHA-256 mismatch")


def validate_plan(scene: dict, plan: dict, manifest: dict) -> list[str]:
    """Return structural validation errors; an empty list means checks passed.

    Relative asset paths are resolved from the current working directory,
    which must be the MoodCut project root when invoking this function.
    """
    errors: list[str] = []
    if not all(isinstance(item, dict) for item in (scene, plan, manifest)):
        return ["scene, plan, and manifest must be dictionaries"]

    for name, data in (("scene", scene), ("plan", plan), ("manifest", manifest)):
        if data.get("schema_version") != SCHEMA_VERSION:
            errors.append(f"{name}: invalid schema_version")

    scene_id = scene.get("scene_id")
    if not _identifier(scene_id):
        errors.append("scene: invalid scene_id")
    if plan.get("scene_id") != scene_id or not _identifier(plan.get("scene_id")):
        errors.append("plan: scene_id does not match scene")
    tone = scene.get("tone")
    if not isinstance(tone, str) or tone not in ALLOWED_TONES:
        errors.append("scene: invalid tone")
    if plan.get("tone") != tone or not isinstance(plan.get("tone"), str):
        errors.append("plan: tone does not match scene")
    if not _identifier(scene.get("story")):
        errors.append("scene: story must be a non-empty string")

    characters = _entries(scene.get("characters"), "scene.characters", errors)
    character_ids = _unique_ids(characters, "id", "scene.characters", errors)
    if len(characters) != 2:
        errors.append("scene: exactly two characters are required")
    for index, character in enumerate(characters):
        if not _identifier(character.get("name")):
            errors.append(f"scene.characters[{index}]: invalid name")

    beats = _entries(scene.get("beats"), "scene.beats", errors)
    beat_ids = _unique_ids(beats, "id", "scene.beats", errors)
    if not beats:
        errors.append("scene: at least one beat is required")
    for index, beat in enumerate(beats):
        if not _identifier(beat.get("description")):
            errors.append(f"scene.beats[{index}]: invalid description")

    scene_asset_ids = scene.get("asset_ids")
    if not isinstance(scene_asset_ids, list):
        errors.append("scene: asset_ids must be a list")
        scene_asset_ids = []
    allowed_scene_assets: set[str] = set()
    for asset_id in scene_asset_ids:
        if not _identifier(asset_id):
            errors.append("scene: invalid asset_id")
        elif asset_id in allowed_scene_assets:
            errors.append(f"scene: duplicate asset_id: {asset_id}")
        else:
            allowed_scene_assets.add(asset_id)

    assets = _entries(manifest.get("assets"), "manifest.assets", errors)
    manifest_ids = _unique_ids(assets, "asset_id", "manifest.assets", errors)
    asset_map = {a["asset_id"]: a for a in assets if _identifier(a.get("asset_id"))}
    root = Path.cwd().resolve()
    for index, asset in enumerate(assets):
        if asset.get("character_id") not in character_ids:
            errors.append(f"manifest.assets[{index}]: unknown character_id")
        if type(asset.get("width")) is not int or asset["width"] <= 0:
            errors.append(f"manifest.assets[{index}]: invalid width")
        if type(asset.get("height")) is not int or asset["height"] <= 0:
            errors.append(f"manifest.assets[{index}]: invalid height")
        crops = asset.get("allowed_crops")
        if not isinstance(crops, list) or not crops or any(c not in ALLOWED_CROPS for c in crops):
            errors.append(f"manifest.assets[{index}]: invalid allowed_crops")
        _validate_asset_file(asset, index, root, errors)
    for asset_id in sorted(allowed_scene_assets - manifest_ids):
        errors.append(f"scene: unknown asset_id: {asset_id}")

    min_duration = scene.get("min_duration_s")
    max_duration = scene.get("max_duration_s")
    max_shots = scene.get("max_shots")
    if not _positive_number(min_duration) or min_duration > 90:
        errors.append("scene: invalid min_duration_s")
    if not _positive_number(max_duration) or not 60 <= max_duration <= 90:
        errors.append("scene: invalid max_duration_s")
    if _positive_number(min_duration) and _positive_number(max_duration) and min_duration > max_duration:
        errors.append("scene: min_duration_s exceeds max_duration_s")
    if type(max_shots) is not int or not 1 <= max_shots <= 6:
        errors.append("scene: invalid max_shots")

    shots = _entries(plan.get("shots"), "plan.shots", errors)
    _unique_ids(shots, "shot_id", "plan.shots", errors)
    if not 1 <= len(shots) <= 6:
        errors.append("plan: shot count must be between 1 and 6")
    if type(max_shots) is int and 1 <= max_shots <= 6 and len(shots) > max_shots:
        errors.append("plan: shot count exceeds scene max_shots")

    covered_beats: set[str] = set()
    total_duration = 0.0
    durations_valid = True
    for index, shot in enumerate(shots):
        label = f"plan.shots[{index}]"
        duration = shot.get("duration_s")
        if not _positive_number(duration):
            errors.append(f"{label}: invalid duration_s")
            durations_valid = False
        else:
            total_duration += duration

        refs = shot.get("beat_ids")
        if not isinstance(refs, list) or not refs:
            errors.append(f"{label}: beat_ids must be a non-empty list")
        else:
            for beat_id in refs:
                if not _identifier(beat_id) or beat_id not in beat_ids:
                    errors.append(f"{label}: unknown beat reference: {beat_id}")
                else:
                    covered_beats.add(beat_id)

        visuals = _entries(shot.get("visuals"), f"{label}.visuals", errors)
        if not 1 <= len(visuals) <= 2:
            errors.append(f"{label}: visuals count must be between 1 and 2")
        for j, visual in enumerate(visuals):
            aid = visual.get("asset_id")
            if not _identifier(aid) or aid not in manifest_ids or aid not in allowed_scene_assets:
                errors.append(f"{label}.visuals[{j}]: unknown or disallowed asset_id")
            crop = visual.get("crop")
            if crop not in ALLOWED_CROPS:
                errors.append(f"{label}.visuals[{j}]: invalid crop")
            elif aid in asset_map and crop not in asset_map[aid].get("allowed_crops", []):
                errors.append(f"{label}.visuals[{j}]: crop not allowed by manifest")

        dialogue = _entries(shot.get("dialogue"), f"{label}.dialogue", errors)
        for j, line in enumerate(dialogue):
            if line.get("character_id") not in character_ids:
                errors.append(f"{label}.dialogue[{j}]: unknown character_id")
            if not _identifier(line.get("text")):
                errors.append(f"{label}.dialogue[{j}]: invalid text")
        if not isinstance(shot.get("narration"), str):
            errors.append(f"{label}: narration must be a string")

    for missing in sorted(beat_ids - covered_beats):
        errors.append(f"plan: missing beat coverage: {missing}")
    if durations_valid:
        if not 60 <= total_duration <= 90:
            errors.append("plan: total duration must be between 60 and 90 seconds")
        if _positive_number(min_duration) and _positive_number(max_duration):
            if not min_duration <= total_duration <= max_duration:
                errors.append("plan: total duration violates scene limits")
    return errors
