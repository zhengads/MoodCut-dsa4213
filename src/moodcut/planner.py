"""Three bounded MovieAgent-inspired text stages using the public LLM client.

The stage order is a method reference, implemented independently for MoodCut's
static-image schema. No upstream code, GPU tools or inference SDK is imported.
"""

from copy import deepcopy
import hashlib
from importlib.resources import files
import json
import logging

from . import validation


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


def _prompts():
    return {stage: files("moodcut").joinpath("prompts", f"planning_{stage}.txt")
            .read_text(encoding="utf-8") for stage in STAGES}


def get_planning_prompt_hashes() -> dict:
    """Hash exact shipped prompt text for persisted block-cache identity."""
    return {stage: hashlib.sha256(text.encode("utf-8")).hexdigest()
            for stage, text in _prompts().items()}


def _check_stage(stage, response, scene):
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


def normalize_plan(response: dict, scene: dict) -> dict:
    """Unwrap equivalent shot-list envelopes; never repair IDs or drop shots.

    Canonical top-level ShotPlan, {shots: [...]}, {plan: {...}} and a single
    {scenes: [{shots: [...]}]} envelope are accepted. Multi-scene generation is
    outside the one-scene contract and fails rather than silently truncating.
    """
    if not isinstance(response, dict):
        raise ValueError("shot response must be an object")
    data = deepcopy(response)
    if "plan" in data:
        if len(data) != 1 or not isinstance(data["plan"], dict):
            raise ValueError("plan wrapper must contain exactly one plan object")
        data = data["plan"]
    if "scenes" in data:
        if set(data) - {"scenes", "scene_id", "tone", "schema_version"}:
            raise ValueError("ambiguous scene envelope")
        scenes = data.pop("scenes")
        if not isinstance(scenes, list) or len(scenes) != 1 or not isinstance(scenes[0], dict):
            raise ValueError("exactly one scene must be returned")
        inner = scenes[0]
        for key in set(data) & set(inner):
            if data[key] != inner[key]:
                raise ValueError(f"conflicting scene metadata: {key}")
        data.update(inner)
    if set(data) - {"schema_version", "scene_id", "tone", "shots"}:
        raise ValueError("unknown fields in shot plan envelope")
    for field, default in (("schema_version", "1.0"), ("scene_id", scene["scene_id"]),
                           ("tone", scene["tone"])):
        data.setdefault(field, default)
    return data


def make_plan_with_trace(scene: dict, manifest: dict, client, *, project_root=None) -> dict:
    """Return plan, parsed responses and prompt hashes, including no hidden retries."""
    raw = {}
    stage = "preflight"
    kwargs = {"project_root": project_root} if project_root is not None else {}
    try:
        errors = validation.validate_scene(scene, manifest, **kwargs)
        if errors:
            raise ValueError("; ".join(errors))
        scene, manifest = deepcopy(scene), deepcopy(manifest)
        prompts = _prompts()
        for stage in STAGES:
            payload = {"scene": scene, "manifest": manifest, "prior_responses": raw}
            user = json.dumps(payload, ensure_ascii=False, allow_nan=False)
            response = client.complete_json(stage=stage, system=prompts[stage], user=user,
                                            max_output_tokens=MAX_OUTPUT_TOKENS[stage])
            raw[stage] = deepcopy(response)
            TRACE_LOGGER.info(json.dumps({"stage": stage, "response": response},
                                         ensure_ascii=False, allow_nan=False))
            if stage != "shot":
                _check_stage(stage, response, scene)
        plan = normalize_plan(raw["shot"], scene)
        errors = validation.validate_plan(scene, plan, manifest, **kwargs)
        if errors:
            raise ValueError("; ".join(errors))
        return {"plan": plan, "raw_responses": raw,
                "prompt_hashes": {name: hashlib.sha256(text.encode("utf-8")).hexdigest()
                                  for name, text in prompts.items()}}
    except Exception as exc:
        # The public client sanitizes transport errors; do not expose response text
        # from provider exceptions. Local validation errors are safe diagnostics.
        errors = [str(exc)] if isinstance(exc, (ValueError, TypeError)) else [type(exc).__name__]
        raise PlanningError(stage, errors, raw) from exc


def make_plan(scene: dict, manifest: dict, client, *, project_root=None) -> dict:
    """Return a validated ShotPlan; failure exposes raw responses on PlanningError."""
    return make_plan_with_trace(scene, manifest, client, project_root=project_root)["plan"]
