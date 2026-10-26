"""Offline reference-guided request compilers and real A/V concatenation."""
from copy import deepcopy
from decimal import Decimal
import base64
import binascii
import csv
import hashlib
import html
import ipaddress
import json
import math
from pathlib import Path
import re
import subprocess
import shutil
from string import Template
import unicodedata
from urllib.parse import urlsplit

from .contracts import (CONDITIONS, CONTRACT_VERSION, _json_copy,
                        assert_dialogue_only_revision, json_hash, shared_generation_sha256)
from .validation import validate_plan
from .video_client import HEYGEN_MODEL, estimate_video_cost, video_request_controls

_GENERATED_TEMPLATE = Path(__file__).with_name("prompts") / "video_generated.txt"

_LATIN_WORD = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)*")


def _dialogue_fits_duration(dialogue, duration_s):
    """Rough preparation gate, not measured speech timing or a quality score.

    Retain every input accepted by the historical eight-characters/second gate.
    For longer text, count Latin words at 2.5 units/second and other letters or
    numbers at eight/second. A Latin token longer than 15 letters contributes
    multiple units rather than letting an arbitrarily long string count as one
    word. Contractions count once; punctuation and spaces are not spoken units.
    Mixed-script contributions add together across all speakers in the shot.
    These engineering allowances are not validated language-specific rates.
    """
    texts = [line["text"] for line in dialogue]
    if sum(map(len, texts)) <= duration_s * 8:
        return True
    text = " ".join(texts)
    word_units = sum((len(word.group().replace("'", "").replace("’", "")) + 14) // 15
                     for word in _LATIN_WORD.finditer(text))
    remaining = _LATIN_WORD.sub("", text)
    other_units = sum(unicodedata.category(char)[0] in ("L", "N") for char in remaining)
    return word_units / 2.5 + other_units / 8 <= duration_s


def get_video_template_sha256() -> str:
    """Identity of the actual UTF-8 template text used by the 1.1 compiler.

    Read text with universal newlines, just as when rendering the prompt, so
    Windows/Linux checkouts identify the same effective template content.
    """
    text = _GENERATED_TEMPLATE.read_text(encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_generated_video_bundle(scene, initial, plans, manifest, settings, *,
                                 project_root, template_sha256, pricing_config) -> dict:
    """Compile full plans without clients, network or media generation.

    Local asset bytes and the actual template are checked. Quotes use only the
    supplied price snapshot; they are neither spending nor live model preflight.
    Invalid candidates are rejected, never projected onto a different script.
    """
    scene, initial, plans, manifest, settings, pricing = _json_copy(
        [scene, initial, plans, manifest, settings, pricing_config])
    if not isinstance(plans, dict) or set(plans) != set(CONDITIONS):
        raise ValueError("plans must contain exactly baseline/generic_review/moodcut")
    if not isinstance(pricing, dict):
        raise ValueError("pricing_config must be an object")
    template = _GENERATED_TEMPLATE.read_text(encoding="utf-8")
    actual_template_sha256 = hashlib.sha256(template.encode("utf-8")).hexdigest()
    if template_sha256 != actual_template_sha256:
        raise ValueError("template_sha256 does not match the actual generated video template; prepare a new source block")
    shared = shared_generation_sha256(scene, initial, manifest, settings, template_sha256=actual_template_sha256)
    for label, plan in [("initial", initial), *[(c, plans[c]) for c in CONDITIONS]]:
        errors = validate_plan(scene, plan, manifest, project_root=project_root, output_mode="generated")
        if errors:
            raise ValueError(label + ": " + "; ".join(errors))
        assert_dialogue_only_revision(initial, plan)
        if shared_generation_sha256(scene, plan, manifest, settings, template_sha256=actual_template_sha256) != shared:
            raise ValueError(label + ": shared generation identity mismatch")
    initial_hash = json_hash(initial)
    if json_hash(plans["baseline"]) != initial_hash:
        raise ValueError("baseline must equal the complete initial plan")

    assets = {a["asset_id"]: a for a in manifest["assets"]}
    names = {c["id"]: c["name"] for c in scene["characters"]}
    bindings = {c["id"]: c for c in settings["characters"]}
    references, reference_records, reference_notes = [], [], []
    # Include every selected reference, in the same order as the shared identity;
    # multiple images of one character need not become a new first-frame layout.
    for index, asset_id in enumerate(scene["asset_ids"], 1):
        asset = assets[asset_id]
        url = asset.get("source_url")
        if settings["model"] == HEYGEN_MODEL and isinstance(url, str) and url.startswith("data:image/png;base64,"):
            try:
                encoded = base64.b64decode(url.split(",", 1)[1], validate=True)
            except (ValueError, binascii.Error):
                raise ValueError("Invalid inline PNG reference") from None
            if not encoded.startswith(b"\x89PNG\r\n\x1a\n") or hashlib.sha256(encoded).hexdigest() != asset["sha256"]:
                raise ValueError("Inline PNG reference differs from the verified asset bytes")
        else:
            url = _public_reference(url)
        references.append({"type": "image_url", "image_url": {"url": url}})
        reference_records.append({k: asset[k] for k in ("asset_id", "character_id", "source_url", "sha256")})
        reference_notes.append({"reference_index": index, "asset_id": asset_id,
                                "character_id": asset["character_id"], "name": names[asset["character_id"]],
                                "primary_identity": bindings[asset["character_id"]]["asset_id"] == asset_id})
        if settings["model"] == HEYGEN_MODEL:
            reference_notes[-1]["provider_reference_label"] = f"<Picture {index}>"
    common = {"style": settings["style"], "sound": settings["sound"], "target_tone": scene["tone"],
              "scene_direction": initial["scene_direction"], "reference_images": reference_notes,
              "characters": [dict(c, name=names[c["id"]]) for c in settings["characters"]]}

    def prompt_json(value):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)

    conditions = []
    for condition in CONDITIONS:
        jobs = []
        for index, shot in enumerate(plans[condition]["shots"]):
            if not _dialogue_fits_duration(shot["dialogue"], shot["duration_s"]):
                raise ValueError(f"{condition}/{shot['shot_id']}: dialogue too long for the fixed clip duration")
            context = {**common, "shot": {k: initial["shots"][index][k]
                                         for k in ("direction", "duration_s", "visuals")}}
            prompt = Template(template).substitute(shared=prompt_json(context), dialogue=prompt_json(shot["dialogue"]))
            request = {"model": settings["model"], "prompt": prompt, "duration": shot["duration_s"],
                       "resolution": settings["resolution"], "aspect_ratio": settings["aspect_ratio"],
                       **video_request_controls(settings["model"]), "seed": settings["seed"] + index,
                       "input_references": deepcopy(references)}
            jobs.append({"shot_id": shot["shot_id"], "request": request,
                         "request_sha256": json_hash(request),
                         "quoted_cost_usd": str(estimate_video_cost(pricing, request))})
        conditions.append({"condition": condition, "final_plan_sha256": json_hash(plans[condition]), "jobs": jobs})
    return {"schema_version": CONTRACT_VERSION, "output_mode": "generated", "kind": "generated_three_condition_bundle",
            "scene_id": scene["scene_id"], "initial_plan_sha256": initial_hash,
            "shared_generation_sha256": shared, "template_sha256": actual_template_sha256,
            "references": reference_records, "settings": settings, "conditions": conditions}


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
    if config.get("generate_audio") is not True or type(config.get("seed")) is not int:
        raise ValueError("Native audio and an integer seed are required")
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
        estimate_video_cost(config, {"model":config["model"], "resolution":config["resolution"],
                                    "aspect_ratio":config["aspect_ratio"], "duration":duration, "generate_audio":True})
        if not isinstance(setting.get("direction"), str) or not setting["direction"].strip():
            raise ValueError("Every clip requires an explicit shared direction")
        total += duration
    conditions = []
    for label, plan in (("baseline", initial), ("dialogue_revision", projected)):
        jobs = []
        for index, (shot, setting) in enumerate(zip(plan["shots"], settings)):
            if not _dialogue_fits_duration(shot["dialogue"], setting["duration_s"]):
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
                         "estimated_cost_usd": str(estimate_video_cost(config, request))})
        conditions.append({"condition": label, "source_plan_sha256": json_hash(plan), "jobs": jobs})
    return {"schema_version": "1.0", "kind": "derived_development_video_pair", "scene_id": scene["scene_id"],
            "initial_plan_sha256": json_hash(initial), "candidate_plan_sha256": json_hash(revised),
            "projected_plan_sha256": json_hash(projected), "projected_plan": projected,
            "projection_verification": "not_independently_verified", "source_plan_duration_s": sum(s["duration_s"] for s in initial["shots"]),
            "duration_s_per_condition": total, "estimated_cost_usd": str(sum(
                (Decimal(job["estimated_cost_usd"]) for condition in conditions for job in condition["jobs"]), Decimal(0))),
            "references": reference_records, "dialogue_changes": changes,
            "ignored_non_dialogue_changes": ignored, "config": deepcopy(config), "conditions": conditions}


def _probe(path, *, include_raw=False):
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
    result = {"duration_s": duration, "has_audio": True, "width": videos[0]["width"], "height": videos[0]["height"]}
    return {**result, "ffprobe": data} if include_raw else result


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


def _file_sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _inspection_frames(clips, directory):
    """Extract actual clip pixels; reuse the existing contact-sheet layout."""
    from PIL import ImageFont
    from .renderer import _make_contact_sheet
    frames, samples = [], []
    directory.mkdir()
    for index, (path, duration, shot_id) in enumerate(clips, 1):
        for fraction in (.1, .5, .9):
            target = directory / f"shot{index:02d}_t{int(fraction*100):02d}.png"
            subprocess.run(["ffmpeg", "-v", "error", "-n", "-ss", str(duration*fraction), "-i", str(path),
                "-frames:v", "1", "-vf", "scale=320:180:force_original_aspect_ratio=decrease,pad=320:180:(ow-iw)/2:(oh-ih)/2",
                str(target)], check=True, capture_output=True, timeout=60)
            if not target.is_file():
                raise ValueError("Could not extract an actual video frame")
            frames.append(target)
            samples.append({"shot_id": shot_id, "time_s": duration*fraction,
                            "path": "frames/"+target.name, "sha256": _file_sha256(target)})
    _make_contact_sheet(frames, directory.parent / "contact_sheet.png", ImageFont.load_default())
    return samples


def _inspection_page(output, summary, source):
    escape = lambda value: html.escape(str(value), quote=True)
    page = ['<!doctype html><html lang="zh-CN"><meta charset="utf-8">',
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; media-src \'self\' file:; img-src \'self\' file:; style-src \'unsafe-inline\'">',
        '<title>MoodCut · 本地视频检查</title><style>body{font:17px system-ui;max-width:1100px;margin:32px auto;padding:0 20px;color:#202a32;background:#f4f1e9}video,img{width:100%;max-height:650px;object-fit:contain;background:#151a20}section{margin:32px 0}table{width:100%;border-collapse:collapse}td,th{padding:10px;text-align:left;vertical-align:top;border-bottom:1px solid #aaa}pre{white-space:pre-wrap;overflow-wrap:anywhere}a{color:#235c68}</style>',
        '<h1>MoodCut · 本地视频检查</h1>',
        '<p><strong>开发检查材料：含条件、目标和台词，不用于盲评。文件检查通过不表示人物、台词、口型或情绪合格。</strong></p>',
        '<p><strong>素材来源声明：'+escape(summary['media_origin'])+
        ('；synthetic 为动态图案/正弦音等软件媒体，不是模型生成视频或效果证据。' if summary['media_origin'] == 'synthetic' else '；仅使用提供的本地文件，来源与真实质量未经本工具独立认定。')+'</strong></p>',
        '<p>检查包状态：'+escape(summary['status'])+' · 目标：'+escape(source['scene']['tone'])+'</p>',
        '<p><a href="manual_checks.csv" download>空白人工检查表 CSV</a> · <a href="manual_checks.json">JSON 检查表</a> · <a href="inspection.json">检查记录</a> · <a href="'+escape(summary['records_path'])+'">原回执与费用记录</a></p>',
        '<p>请另存填写人物/动作、台词/说话人、声音/口型、连续性及备注；本工具不自动评分。</p>']
    for row in summary['conditions']:
        condition = row['condition']  # Fixed public condition names; file names never use shot IDs.
        page += ['<section><h2>'+escape(condition)+'</h2><p>'+escape(row['status'])+'</p>']
        if row['status'] == 'ready_requires_manual_inspection':
            page += [f'<video controls preload="metadata" src="{condition}/film.mp4"></video>',
                     f'<p><a href="{condition}/media_check.json">成片来源绑定</a> · <a href="{condition}/ffprobe.json">ffprobe 信息</a></p>',
                     f'<img src="{condition}/contact_sheet.png" alt="实际片段在10%、50%、90%处的抽帧接触表">',
                     '<p>每行依次为同镜头10%、50%、90%处的真实抽帧；抽样画面不能替代完整听看。</p>']
        if row['errors']:
            page += ['<pre>'+escape('\n'.join(row['errors']))+'</pre>']
        page += ['<table><tr><th>镜头/共同动作</th><th>预期台词（不是语音识别结果）</th></tr>']
        selected = set(summary['selected_shot_ids'])
        for shot in source['plans'][condition]['shots']:
            if shot['shot_id'] in selected:
                spoken = '\n'.join(line['character_id']+': '+line['text'] for line in shot['dialogue']) or '（无台词）'
                page += ['<tr><td>'+escape(shot['shot_id'])+'<br>'+escape(shot['direction'])+'</td><td><pre>'+escape(spoken)+'</pre></td></tr>']
        page += ['</table></section>']
    page += ['</html>']
    (output / 'index.html').write_text('\n'.join(page), encoding='utf-8')


def inspect_generated_video(preparation, *, evidence, out_dir, pricing_config,
                            media_origin, project_root=".") -> dict:
    """Bind and inspect existing local A/V through the P1 receipt boundary.

    No client, model, catalogue, download or retry. Subjective checklist cells
    stay empty. Failed/unknown receipts remain in the original accounting path.
    """
    from .pipeline import assemble_generated_records, read_json, write_json
    if media_origin not in ("synthetic", "provided_local"):
        raise ValueError("Declare media_origin as synthetic or provided_local")
    output = Path(out_dir).resolve()
    if output.exists() or output.is_symlink():
        raise FileExistsError("Output already exists; choose a new inspection directory")
    evidence_path = Path(evidence).resolve(strict=True)
    # P1 validates prepared sources, receipts, reuse, A/V and costs before it
    # creates the first output. Do not duplicate that validation/accounting here.
    preflight = assemble_generated_records(preparation, evidence=evidence_path, out_dir=output / "preflight_records",
        pricing_config=pricing_config, project_root=project_root)
    source = read_json(output / "preflight_records/source_inputs.json")
    bundle = read_json(output / "preflight_records/bundle.json")
    supplied = read_json(output / "preflight_records/evidence.json")
    # Preserve the supplied evidence snapshot; resolve pointers for a new file
    # rather than modifying receipts, costs or the original evidence manifest.
    def absolute_pointer(value):
        # Invalid/missing receipt pointers remain invalid evidence for P1; do
        # not reinterpret a failed URL or non-string as a different local file.
        if not isinstance(value, str) or not value.strip() or '://' in value:
            return value
        path = Path(value)
        return str((path if path.is_absolute() else evidence_path.parent / path).resolve())
    for condition in supplied['conditions']:
        if condition.get('media_check_path') is not None:
            condition['media_check_path'] = absolute_pointer(condition['media_check_path'])
        for job in condition.get('jobs', []):
            if job.get('receipt_path') is not None:
                job['receipt_path'] = absolute_pointer(job['receipt_path'])
    rows = []
    for run, compiled, condition in zip(preflight['runs'], bundle['conditions'], supplied['conditions']):
        name = run['condition']
        row = {'condition': name, 'status': 'not_ready', 'errors': list(run['errors'])}
        rows.append(row)
        jobs = run['generation_jobs']
        if run['run_status'] == 'failed':
            row['status'] = 'failed'
            continue
        if not all(job['status'] == 'downloaded' for job in jobs):
            continue
        directory = output / name
        directory.mkdir()
        check_path = directory / 'media_check.json'
        condition['media_check_path'] = str(check_path)
        try:
            (directory / 'clips').mkdir()
            bindings, files, clips, probes = [], [], [], []
            for index, (job, request_job) in enumerate(zip(jobs, compiled['jobs'])):
                original = Path(job['video_path']).resolve(strict=True)
                expected = job['media_check']['sha256']
                if _file_sha256(original) != expected:
                    raise ValueError('Source clip changed after receipt validation')
                copied = directory / 'clips' / f'shot{index:02d}.mp4'
                shutil.copyfile(original, copied)
                if _file_sha256(copied) != expected:
                    raise ValueError('Source clip changed while copying')
                duration = request_job['request']['duration']
                checked = _probe(copied, include_raw=True)
                if abs(checked['duration_s'] - duration) > .5:
                    raise ValueError('Copied clip duration differs from its request')
                bindings.append({'shot_id': job['shot_id'], 'request_sha256': job['request_sha256'], 'sha256': expected})
                files.append({'path': 'clips/'+copied.name, 'original_path': str(original), 'sha256': expected})
                clips.append((copied, duration, job['shot_id']))
                probes.append({'shot_id': job['shot_id'], **checked})
            film = directory / 'film.mp4'
            if run['run_status'] == 'completed':
                # Existing assembly has already passed P1's binding and byte check.
                shutil.copyfile(run['video_path'], film)
                if _file_sha256(film) != run['media_check']['sha256']:
                    raise ValueError('Existing assembly changed while copying')
            else:
                assemble_generated_clips([str(c[0]) for c in clips], durations=[c[1] for c in clips], out_path=str(film))
            film_probe = _probe(film, include_raw=True)
            if abs(film_probe['duration_s'] - sum(c[1] for c in clips)) > .5:
                raise ValueError('Assembled duration differs from selected requests')
            film_hash = _file_sha256(film)
            samples = _inspection_frames(clips, directory / 'frames')
            # Check both originals and packaged copies again after FFmpeg work.
            if _file_sha256(film) != film_hash or any(
                    _file_sha256(Path(f['original_path'])) != f['sha256'] or
                    _file_sha256(directory / f['path']) != f['sha256'] for f in files):
                raise ValueError('Media bytes changed during inspection')
            check = {k: v for k, v in film_probe.items() if k != 'ffprobe'}
            check.update(schema_version=CONTRACT_VERSION, output_mode='generated', kind='generated_media_check',
                block_id=preflight['block_id'], condition=name, media_origin=media_origin,
                initial_plan_sha256=preflight['initial_plan_sha256'], shared_generation_sha256=preflight['shared_generation_sha256'],
                selected_shot_ids=preflight['selected_shot_ids'], video_path='film.mp4', sha256=film_hash,
                source_clips=bindings, source_files=files, frame_samples=samples,
                speech_and_visual_quality='requires_manual_inspection')
            write_json(check_path, check)
            write_json(directory / 'ffprobe.json', {'film': film_probe, 'clips': probes})
            row.update(status='ready_requires_manual_inspection', media_check_path=name+'/media_check.json',
                       video_path=name+'/film.mp4', sha256=film_hash, source_clips=bindings)
        except (ValueError, TypeError, KeyError, OSError, subprocess.SubprocessError) as exc:
            row.update(status='failed', errors=[f'{type(exc).__name__}: {exc}'])
            write_json(check_path, {'status': 'failed', 'errors': row['errors'], 'speech_and_visual_quality': 'not_reviewed'})
    write_json(output / 'evidence.json', supplied)
    errors = []
    records_path = 'records/block.json'
    try:
        records = assemble_generated_records(preparation, evidence=output / 'evidence.json', out_dir=output / 'records',
            pricing_config=pricing_config, project_root=project_root)
        for row, run in zip(rows, records['runs']):
            if run['run_status'] == 'failed':
                row.update(status='failed', errors=list(dict.fromkeys(row['errors']+run['errors'])))
            elif row['status'] == 'ready_requires_manual_inspection' and run['run_status'] != 'completed':
                row.update(status='not_ready', errors=['Receipt/media completion changed during inspection'])
    except (ValueError, TypeError, KeyError, OSError, subprocess.SubprocessError) as exc:
        errors = [f'Final source revalidation failed: {type(exc).__name__}: {exc}']
        records_path = 'preflight_records/block.json'
        for row in rows:
            row.update(status='failed', errors=row['errors']+errors)
    status = ('failed' if errors or any(r['status'] == 'failed' for r in rows) else
              'ready_requires_manual_inspection' if all(r['status'] == 'ready_requires_manual_inspection' for r in rows) else 'incomplete')
    summary = {'schema_version': CONTRACT_VERSION, 'output_mode': 'generated', 'kind': 'generated_media_inspection',
        'status': status, 'media_origin': media_origin, 'block_id': preflight['block_id'],
        'initial_plan_sha256': preflight['initial_plan_sha256'], 'shared_generation_sha256': preflight['shared_generation_sha256'],
        'selected_shot_ids': preflight['selected_shot_ids'], 'conditions': rows, 'records_path': records_path,
        'comparison_status': 'ineligible' if status == 'failed' else 'not_checked', 'errors': errors,
        'speech_and_visual_quality': 'not_reviewed',
        'inspection_activity': {'calls': 0, 'real_http_calls': 0, 'generation_posts': 0, 'video_get_calls': 0,
                                'provider_cost_usd': 0.0}}
    checks = []
    for row, compiled in zip(rows, bundle['conditions']):
        for job in compiled['jobs']:
            clip = next((c for c in row.get('source_clips', []) if c['shot_id'] == job['shot_id']), {})
            checks.append({'condition': row['condition'], 'shot_id': job['shot_id'], 'request_sha256': job['request_sha256'],
                'clip_sha256': clip.get('sha256'), 'film_sha256': row.get('sha256'), 'material_status': row['status'],
                'character_action': None, 'dialogue_speaker': None, 'audio_lipsync': None, 'continuity': None, 'notes': ''})
    write_json(output / 'manual_checks.json', {'status': 'not_reviewed', 'media_origin': media_origin, 'items': checks})
    with (output / 'manual_checks.csv').open('x', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(checks[0]))
        writer.writeheader()
        writer.writerows({key: "'"+value if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@'))
                          else value for key, value in item.items()} for item in checks)
    write_json(output / 'inspection.json', summary)
    _inspection_page(output, summary, source)
    return summary
