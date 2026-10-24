"""Offline reference-to-video preparation and local synthetic media checks."""
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
import hashlib
import json
import shutil
import subprocess

import pytest

from moodcut.video_generation import (build_video_bundle, assemble_generated_clips,
                                     build_generated_video_bundle, get_video_template_sha256)
from moodcut.contracts import CONDITIONS, assert_dialogue_only_revision, shared_generation_sha256
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


def test_seedance_bundle_keeps_identity_and_prices_native_audio(inputs):
    from decimal import Decimal
    original = build_video_bundle(*inputs, project_root=str(ROOT))
    cfg = inputs[-1]
    cfg['model'] = 'bytedance/seedance-2.0-mini'
    cfg.pop('price_per_second_usd')
    cfg['price_per_million_video_tokens_usd'] = '3.50'
    seed = build_video_bundle(*inputs, project_root=str(ROOT))
    assert Decimal(seed['estimated_cost_usd']) == Decimal('2.7216')
    for before, after in zip(original['conditions'], seed['conditions']):
        for a,b in zip(before['jobs'],after['jobs']):
            assert a['request']['prompt'] == b['request']['prompt']
            assert a['request']['input_references'] == b['request']['input_references']
            assert b['request']['generate_audio'] is True
            assert Decimal(b['estimated_cost_usd']) == Decimal('0.4536')


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


@pytest.mark.parametrize("case,status,accepted", [
    ("no_issues", "unchanged", True), ("empty_patch", "unchanged", True),
    ("changed", "applied", True), ("rejected", "rejected", False),
    ("failed", "review_failed", False),
])
def test_real_review_records_feed_source_gate_offline(inputs, tmp_path, case, status, accepted):
    """Use real review/pipeline code with FakeClient; no video job or network."""
    from moodcut.client import FakeClient
    from moodcut.pipeline import run_condition, write_json
    command = load_command()
    scene, initial, _, manifest, _ = inputs
    shutil.copytree(ROOT / "tests/fixtures", tmp_path / "tests/fixtures")
    run = tmp_path / "runs/integrated"
    write_json(run / "scene.json", scene)
    write_json(run / "assets.json", manifest)
    report = {"schema_version": "1.0", "scene_id": scene["scene_id"], "mode": "moodcut", "issues": []}
    responses = []
    if case != "failed":
        if case != "no_issues":
            report["issues"] = [{"issue_id": "r1", "shot_id": "s1", "dimension": "tone",
                                 "evidence": "Software fixture", "suggestion": "Revise dialogue", "severity": "minor"}]
        responses.append(report)
        if case != "no_issues":
            changes = {"story": "invalid"} if case == "rejected" else {
                "dialogue": [{"character_id": "a", "text": "请你收好。"}]}
            responses.append({"schema_version": "1.0", "scene_id": scene["scene_id"],
                              "edits": [] if case == "empty_patch" else [
                                  {"issue_id": "r1", "shot_id": "s1", "set": changes}]})
            if case != "rejected":
                responses.append({"scene_id": scene["scene_id"], "resolved_issue_ids": [],
                                  "unresolved_issue_ids": ["r1"], "new_concerns": []})
    for condition, client in (("baseline", FakeClient([])), ("moodcut", FakeClient(responses))):
        record = run_condition(scene, initial, manifest, client, condition=condition,
                               out_dir=str(run / condition), project_root=str(tmp_path), font_path=None, render=False)
    assert record["review_status"] == status
    assert record["run_status"] == ("completed" if accepted else "failed")
    assert record["real_http_calls"] == 0
    if accepted:
        source = command.load_source(run)
        assert json_hash(source[2]) == record["final_plan_sha256"]
        if status == "unchanged":
            assert source[1] == source[2]
    else:
        with pytest.raises(ValueError, match="successful source review"):
            command.load_source(run)


@pytest.mark.parametrize("status", ["unchanged", "no_changes"])
def test_unchanged_alias_requires_actual_unchanged_plan(inputs, tmp_path, status):
    command = load_command()
    run = prepare_command_root(inputs, tmp_path)
    record = json.loads((run / "moodcut/run.json").read_text())
    record["review_status"] = status
    (run / "moodcut/run.json").write_text(json.dumps(record), encoding="utf-8")
    # Consistent hashes alone cannot make a changed plan an unchanged result.
    with pytest.raises(ValueError, match="[Uu]nchanged"):
        command.load_source(run)
    initial = json.loads((run / "baseline/initial.json").read_text())
    (run / "moodcut/final.json").write_text(json.dumps(initial), encoding="utf-8")
    record["final_plan_sha256"] = json_hash(initial)
    (run / "moodcut/run.json").write_text(json.dumps(record), encoding="utf-8")
    source = command.load_source(run)
    assert source[1] == source[2]
    record["run_status"] = "failed"
    (run / "moodcut/run.json").write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ValueError, match="successful source review"):
        command.load_source(run)


def test_unchanged_source_can_prepare_offline_without_submitting(inputs, tmp_path, monkeypatch):
    command = load_command()
    run = prepare_command_root(inputs, tmp_path)
    initial = json.loads((run / "baseline/initial.json").read_text())
    (run / "moodcut/final.json").write_text(json.dumps(initial), encoding="utf-8")
    record = json.loads((run / "moodcut/run.json").read_text())
    record.update(review_status="unchanged", final_plan_sha256=json_hash(initial))
    (run / "moodcut/run.json").write_text(json.dumps(record), encoding="utf-8")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr(command, "fetch_video_models", lambda: pytest.fail("Offline means no network"))
    monkeypatch.setattr(command, "OpenRouterVideoClient", lambda *a, **k: pytest.fail("No client permitted"))
    assert command.main(["--project-root", str(tmp_path), "--run", "runs/source", "--output", "runs/unchanged"]) == 0
    bundle = json.loads((tmp_path / "runs/unchanged/bundle.json").read_text())
    assert bundle["dialogue_changes"] == []


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


@pytest.fixture(params=["letter", "umbrella"])
def generated_inputs(request, monkeypatch):
    return _generated_case(request.param, monkeypatch)


def _generated_case(kind, monkeypatch):
    """Task-local hand-written software stories, not model outputs or a dataset."""
    data = json.loads((ROOT / "tests/fixtures/generated_contract.json").read_text(encoding="utf-8"))
    scene, initial, settings = data["scene"], data["initial_plan"], data["settings"]
    manifest = json.loads((ROOT / "tests/fixtures/assets.json").read_text(encoding="utf-8"))
    pricing = json.loads((ROOT / "configs/video.json").read_text(encoding="utf-8"))
    settings["model"] = pricing["model"]
    if kind == "umbrella":
        scene.update(scene_id="software_bus_stop", tone="affectionate", story="Lin returns Bo's umbrella; they walk to the bus.",
                     characters=[{"id": "lin", "name": "林"}, {"id": "bo", "name": "博"}],
                     beats=[{"id": "handover", "description": "Lin returns the umbrella."},
                            {"id": "depart", "description": "Both walk to the bus."}],
                     asset_ids=["lin_portrait", "bo_portrait"], min_duration_s=10, max_duration_s=10,
                     min_shot_duration_s=4, max_shot_duration_s=6, max_shots=2)
        initial.update(scene_id=scene["scene_id"], tone=scene["tone"],
                       scene_direction="A rainy bus stop at dawn. The parked bus is to the right.", shots=[
            {"shot_id": "return-umbrella", "beat_ids": ["handover"], "duration_s": 4,
             "direction": "Medium two-shot: Lin hands the closed umbrella to Bo, who takes it.",
             "visuals": [{"asset_id": a, "crop": "full"} for a in scene["asset_ids"]],
             "dialogue": [{"character_id": "lin", "text": "伞还给你。"}], "narration": "Lin returns the umbrella."},
            {"shot_id": "walk-to-bus", "beat_ids": ["depart"], "duration_s": 6,
             "direction": "Wide tracking shot: Lin and Bo walk together toward the parked bus.",
             "visuals": [{"asset_id": a, "crop": "full"} for a in scene["asset_ids"]],
             "dialogue": [], "narration": "Both walk toward the bus."}])
        for asset, character, binding in zip(manifest["assets"], scene["characters"], settings["characters"]):
            asset.update(asset_id=character["id"]+"_portrait", character_id=character["id"])
            binding.update(id=character["id"], asset_id=asset["asset_id"])
    for asset in manifest["assets"]:
        # This domain is inert: the compiler must never download the URL.
        asset["source_url"] = "https://example.invalid/" + asset["asset_id"] + ".png"
    plans = {c: deepcopy(initial) for c in CONDITIONS}
    speaker = scene["characters"][0]["id"]
    for condition, text in (("generic_review", "请你收好。"), ("moodcut", "下次下雨，我还陪你。")):
        plans[condition]["shots"][0]["dialogue"] = [{"character_id": speaker, "text": text}]
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr("socket.socket.connect", lambda *a, **k: pytest.fail("Offline tests must not connect"))
    return scene, initial, plans, manifest, settings, pricing


def compile_generated(case, **overrides):
    scene, initial, plans, manifest, settings, pricing = case
    return build_generated_video_bundle(scene, initial, plans, manifest, settings, project_root=ROOT,
        template_sha256=overrides.get("template_sha256", get_video_template_sha256()), pricing_config=pricing)


@pytest.mark.parametrize("inline", [False, True])
def test_heygen_compiler_keeps_common_controls_and_only_changes_dialogue(monkeypatch, inline):
    import base64
    from test_video_client import heygen_case
    scene, initial, plans, manifest, settings, _ = _generated_case("umbrella", monkeypatch)
    if inline:
        for asset in manifest["assets"]:
            asset["source_url"] = "data:image/png;base64," + base64.b64encode((ROOT/asset["path"]).read_bytes()).decode("ascii")
    pricing, _, _ = heygen_case()
    settings.update(model=pricing["model"], resolution="768p")
    scene.update(min_duration_s=11, max_duration_s=11)
    for plan in [initial, *plans.values()]:
        plan["shots"][0]["duration_s"] = 5
    bundle = compile_generated((scene, initial, plans, manifest, settings, pricing))
    common = []
    for condition in bundle["conditions"]:
        job = condition["jobs"][0]
        req = deepcopy(job["request"])
        assert job["quoted_cost_usd"] == "0.250"
        assert "generate_audio" not in req and req["duration"] == 5
        assert req["provider"]["options"]["heygen"]["parameters"]["prompt_enhancement"] == "disabled"
        assert "<Picture 1>" in req["prompt"] and "<Picture 2>" in req["prompt"]
        req["prompt"] = req["prompt"].split("\n\nDIALOGUE_JSON:")[0]
        common.append(req)
    assert common[0] == common[1] == common[2]
    if inline:
        assert all(r["image_url"]["url"].startswith("data:image/png;base64,") for r in common[0]["input_references"])


def test_heygen_compiler_rejects_inline_bytes_that_do_not_match_asset(monkeypatch):
    import base64
    from test_video_client import heygen_case
    scene, initial, plans, manifest, settings, _ = _generated_case("umbrella", monkeypatch)
    pricing, _, _ = heygen_case()
    settings.update(model=pricing["model"], resolution="768p")
    scene.update(min_duration_s=11, max_duration_s=11)
    for plan in [initial, *plans.values()]:
        plan["shots"][0]["duration_s"] = 5
    manifest["assets"][0]["source_url"] = "data:image/png;base64," + base64.b64encode(b"different bytes").decode("ascii")
    with pytest.raises(ValueError, match="Inline PNG"):
        compile_generated((scene, initial, plans, manifest, settings, pricing))


def prompt_parts(request):
    shared, dialogue = request["prompt"].split("SHARED_REQUIREMENTS_JSON:\n", 1)[1].split("\n\nDIALOGUE_JSON:\n", 1)
    return json.loads(shared), json.loads(dialogue)


def test_generated_requests_use_frozen_plan_and_only_dialogue_varies(generated_inputs):
    scene, initial, plans, manifest, settings, pricing = generated_inputs
    saved = deepcopy(generated_inputs)
    bundle = compile_generated(generated_inputs)
    assert saved == generated_inputs
    assert [c["condition"] for c in bundle["conditions"]] == list(CONDITIONS)
    assert bundle["kind"] == "generated_three_condition_bundle" and bundle["schema_version"] == "1.1"
    assert bundle["initial_plan_sha256"] == json_hash(initial)
    assert bundle["shared_generation_sha256"] == shared_generation_sha256(
        scene, initial, manifest, settings, template_sha256=get_video_template_sha256())
    for index, shot in enumerate(initial["shots"]):
        requests = []
        for condition in bundle["conditions"]:
            job = condition["jobs"][index]
            request = deepcopy(job["request"])
            assert set(request) == {"model", "prompt", "duration", "resolution", "aspect_ratio", "generate_audio", "seed", "input_references"}
            shared, spoken = prompt_parts(request)
            assert shared["scene_direction"] == initial["scene_direction"]
            assert shared["shot"] == {k: shot[k] for k in ("direction", "duration_s", "visuals")}
            assert spoken == plans[condition["condition"]]["shots"][index]["dialogue"]
            assert request["seed"] == settings["seed"] + index and request["duration"] == shot["duration_s"]
            assert request["generate_audio"] is True and len(request["input_references"]) == len(scene["asset_ids"])
            assert all(c not in request["prompt"] for c in CONDITIONS)
            assert job["request_sha256"] == json_hash(request)
            assert job["quoted_cost_usd"] == str(Decimal("0.10") * shot["duration_s"])
            assert "estimated_cost_usd" not in job and "provider_cost_usd" not in job
            request["prompt"] = shared
            requests.append(request)
        assert requests[0] == requests[1] == requests[2]
    assert compile_generated(generated_inputs) == bundle
    # Empty/unchanged shots compile to exactly equal full requests, not only equal settings.
    assert len({c["jobs"][-1]["request_sha256"] for c in bundle["conditions"]}) == 1
    if scene["scene_id"] == "software_bus_stop":
        assert sum(s["duration_s"] for s in initial["shots"]) == 10
        assert not any(token in str(bundle) for token in ("Anna", "Elsa", "letter", "s1", "s2", "s3"))
    bundle["settings"]["characters"][0]["voice"] = "changed output"
    assert generated_inputs == saved


@pytest.mark.parametrize("field", ["scene_direction", "direction", "duration_s", "visuals", "narration", "extension", "order"])
def test_generated_compiler_rejects_non_dialogue_changes(generated_inputs, field):
    candidate = generated_inputs[2]["moodcut"]
    if field == "scene_direction":
        candidate[field] += " Additional setting."
    elif field == "order":
        candidate["shots"].reverse()
    elif field == "duration_s":
        candidate["shots"][0][field] += 1
    elif field == "visuals":
        candidate["shots"][0][field][0]["crop"] = "center_close"
    else:
        candidate["shots"][0][field] = "Only this condition gets an enhancement."
    with pytest.raises(ValueError):
        compile_generated(generated_inputs)


@pytest.mark.parametrize("mutation", ["missing", "extra", "baseline", "speaker", "dialogue_control", "long",
    "old_header", "asset_hash", "binding", "audio", "seed", "setting_extra", "price_model", "price_unknown"])
def test_generated_compiler_rejects_invalid_input(generated_inputs, mutation):
    scene, initial, plans, manifest, settings, pricing = generated_inputs
    if mutation == "missing":
        del plans["generic_review"]
    elif mutation == "extra":
        plans["dialogue_revision"] = deepcopy(initial)
    elif mutation == "baseline":
        plans["baseline"]["shots"][0]["dialogue"] = []
    elif mutation == "speaker":
        plans["moodcut"]["shots"][0]["dialogue"][0]["character_id"] = "unknown"
    elif mutation == "dialogue_control":
        plans["moodcut"]["shots"][0]["dialogue"][0]["voice"] = "Special enhancement"
    elif mutation == "long":
        plans["moodcut"]["shots"][0]["dialogue"][0]["text"] = "长" * 500
    elif mutation == "old_header":
        initial["schema_version"] = "1.0"
    elif mutation == "asset_hash":
        manifest["assets"][0]["sha256"] = "0" * 64
    elif mutation == "binding":
        settings["characters"][0]["asset_id"] = settings["characters"][1]["asset_id"]
    elif mutation == "audio":
        settings["generate_audio"] = False
    elif mutation == "seed":
        settings["seed"] = True
    elif mutation == "setting_extra":
        settings["shots"] = pricing["shots"]
    elif mutation == "price_model":
        pricing["model"] = "different/model"
    else:
        pricing.pop("price_per_second_usd")
    with pytest.raises(ValueError):
        compile_generated(generated_inputs)


@pytest.mark.parametrize("url", [None, "file:///private.png", "https://localhost/a.png", "http://example.com/a.png"])
def test_generated_references_require_public_https_without_fetching(generated_inputs, url):
    generated_inputs[3]["assets"][0]["source_url"] = url
    with pytest.raises(ValueError, match="Reference"):
        compile_generated(generated_inputs)


def test_generated_template_is_actual_content_not_a_declared_hash(generated_inputs, tmp_path, monkeypatch):
    import hashlib
    from moodcut import video_generation
    path = video_generation._GENERATED_TEMPLATE
    expected = hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
    assert get_video_template_sha256() == expected
    with pytest.raises(ValueError, match="actual generated video template"):
        compile_generated(generated_inputs, template_sha256="a" * 64)
    modified = tmp_path / "template.txt"
    modified.write_text(path.read_text(encoding="utf-8") + "\nChanged common template.\n", encoding="utf-8")
    monkeypatch.setattr(video_generation, "_GENERATED_TEMPLATE", modified)
    assert get_video_template_sha256() != expected
    with pytest.raises(ValueError, match="actual generated video template"):
        compile_generated(generated_inputs, template_sha256=expected)
    bundle = compile_generated(generated_inputs)
    assert bundle["template_sha256"] == get_video_template_sha256()


def test_generated_seedance_uses_existing_local_quote_without_changing_prompt(generated_inputs):
    from decimal import Decimal
    original = compile_generated(generated_inputs)
    settings, pricing = generated_inputs[-2:]
    settings["model"] = pricing["model"] = "bytedance/seedance-2.0-mini"
    pricing.pop("price_per_second_usd")
    pricing["price_per_million_video_tokens_usd"] = "3.50"
    changed = compile_generated(generated_inputs)
    assert changed["shared_generation_sha256"] != original["shared_generation_sha256"]
    for before, after in zip(original["conditions"], changed["conditions"]):
        for a, b in zip(before["jobs"], after["jobs"]):
            assert a["request"]["prompt"] == b["request"]["prompt"]
            assert a["request"]["input_references"] == b["request"]["input_references"]
            assert Decimal(b["quoted_cost_usd"]) == Decimal("0.0756") * b["request"]["duration"]


def test_generated_does_not_consume_legacy_letter_recipe(generated_inputs):
    before = compile_generated(generated_inputs)
    pricing = generated_inputs[-1]
    for key in list(pricing):
        if key not in {"model", "resolution", "aspect_ratio", "price_per_second_usd"}:
            del pricing[key]
    assert compile_generated(generated_inputs) == before


def test_generated_all_reference_images_map_in_shared_order(generated_inputs):
    scene, _initial, _plans, manifest, _settings, _pricing = generated_inputs
    # An extra selected image of the same character still receives an explicit
    # character mapping; manifest storage order must not change the request.
    extra = deepcopy(manifest["assets"][0])
    extra.update(asset_id="software_secondary_view", source_url="https://example.invalid/secondary.png")
    scene["asset_ids"].append(extra["asset_id"])
    manifest["assets"].append(extra)
    before = compile_generated(generated_inputs)
    manifest["assets"].reverse()
    after = compile_generated(generated_inputs)
    assert before == after
    request = after["conditions"][0]["jobs"][0]["request"]
    shared, _spoken = prompt_parts(request)
    assert [r["asset_id"] for r in shared["reference_images"]] == scene["asset_ids"]
    assert shared["reference_images"][-1] == {"reference_index": 3, "asset_id": extra["asset_id"],
        "character_id": extra["character_id"], "name": scene["characters"][0]["name"], "primary_identity": False}
    assert request["input_references"][-1]["image_url"]["url"] == extra["source_url"]


def test_generated_valid_plan_with_unsupported_provider_duration_is_rejected(generated_inputs):
    scene, initial, plans, _manifest, _settings, _pricing = generated_inputs
    scene.update(max_shot_duration_s=11, max_duration_s=40)
    initial["shots"][0]["duration_s"] = 11
    for plan in plans.values():
        plan["shots"][0]["duration_s"] = 11
    with pytest.raises(ValueError, match="Unsupported Wan"):
        compile_generated(generated_inputs)


def script_source(case, output):
    """Actual P1/P2/P3 with FakeClient JSON; no business-function doubles."""
    from moodcut.client import FakeClient
    from moodcut.pipeline import run_experiment
    scene, initial, plans, manifest, settings, _pricing = case
    responses = [{"scene_id": scene["scene_id"], "tone": scene["tone"],
                  "beat_order": [b["id"] for b in scene["beats"]], "approach": "Software planning only."},
                 {"scene_id": scene["scene_id"], "scene_direction": initial["scene_direction"], "segments": [
                     {"beat_ids": s["beat_ids"], "direction": s["direction"], "duration_s": s["duration_s"],
                      "description": s["narration"]} for s in initial["shots"]]}, initial]
    shot_id = initial["shots"][0]["shot_id"]
    for mode in CONDITIONS[1:]:
        responses += [{"schema_version": "1.0", "scene_id": scene["scene_id"], "mode": mode, "issues": [
            {"issue_id": "software-issue", "shot_id": shot_id, "dimension": "naturalness", "severity": "minor",
             "evidence": "Hand-written software concern.", "suggestion": "Revise the dialogue only."}]},
            {"schema_version": "1.0", "scene_id": scene["scene_id"], "edits": [
                {"issue_id": "software-issue", "shot_id": shot_id, "set": {"dialogue": plans[mode]["shots"][0]["dialogue"]}}]},
            {"scene_id": scene["scene_id"], "resolved_issue_ids": ["software-issue"], "unresolved_issue_ids": [], "new_concerns": []}]
    client = FakeClient(responses)
    block = run_experiment(scene, manifest, client, out_dir=output, project_root=ROOT,
        output_mode="generated", generation_settings=settings, template_sha256=get_video_template_sha256())
    assert block["status"] == "prepared" and block["planning"]["calls"] == 3 and len(client.calls) == 9
    assert [r["review_calls"] for r in block["runs"]] == [0, 3, 3]
    return block


def test_actual_planning_review_compiler_cli_all_and_single_shot(generated_inputs, tmp_path, monkeypatch):
    from moodcut import client, video_client
    from moodcut.__main__ import main
    from moodcut.pipeline import read_json
    monkeypatch.setattr(client.OpenRouterClient, "from_env", lambda *a, **k: pytest.fail("No text client"))
    monkeypatch.setattr(video_client, "OpenRouterVideoClient", lambda *a, **k: pytest.fail("No video client"))
    monkeypatch.setattr(video_client, "fetch_video_models", lambda *a, **k: pytest.fail("No catalogue"))
    source = tmp_path / "scripts"
    block = script_source(generated_inputs, source)
    before = {p: p.read_bytes() for p in source.rglob("*.json")}
    full_ids = [s["shot_id"] for s in generated_inputs[1]["shots"]]
    bundles = []
    for selection in (None, full_ids[-1]):
        output = tmp_path / ("all" if selection is None else "selected")
        args = ["run", "--project-root", str(ROOT), "--output-mode", "generated", "--source-block", str(source),
                "--pricing-config", "configs/video.json", "--output", str(output)]
        if selection is not None:
            args += ["--shot-id", selection]
        assert main(args) == 0
        prepared = read_json(output / "preparation.json")
        bundle = read_json(output / "bundle.json")
        bundles.append(bundle)
        assert prepared["status"] == "prepared_offline" and prepared["comparison_status"] == "not_checked"
        assert prepared["shared_generation_sha256"] == block["shared_generation_sha256"]
        assert prepared["calls"] == prepared["generation_posts"] == prepared["video_get_calls"] == prepared["real_http_calls"] == 0
        assert prepared["provider_cost_usd"] == 0.0 and prepared["video_path"] is None
        assert not list(output.rglob("*.mp4"))
        assert read_json(output / "source_block.json") == block
        assert read_json(output / "source_inputs.json")["plans"] == generated_inputs[2]
        for condition in bundle["conditions"]:
            assert condition["final_plan_sha256"] == json_hash(generated_inputs[2][condition["condition"]])
            for job in condition["jobs"]:
                assert job["request"]["seed"] == generated_inputs[4]["seed"] + job["shot_index"]
                assert_dialogue_only_revision(generated_inputs[1], generated_inputs[2][condition["condition"]])
        assert {p: p.read_bytes() for p in source.rglob("*.json")} == before
        assert main(args) == 1  # Existing artifacts stay intact.
    for full, selected in zip(*[b["conditions"] for b in bundles]):
        assert selected["jobs"] == [full["jobs"][-1]]


def test_actual_cli_refuses_template_changed_after_source_freeze(generated_inputs, tmp_path, monkeypatch):
    from moodcut import video_generation
    from moodcut.__main__ import main
    source = tmp_path / "scripts"
    script_source(generated_inputs, source)
    before = {p: p.read_bytes() for p in source.rglob("*.json")}
    changed = tmp_path / "changed-template.txt"
    changed.write_text(video_generation._GENERATED_TEMPLATE.read_text(encoding="utf-8") + "\nNew template\n", encoding="utf-8")
    monkeypatch.setattr(video_generation, "_GENERATED_TEMPLATE", changed)
    output = tmp_path / "requests"
    assert main(["run", "--project-root", str(ROOT), "--output-mode", "generated", "--source-block", str(source),
                 "--pricing-config", "configs/video.json", "--output", str(output)]) == 1
    assert not output.exists()
    assert {p: p.read_bytes() for p in source.rglob("*.json")} == before


def test_actual_compiler_requests_reuse_existing_records_accounting(generated_inputs, tmp_path):
    """Synthetic moving/sine media, a hand-written receipt; no HTTP generation."""
    from moodcut.pipeline import prepare_generated_run, assemble_generated_records, write_json
    source = tmp_path / "scripts"
    block = script_source(generated_inputs, source)
    shot_id = generated_inputs[1]["shots"][-1]["shot_id"]
    prep = tmp_path / "prepared"
    prepare_generated_run(source, out_dir=prep, project_root=ROOT, shot_id=shot_id, pricing_config=ROOT / "configs/video.json")
    bundle = json.loads((prep / "bundle.json").read_text(encoding="utf-8"))
    jobs = [c["jobs"][0] for c in bundle["conditions"]]
    assert len({j["request_sha256"] for j in jobs}) == 1
    media = tmp_path / "synthetic-moving-sine.mp4"
    duration = jobs[0]["request"]["duration"]
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", f"testsrc2=size=160x90:rate=24:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}", "-c:v", "libx264", "-c:a", "aac",
        "-shortest", str(media)], check=True, capture_output=True, timeout=30)
    receipt = tmp_path / "synthetic-receipt.json"
    write_json(receipt, {"schema_version": "1.1", "model": jobs[0]["request"]["model"], "status": "downloaded",
        "job_id": "synthetic-not-a-real-task", "request_sha256": jobs[0]["request_sha256"],
        "estimated_cost_usd": jobs[0]["quoted_cost_usd"], "provider_cost_usd": "0.23", "video_path": str(media),
        "post_attempts": 1, "poll_attempts": 2, "download_attempts": 1, "download_redirect_attempts": 0})
    evidence = tmp_path / "synthetic-evidence.json"
    write_json(evidence, {"schema_version": "1.1", "block_id": block["block_id"], "provenance": "Software evidence only",
        "conditions": [{"condition": c, "jobs": [{"shot_id": shot_id, **(
            {"receipt_path": str(receipt)} if c == "baseline" else
            {"reused_from": {"run_id": block["runs"][0]["run_id"], "shot_id": shot_id}})}]} for c in CONDITIONS]})
    result = assemble_generated_records(prep, evidence=evidence, out_dir=tmp_path / "records",
        pricing_config=ROOT / "configs/video.json", project_root=ROOT)
    assert result["accounting"]["generation_posts"] == 1
    assert result["accounting"]["provider_cost_usd"] == .23
    assert result["assembly_activity"]["real_http_calls"] == 0
    assert [r["generation_posts"] for r in result["runs"]] == [1, 0, 0]
    assert [r["provider_cost_usd"] for r in result["runs"]] == [.23, 0, 0]
    assert all(r["run_status"] == "completed" and r["comparison_status"] == "not_checked" for r in result["runs"])


@pytest.fixture
def inspection_inputs(tmp_path, monkeypatch):
    """Actual P1/P2/P3/P4 requests + synthetic moving/sine files and receipts."""
    from moodcut import client, video_client
    from moodcut.pipeline import prepare_generated_run, read_json, write_json
    case = _generated_case('umbrella', monkeypatch)
    scene, initial, plans = case[:3]
    scene.update(min_duration_s=4, max_duration_s=4, min_shot_duration_s=2, max_shot_duration_s=2)
    for plan in [initial, *plans.values()]:
        for shot in plan['shots']:
            shot['duration_s'] = 2
    # Deliberately awkward IDs exercise safe file naming and escaped HTML/CSV.
    for plan in [initial, *plans.values()]:
        plan['shots'][0]['shot_id'] = '=1+1<script>alert(1)</script>'
    for module, name in ((video_client, 'OpenRouterVideoClient'), (video_client, 'fetch_video_models'),
                         (client.OpenRouterClient, 'from_env')):
        monkeypatch.setattr(module, name, lambda *a, **k: pytest.fail('No clients/catalogue/network during inspection'))
    source = tmp_path / 'scripts'
    block = script_source(case, source)
    prep = tmp_path / 'prepared'
    prepare_generated_run(source, out_dir=prep, project_root=ROOT, pricing_config=ROOT / 'configs/video.json')
    bundle = read_json(prep / 'bundle.json')
    media = []
    for index in range(2):
        path = tmp_path / f'synthetic-pattern-{index}.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'testsrc2=size=160x90:rate=24:duration=2',
            '-f', 'lavfi', '-i', f'sine=frequency={440+index*220}:duration=2', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-shortest', str(path)], check=True, capture_output=True, timeout=30)
        media.append(path)
    supplied = {'schema_version': '1.1', 'block_id': block['block_id'], 'provenance': 'Synthetic software media/receipts; no model output or actual charges.',
                'conditions': []}
    for condition_index, condition in enumerate(bundle['conditions']):
        entries = []
        for index, job in enumerate(condition['jobs']):
            if condition_index and index == 1:
                entries.append({'shot_id': job['shot_id'], 'reused_from': {'run_id': block['runs'][0]['run_id'], 'shot_id': job['shot_id']}})
                continue
            receipt = tmp_path / f'receipt-{condition_index}-{index}.json'
            write_json(receipt, {'schema_version': '1.1', 'model': job['request']['model'], 'status': 'downloaded',
                'job_id': f'synthetic-job-{condition_index}-{index}', 'request_sha256': job['request_sha256'],
                'estimated_cost_usd': job['quoted_cost_usd'], 'provider_cost_usd': '0.07', 'video_path': media[index].name,
                'post_attempts': 1, 'poll_attempts': 2, 'download_attempts': 1, 'download_redirect_attempts': 0})
            entries.append({'shot_id': job['shot_id'], 'receipt_path': receipt.name})
        supplied['conditions'].append({'condition': condition['condition'], 'jobs': entries})
    evidence = tmp_path / 'evidence.json'
    write_json(evidence, supplied)
    return {'case': case, 'source': source, 'prep': prep, 'block': block, 'bundle': bundle, 'media': media,
            'evidence': evidence, 'supplied': supplied, 'output': tmp_path / 'inspection'}


def inspect_local(case, **options):
    from moodcut.video_generation import inspect_generated_video
    return inspect_generated_video(case['prep'], evidence=case['evidence'], out_dir=options.get('out_dir', case['output']),
        pricing_config=ROOT / 'configs/video.json', project_root=ROOT, media_origin=options.get('media_origin', 'synthetic'))


def test_inspection_binds_real_local_media_and_leaves_subjective_cells_blank(inspection_inputs):
    import csv
    from PIL import Image, ImageChops
    from moodcut.pipeline import read_json
    case = inspection_inputs
    original = {p: p.read_bytes() for p in [*case['source'].rglob('*.json'), *case['prep'].glob('*.json'),
                case['evidence'], *case['evidence'].parent.glob('receipt-*.json'), *case['media']]}
    result = inspect_local(case)
    output = case['output']
    assert result['status'] == 'ready_requires_manual_inspection' and result['comparison_status'] == 'not_checked'
    assert result['media_origin'] == 'synthetic' and result['speech_and_visual_quality'] == 'not_reviewed'
    assert all(v == 0 for v in result['inspection_activity'].values())
    records = read_json(output / 'records/block.json')
    assert records['status'] == 'completed' and records['accounting']['provider_cost_usd'] == .28
    assert records['accounting']['generation_posts'] == 4 and records['accounting']['planning_counted_once'] is True
    assert records['accounting'] == read_json(output / 'preflight_records/block.json')['accounting']
    assert [r['generation_posts'] for r in records['runs']] == [2, 1, 1]
    for index, row in enumerate(result['conditions']):
        folder = output / row['condition']
        check = read_json(folder / 'media_check.json')
        assert check['video_path'] == 'film.mp4' and check['sha256'] == hashlib.sha256((folder/'film.mp4').read_bytes()).hexdigest()
        expected = [{'shot_id': job['shot_id'], 'request_sha256': job['request_sha256'],
                     'sha256': hashlib.sha256(case['media'][j].read_bytes()).hexdigest()}
                    for j, job in enumerate(case['bundle']['conditions'][index]['jobs'])]
        assert check['source_clips'] == expected
        assert check['selected_shot_ids'] == result['selected_shot_ids']
        assert check['shared_generation_sha256'] == case['block']['shared_generation_sha256']
        assert check['speech_and_visual_quality'] == 'requires_manual_inspection'
        assert records['runs'][index]['media_check']['sha256'] == check['sha256']
        probe = read_json(folder / 'ffprobe.json')
        assert probe['film']['has_audio'] is True and abs(probe['film']['duration_s']-4) < .5
        assert {'video', 'audio'} <= {s['codec_type'] for s in probe['film']['ffprobe']['streams']}
        assert len(probe['clips']) == 2 and len(check['frame_samples']) == 6
        assert (folder / 'contact_sheet.png').is_file()
        frames = [Image.open(folder / sample['path']).convert('RGB') for sample in check['frame_samples'][:3]]
        assert ImageChops.difference(frames[0], frames[2]).getbbox() is not None  # Synthetic motion really changes pixels.
    checklist = read_json(output / 'manual_checks.json')
    assert checklist['status'] == 'not_reviewed' and len(checklist['items']) == 6
    for item in checklist['items']:
        assert all(item[k] is None for k in ('character_action','dialogue_speaker','audio_lipsync','continuity'))
        assert item['notes'] == '' and item['film_sha256']
    with (output/'manual_checks.csv').open(encoding='utf-8-sig', newline='') as stream:
        items = list(csv.DictReader(stream))
    assert items[0]['shot_id'].startswith("'=1+1")
    assert all(item[k] == '' for item in items for k in ('character_action','dialogue_speaker','audio_lipsync','continuity','notes'))
    page = (output/'index.html').read_text(encoding='utf-8')
    assert 'synthetic' in page and '不用于盲评' in page and '不是语音识别结果' in page
    assert '<script>alert(1)</script>' not in page and '&lt;script&gt;' in page
    assert page.count('<video controls') == 3
    assert all(p.read_bytes() == content for p, content in original.items())
    with pytest.raises(FileExistsError):
        inspect_local(case)


@pytest.mark.parametrize('problem', ['silent', 'duration', 'failed_unknown', 'missing_receipt', 'invalid_pointer', 'unsubmitted'])
def test_inspection_preserves_failed_or_missing_media_and_unknown_costs(inspection_inputs, problem):
    from moodcut.pipeline import read_json, write_json
    case = inspection_inputs
    receipt = case['evidence'].parent / 'receipt-0-0.json'
    data = read_json(receipt)
    if problem in ('silent', 'duration'):
        invalid = case['evidence'].parent / 'synthetic-invalid.mp4'
        args = ['ffmpeg','-v','error','-i',str(case['media'][0])]
        args += ['-an','-c:v','copy'] if problem == 'silent' else ['-t','0.4','-c','copy']
        subprocess.run([*args,str(invalid)],check=True,capture_output=True,timeout=30)
        data['video_path'] = invalid.name
    elif problem == 'failed_unknown':
        data.update(status='failed', video_path=None, provider_cost_usd=None)
        data.pop('download_attempts')
    elif problem == 'missing_receipt':
        receipt.unlink()
    elif problem == 'invalid_pointer':
        case['supplied']['conditions'][0]['jobs'][0]['receipt_path'] = 123
    else:
        case['supplied']['conditions'][0]['jobs'] = []
        # A reuse of an unsubmitted origin is also invalid and must not generate a film.
    if problem not in ('missing_receipt','invalid_pointer','unsubmitted'):
        receipt.write_text(json.dumps(data),encoding='utf-8')
    case['evidence'].write_text(json.dumps(case['supplied']),encoding='utf-8')
    result = inspect_local(case)
    assert result['status'] == 'failed'
    assert result['conditions'][0]['status'] in ('failed','not_ready')
    assert not (case['output']/'baseline/film.mp4').exists()
    records = read_json(case['output']/'records/block.json')
    if problem in ('failed_unknown','missing_receipt','invalid_pointer'):
        assert records['accounting']['provider_cost_usd'] is None
    else:
        assert records['runs'][0]['provider_cost_usd'] == (.14 if problem != 'unsubmitted' else 0)
    assert (case['output']/'index.html').is_file()
    assert result['inspection_activity']['real_http_calls'] == 0


def test_inspection_cli_and_unsubmitted_records_are_explicit(inspection_inputs, monkeypatch):
    import importlib.util
    from moodcut.pipeline import write_json, read_json
    case = inspection_inputs
    spec = importlib.util.spec_from_file_location('inspect_video_command', ROOT/'scripts/inspect_generated_video.py')
    command = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(command)
    for condition in case['supplied']['conditions']:
        condition['jobs'] = []
    case['evidence'].write_text(json.dumps(case['supplied']),encoding='utf-8')
    monkeypatch.chdir(case['evidence'].parent)
    args = ['--project-root',str(ROOT),'--preparation',str(case['prep']),'--evidence',str(case['evidence']),
            '--output',str(case['output']),'--media-origin','synthetic']
    assert command.main(args) == 1
    result = read_json(case['output']/'inspection.json')
    assert result['status'] == 'incomplete' and result['comparison_status'] == 'not_checked'
    assert not list(case['output'].rglob('*.mp4'))
    assert read_json(case['output']/'records/block.json')['accounting']['generation_posts'] == 0
    assert command.main(args) == 1
    with pytest.raises(SystemExit):
        command.main([*args, '--allow-paid'])


def test_inspection_rejects_tampered_preparation_before_output(inspection_inputs):
    from moodcut.pipeline import read_json, write_json
    case = inspection_inputs
    bundle = read_json(case['prep']/'bundle.json')
    bundle['conditions'][0]['jobs'][0]['request']['seed'] += 1
    (case['prep']/'bundle.json').write_text(json.dumps(bundle),encoding='utf-8')
    with pytest.raises(ValueError, match='hash mismatch'):
        inspect_local(case)
    assert not case['output'].exists()


def test_inspection_reuses_validated_existing_assembly_without_reencoding(inspection_inputs, monkeypatch):
    from moodcut import video_generation
    case = inspection_inputs
    first = inspect_local(case)
    # Reuse a bound local film, never regenerate or silently repair it.
    case['evidence'] = case['output'] / 'evidence.json'
    monkeypatch.setattr(video_generation, 'assemble_generated_clips', lambda *a, **k: pytest.fail('Existing assembly should be copied'))
    second = inspect_local(case, out_dir=case['output'].parent / 'inspection-copy', media_origin='provided_local')
    assert second['status'] == 'ready_requires_manual_inspection'
    assert [r['sha256'] for r in second['conditions']] == [r['sha256'] for r in first['conditions']]
    assert second['media_origin'] == 'provided_local'


def test_inspection_detects_media_changed_during_assembly(inspection_inputs, monkeypatch):
    from moodcut import video_generation
    from moodcut.pipeline import read_json
    case = inspection_inputs
    original = video_generation.assemble_generated_clips
    def mutate_after_assembly(*args, **kwargs):
        result = original(*args, **kwargs)
        with case['media'][0].open('ab') as stream:
            stream.write(b'changed-after-preflight')
        return result
    monkeypatch.setattr(video_generation, 'assemble_generated_clips', mutate_after_assembly)
    result = inspect_local(case)
    assert result['status'] == 'failed' and result['comparison_status'] == 'ineligible'
    assert any('changed during inspection' in e for e in result['conditions'][0]['errors'])
    assert '<video controls' not in (case['output']/'index.html').read_text(encoding='utf-8')
    records = read_json(case['output']/'records/block.json')
    assert records['accounting']['provider_cost_usd'] == .28
    assert all(r['run_status'] == 'failed' for r in records['runs'])


def test_inspection_valid_media_retains_unknown_legacy_bill(inspection_inputs):
    from moodcut.pipeline import read_json
    case = inspection_inputs
    receipt = case['evidence'].parent / 'receipt-0-0.json'
    data = read_json(receipt)
    data.update(schema_version='1.0', provider_cost_usd=None)
    data.pop('download_attempts')
    data.pop('download_redirect_attempts')
    receipt.write_text(json.dumps(data),encoding='utf-8')
    result = inspect_local(case)
    assert result['status'] == 'ready_requires_manual_inspection'
    records = read_json(case['output']/'records/block.json')
    assert records['accounting']['provider_cost_usd'] is None
    assert records['accounting']['real_http_calls'] is None
    assert records['accounting']['known_subtotals']['provider_cost_usd'] == .21
    assert records['runs'][0]['generation_jobs'][0]['missing_counters'] == ['download_attempts','download_redirect_attempts']
    assert all(r['run_status'] == 'completed' and r['comparison_status'] == 'not_checked' for r in records['runs'])


def test_inspection_cli_single_shot_retains_full_plan_identity(inspection_inputs):
    import importlib.util
    from moodcut.pipeline import prepare_generated_run, read_json
    case = inspection_inputs
    prep = case['prep'].parent / 'one-prepared'
    prepare_generated_run(case['source'], out_dir=prep, project_root=ROOT, shot_id='walk-to-bus',
                          pricing_config=ROOT/'configs/video.json')
    for condition in case['supplied']['conditions']:
        condition['jobs'] = [j for j in condition['jobs'] if j['shot_id'] == 'walk-to-bus']
    case['evidence'].write_text(json.dumps(case['supplied']),encoding='utf-8')
    spec = importlib.util.spec_from_file_location('inspect_single_command',ROOT/'scripts/inspect_generated_video.py')
    command = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(command)
    assert command.main(['--project-root',str(ROOT),'--preparation',str(prep),'--evidence',str(case['evidence']),
                         '--output',str(case['output']),'--media-origin','synthetic']) == 0
    result = read_json(case['output']/'inspection.json')
    assert result['selected_shot_ids'] == ['walk-to-bus']
    assert result['initial_plan_sha256'] == case['block']['initial_plan_sha256']
    assert result['shared_generation_sha256'] == case['block']['shared_generation_sha256']
    check = read_json(case['output']/'baseline/media_check.json')
    assert abs(check['duration_s']-2) < .5 and len(check['source_clips']) == 1
    assert read_json(case['output']/'records/block.json')['accounting']['provider_cost_usd'] == .07


def test_inspection_requires_explicit_media_origin(tmp_path):
    from moodcut.video_generation import inspect_generated_video
    with pytest.raises(ValueError, match='media_origin'):
        inspect_generated_video('missing', evidence='missing', out_dir=tmp_path/'out', pricing_config='missing',
                                media_origin='generated-and-passed')
    assert not (tmp_path/'out').exists()


def test_inspection_final_receipt_recheck_can_downgrade_readiness(inspection_inputs, monkeypatch):
    from moodcut import video_generation
    from moodcut.pipeline import read_json
    case = inspection_inputs
    original = video_generation._inspection_frames
    def change_receipt(*args, **kwargs):
        result = original(*args, **kwargs)
        receipt = case['evidence'].parent/'receipt-0-0.json'
        data = read_json(receipt)
        data['status'] = 'pending'
        receipt.write_text(json.dumps(data),encoding='utf-8')
        return result
    monkeypatch.setattr(video_generation, '_inspection_frames', change_receipt)
    result = inspect_local(case)
    assert result['status'] == 'incomplete' and result['conditions'][0]['status'] == 'not_ready'
    assert 'completion changed' in result['conditions'][0]['errors'][0]
    assert read_json(case['output']/'records/block.json')['runs'][0]['run_status'] == 'prepared'
    assert (case['output']/'index.html').read_text(encoding='utf-8').count('<video controls') == 2
