"""Reference-guided development video requests and real A/V concatenation.

This path does not change the legacy animatic contract or formal experiment.
"""
from copy import deepcopy
from decimal import Decimal
import ipaddress
import json
import math
from pathlib import Path
import subprocess
from urllib.parse import urlsplit

from .pipeline import json_hash
from .validation import validate_plan


def _public_reference(url):
    if not isinstance(url, str):
        raise ValueError("Reference requires a public HTTPS source_url")
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password or parts.fragment:
        raise ValueError("Reference requires a public HTTPS source_url")
    if parts.port not in (None, 443) or parts.hostname in {"localhost", "localhost.localdomain"}:
        raise ValueError("Reference URL must be public")
    try:
        address = ipaddress.ip_address(parts.hostname)
    except ValueError:
        if "." not in parts.hostname or parts.hostname.endswith((".local", ".localhost", ".internal")):
            raise ValueError("Reference URL must be public")
    else:
        if not address.is_global:
            raise ValueError("Reference URL must be public")
    return url


def build_video_bundle(scene: dict, initial: dict, revised: dict,
                       manifest: dict, config: dict, *, project_root: str) -> dict:
    """Project a candidate onto dialogue only; compile an explicitly derived pair."""
    if config.get("schema_version") != "1.0" or config.get("scene_id") != scene.get("scene_id"):
        raise ValueError("Video config must match the source scene")
    for name, plan in (("initial", initial), ("revised", revised)):
        errors = validate_plan(scene, plan, manifest, project_root=project_root)
        if errors:
            raise ValueError(name + ": " + "; ".join(errors))
    original_ids = [s["shot_id"] for s in initial["shots"]]
    if [s["shot_id"] for s in revised["shots"]] != original_ids:
        raise ValueError("Candidate must retain the exact source shot order")
    settings = config.get("shots")
    if not isinstance(settings, list) or [s.get("shot_id") for s in settings] != original_ids:
        raise ValueError("Video directions must match the exact source shot order")
    if config.get("model") != "alibaba/wan-2.7" or config.get("resolution") != "720p" or config.get("aspect_ratio") != "16:9":
        raise ValueError("This adapter is pinned to Wan 2.7, 720p, 16:9; update and verify the contract to change it")
    if config.get("generate_audio") is not True or type(config.get("seed")) is not int:
        raise ValueError("Native audio and an integer seed are required")
    rate = Decimal(str(config.get("price_per_second_usd")))
    if not rate.is_finite() or rate <= 0:
        raise ValueError("A known positive price is required")
    for field in ("style", "sound"):
        if not isinstance(config.get(field), str) or not config[field].strip():
            raise ValueError(f"Missing video {field}")
    character_ids = [c["id"] for c in scene["characters"]]
    characters = config.get("characters")
    if not isinstance(characters, list) or [c.get("id") for c in characters] != character_ids:
        raise ValueError("Video characters must match the scene character order")
    assets = {a["asset_id"]: a for a in manifest["assets"]}
    names = {c["id"]: c["name"] for c in scene["characters"]}
    references, reference_records, identity_notes = [], [], []
    for index, character in enumerate(characters, 1):
        asset_id = character.get("asset_id")
        if asset_id not in scene["asset_ids"] or asset_id not in assets:
            raise ValueError("Unknown character reference asset")
        asset = assets[asset_id]
        if asset["character_id"] != character["id"] or not isinstance(character.get("voice"), str) or not character["voice"].strip():
            raise ValueError("Reference/voice character mapping is invalid")
        url = _public_reference(asset.get("source_url"))
        references.append({"type": "image_url", "image_url": {"url": url}})
        reference_records.append({k: asset[k] for k in ("asset_id", "character_id", "source_url", "sha256")})
        identity_notes.append(f"Reference image {index}: {names[character['id']]} ({character['id']}). Voice: {character['voice']}")

    projected = deepcopy(initial)
    changes, ignored = [], []
    for key in sorted(set(initial) | set(revised)):
        if key != "shots" and initial.get(key) != revised.get(key):
            ignored.append(key)
    for original, candidate, output in zip(initial["shots"], revised["shots"], projected["shots"]):
        for key in sorted(set(original) | set(candidate)):
            if key != "dialogue" and original.get(key) != candidate.get(key):
                ignored.append(f"shots.{original['shot_id']}.{key}")
        output["dialogue"] = deepcopy(candidate["dialogue"])
        if original["dialogue"] != output["dialogue"]:
            changes.append({"shot_id": original["shot_id"], "before": original["dialogue"], "after": output["dialogue"]})

    total = 0
    for setting in settings:
        duration = setting.get("duration_s")
        if type(duration) is not int or duration not in range(2, 11):
            raise ValueError("Wan 2.7 clip duration must be an integer from 2 through 10")
        if not isinstance(setting.get("direction"), str) or not setting["direction"].strip():
            raise ValueError("Every clip requires an explicit shared direction")
        total += duration
    conditions = []
    for label, plan in (("baseline", initial), ("dialogue_revision", projected)):
        jobs = []
        for index, (shot, setting) in enumerate(zip(plan["shots"], settings)):
            # Conservative preparation check, not a guarantee about generated speech speed.
            if sum(len(line["text"]) for line in shot["dialogue"]) > setting["duration_s"] * 8:
                raise ValueError(f"Dialogue too long for clip {shot['shot_id']}; shorten it or explicitly change clip duration")
            spoken = "\n".join(f"{names[line['character_id']]} says exactly: {json.dumps(line['text'], ensure_ascii=False)}"
                                for line in shot["dialogue"]) or "No spoken dialogue in this shot."
            prompt = "\n\n".join((config["style"], "\n".join(identity_notes),
                                     "Scene target atmosphere: " + scene["tone"],
                                     "Required visible action: " + setting["direction"], config["sound"], spoken))
            request = {"model": config["model"], "prompt": prompt, "duration": setting["duration_s"],
                       "resolution": config["resolution"], "aspect_ratio": config["aspect_ratio"],
                       "generate_audio": True, "seed": config["seed"] + index,
                       "input_references": deepcopy(references)}
            jobs.append({"shot_id": shot["shot_id"], "direction": setting["direction"],
                         "dialogue": deepcopy(shot["dialogue"]), "request": request,
                         "request_sha256": json_hash(request),
                         "estimated_cost_usd": str(rate * setting["duration_s"])})
        conditions.append({"condition": label, "source_plan_sha256": json_hash(plan), "jobs": jobs})
    return {"schema_version": "1.0", "kind": "derived_development_video_pair", "scene_id": scene["scene_id"],
            "initial_plan_sha256": json_hash(initial), "candidate_plan_sha256": json_hash(revised),
            "projected_plan_sha256": json_hash(projected), "projected_plan": projected,
            "projection_verification": "not_independently_verified", "source_plan_duration_s": sum(s["duration_s"] for s in initial["shots"]),
            "duration_s_per_condition": total, "estimated_cost_usd": str(rate * total * 2),
            "references": reference_records, "dialogue_changes": changes,
            "ignored_non_dialogue_changes": ignored, "config": deepcopy(config), "conditions": conditions}


def _probe(path):
    process = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
                             check=True, capture_output=True, text=True, encoding="utf-8", timeout=60)
    data = json.loads(process.stdout)
    streams = data.get("streams", [])
    videos = [s for s in streams if s.get("codec_type") == "video"]
    audios = [s for s in streams if s.get("codec_type") == "audio"]
    if not videos or not audios:
        raise ValueError("Generated clip must contain actual video and audio streams")
    duration = float(data["format"]["duration"])
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Invalid generated clip duration")
    return {"duration_s": duration, "has_audio": True, "width": videos[0]["width"], "height": videos[0]["height"]}


def assemble_generated_clips(paths: list[str], *, durations: list[int], out_path: str) -> dict:
    """Concatenate actual generated A/V; never create a still-frame fallback."""
    target = Path(out_path).resolve()
    if target.exists():
        raise FileExistsError("Output already exists")
    if not paths or len(paths) != len(durations):
        raise ValueError("One expected duration is required for every generated clip")
    probes = [_probe(Path(path).resolve(strict=True)) for path in paths]
    for probe, duration in zip(probes, durations):
        if abs(probe["duration_s"] - duration) > .5:
            raise ValueError("Generated clip duration does not match its request")
    target.parent.mkdir(parents=True, exist_ok=True)
    command = ["ffmpeg", "-v", "error", "-n"]
    for path in paths:
        command.extend(["-i", str(Path(path).resolve())])
    filters = []
    for index in range(len(paths)):
        filters.append(f"[{index}:v:0]scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=24,setpts=PTS-STARTPTS[v{index}]")
        filters.append(f"[{index}:a:0]aresample=48000,aformat=channel_layouts=stereo,asetpts=PTS-STARTPTS[a{index}]")
    filters.append("".join(f"[v{i}][a{i}]" for i in range(len(paths))) + f"concat=n={len(paths)}:v=1:a=1[v][a]")
    command.extend(["-filter_complex", ";".join(filters), "-map", "[v]", "-map", "[a]", "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart", str(target)])
    subprocess.run(command, check=True, capture_output=True, timeout=300)
    result = _probe(target)
    if abs(result["duration_s"] - sum(p["duration_s"] for p in probes)) > .5:
        raise ValueError("Assembled duration differs from generated source durations")
    return {**result, "video_path": str(target), "speech_and_visual_quality": "requires_manual_inspection"}
