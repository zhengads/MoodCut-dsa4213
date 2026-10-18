"""Three bounded MovieAgent-inspired text stages using the public LLM client.

The stage order is a method reference, implemented independently for MoodCut's
animatic and generated schemas. No upstream code, GPU tools or inference SDK is imported.
"""

from copy import deepcopy
import hashlib
from importlib.resources import files
import json
import logging

from . import validation
from .contracts import OUTPUT_MODES, _json_copy, json_hash


STAGES = ("director", "scene", "shot")
MAX_OUTPUT_TOKENS = {"director": 1024, "scene": 2048, "shot": 4096}
TRACE_LOGGER = logging.getLogger("moodcut.planning.trace")


class PlanningError(ValueError):
    """Failed planning with parsed raw responses available for run artifacts."""

    def __init__(self, stage, errors, raw_responses):
        self.stage = stage
        self.errors = list(errors)
        self.raw_responses = deepcopy(raw_responses)
        super().__init__(f"Planning failed at {stage}: " + "; ".join(self.errors))


def _prompts(*, output_mode="animatic"):
    if not isinstance(output_mode, str) or output_mode not in OUTPUT_MODES:
        raise ValueError("output_mode must be animatic or generated")
    prefix = "planning_generated" if output_mode == "generated" else "planning"
    return {stage: files("moodcut").joinpath("prompts", f"{prefix}_{stage}.txt")
            .read_text(encoding="utf-8") for stage in STAGES}


def get_planning_prompt_hashes(*, output_mode="animatic") -> dict:
    """Hash exact shipped prompt text for persisted block-cache identity."""
    return {stage: hashlib.sha256(text.encode("utf-8")).hexdigest()
            for stage, text in _prompts(output_mode=output_mode).items()}


def _check_stage(stage, response, scene, *, output_mode="animatic"):
    if not isinstance(response, dict):
        raise ValueError("response must be a JSON object")
    json.dumps(response, allow_nan=False)
    if response.get("scene_id") != scene["scene_id"]:
        raise ValueError("scene_id does not match input")
    expected = [beat["id"] for beat in scene["beats"]]
    if stage == "director":
        if response.get("tone") != scene["tone"]:
            raise ValueError("director tone does not match input")
        if response.get("beat_order") != expected:
            raise ValueError("director beat_order must preserve all input beat IDs in order")
        if not isinstance(response.get("approach"), str) or not response["approach"].strip():
            raise ValueError("director approach must be a non-empty string")
    elif stage == "scene":
        segments = response.get("segments")
        if not isinstance(segments, list) or not 1 <= len(segments) <= scene["max_shots"]:
            raise ValueError("scene segments must fit the requested shot limit")
        ordered = []
        for segment in segments:
            if (not isinstance(segment, dict) or not isinstance(segment.get("beat_ids"), list)
                    or not segment["beat_ids"] or not isinstance(segment.get("description"), str)
                    or not segment["description"].strip()):
                raise ValueError("scene segment requires beat_ids and non-empty description")
            ordered.extend(segment["beat_ids"])
        if ordered != expected:
            raise ValueError("scene segments must preserve all input beat IDs in order")
        if output_mode == "generated":
            if not isinstance(response.get("scene_direction"), str) or not response["scene_direction"].strip():
                raise ValueError("scene requires a non-empty scene_direction")
            total = 0
            for segment in segments:
                if not isinstance(segment.get("direction"), str) or not segment["direction"].strip():
                    raise ValueError("scene segment requires a non-empty direction")
                duration = segment.get("duration_s")
                if (type(duration) is not int
                        or not scene["min_shot_duration_s"] <= duration <= scene["max_shot_duration_s"]):
                    raise ValueError("scene segment duration_s violates integer shot limits")
                total += duration
            if not scene["min_duration_s"] <= total <= scene["max_duration_s"]:
                raise ValueError("scene segment total duration violates scene limits")


def normalize_plan(response: dict, scene: dict, *, output_mode="animatic") -> dict:
    """Unwrap equivalent shot-list envelopes; never repair IDs or drop shots.

    Canonical top-level ShotPlan, {shots: [...]}, {plan: {...}} and a single
    {scenes: [{shots: [...]}]} envelope are accepted. Multi-scene generation is
    outside the one-scene contract and fails rather than silently truncating.
    Generated envelopes must explicitly retain their 1.1/generated header;
    unknown JSON extension fields survive rather than being silently projected.
    """
    if not isinstance(output_mode, str) or output_mode not in OUTPUT_MODES:
        raise ValueError("output_mode must be animatic or generated")
    if not isinstance(response, dict):
        raise ValueError("shot response must be an object")
    generated = output_mode == "generated"
    data = _json_copy(response) if generated else deepcopy(response)
    if "plan" in data:
        if len(data) != 1 or not isinstance(data["plan"], dict):
            raise ValueError("plan wrapper must contain exactly one plan object")
        data = data["plan"]
    if "scenes" in data:
        if not generated and set(data) - {"scenes", "scene_id", "tone", "schema_version"}:
            raise ValueError("ambiguous scene envelope")
        scenes = data.pop("scenes")
        if not isinstance(scenes, list) or len(scenes) != 1 or not isinstance(scenes[0], dict):
            raise ValueError("exactly one scene must be returned")
        inner = scenes[0]
        for key in set(data) & set(inner):
            same = json_hash(data[key]) == json_hash(inner[key]) if generated else data[key] == inner[key]
            if not same:
                raise ValueError(f"conflicting scene metadata: {key}")
        data.update(inner)
    if generated:
        # No implicit upgrade from a 1.0/partial result. The shared validator
        # checks headers, directions, bounds, references and required coverage.
        return data
    if set(data) - {"schema_version", "scene_id", "tone", "shots"}:
        raise ValueError("unknown fields in shot plan envelope")
    for field, default in (("schema_version", "1.0"), ("scene_id", scene["scene_id"]),
                           ("tone", scene["tone"])):
        data.setdefault(field, default)
    return data


def make_plan_with_trace(scene: dict, manifest: dict, client, *, project_root=None,
                         output_mode="animatic") -> dict:
    """Return plan, parsed responses and prompt hashes, including no hidden retries."""
    raw = {}
    stage = "preflight"
    kwargs = {"project_root": project_root} if project_root is not None else {}
    kwargs["output_mode"] = output_mode
    try:
        errors = validation.validate_scene(scene, manifest, **kwargs)
        if errors:
            raise ValueError("; ".join(errors))
        scene, manifest = deepcopy(scene), deepcopy(manifest)
        prompts = _prompts(output_mode=output_mode)
        for stage in STAGES:
            payload = {"scene": scene, "manifest": manifest, "prior_responses": raw}
            if output_mode == "generated":
                payload["output_mode"] = output_mode
            user = json.dumps(payload, ensure_ascii=False, allow_nan=False)
            response = client.complete_json(stage=stage, system=prompts[stage], user=user,
                                            max_output_tokens=MAX_OUTPUT_TOKENS[stage])
            raw[stage] = deepcopy(response)
            if output_mode == "generated":
                _json_copy(response)
            TRACE_LOGGER.info(json.dumps({"stage": stage, "response": response},
                                         ensure_ascii=False, allow_nan=False))
            if stage != "shot":
                _check_stage(stage, response, scene, output_mode=output_mode)
        plan = normalize_plan(raw["shot"], scene, output_mode=output_mode)
        errors = validation.validate_plan(scene, plan, manifest, **kwargs)
        if errors:
            raise ValueError("; ".join(errors))
        if output_mode == "generated":
            staged = raw["scene"]
            if plan["scene_direction"] != staged["scene_direction"] or len(plan["shots"]) != len(staged["segments"]):
                raise ValueError("shot plan must retain the staged scene direction and segment count")
            for shot, segment in zip(plan["shots"], staged["segments"]):
                for field in ("beat_ids", "duration_s", "direction"):
                    if json_hash(shot[field]) != json_hash(segment[field]):
                        raise ValueError("shot plan changed staged " + field)
        return {"plan": plan, "raw_responses": raw,
                "prompt_hashes": {name: hashlib.sha256(text.encode("utf-8")).hexdigest()
                                  for name, text in prompts.items()}}
    except Exception as exc:
        # The public client sanitizes transport errors; do not expose response text
        # from provider exceptions. Local validation errors are safe diagnostics.
        errors = [str(exc)] if isinstance(exc, (ValueError, TypeError)) else [type(exc).__name__]
        raise PlanningError(stage, errors, raw) from exc


def make_plan(scene: dict, manifest: dict, client, *, project_root=None, output_mode="animatic") -> dict:
    """Return a validated ShotPlan; failure exposes raw responses on PlanningError."""
    return make_plan_with_trace(scene, manifest, client, project_root=project_root, output_mode=output_mode)["plan"]
