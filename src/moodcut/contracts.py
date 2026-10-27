"""Public generated-mode 1.1 identities and review policy, with no I/O.

These helpers are not scene/media validators or an executable generation pipeline.
Legacy 1.0 callers keep their existing behavior until explicitly integrated.
"""
from copy import deepcopy
import hashlib
import json
import math

CONTRACT_VERSION = "1.1"
CONDITIONS = ("baseline", "generic_review", "moodcut")
OUTPUT_MODES = ("animatic", "generated")
LEGACY_TONES = ("affectionate", "suspicious", "hostile", "tense")
VEMOCLAP_EMOTIONS = ("anger", "disgust", "fear", "joy", "sadness", "surprise")
SUPPORTED_TONES = LEGACY_TONES + VEMOCLAP_EMOTIONS
GENERATION_SETTING_FIELDS = frozenset({
    "schema_version", "output_mode", "model", "resolution", "aspect_ratio",
    "generate_audio", "seed", "style", "sound", "characters",
})


def json_hash(data):
    """The existing MoodCut UTF-8 sorted-JSON SHA-256, byte-for-byte compatible."""
    text = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def allowed_patch_fields(*, output_mode: str) -> frozenset[str]:
    """Both review conditions must use the same mode-specific field whitelist."""
    if output_mode == "generated":
        return frozenset({"dialogue"})
    if output_mode == "animatic":
        return frozenset({"dialogue", "narration", "visuals", "duration_s"})
    raise ValueError("output_mode must be animatic or generated")


def _json_copy(value):
    def check(item):
        if type(item) is dict:
            if any(type(key) is not str for key in item):
                raise ValueError("Contract JSON object keys must be strings")
            for child in item.values():
                check(child)
        elif type(item) is list:
            for child in item:
                check(child)
        elif type(item) is float:
            if not math.isfinite(item):
                raise ValueError("Contract JSON numbers must be finite")
        elif item is not None and type(item) not in (str, int, bool):
            raise ValueError("Contract inputs must contain JSON values only")
    check(value)
    return deepcopy(value)


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _sha256(value):
    return (isinstance(value, str) and len(value) == 64
            and all(c in "0123456789abcdef" for c in value))


def _generated_header(value, label):
    if (not isinstance(value, dict) or value.get("schema_version") != CONTRACT_VERSION
            or value.get("output_mode") != "generated"):
        raise ValueError(f"{label} requires explicit schema_version=1.1 and output_mode=generated")


def non_dialogue_plan(plan: dict) -> dict:
    """Copy the entire plan, removing ONLY each shot's top-level dialogue field."""
    result = _json_copy(plan)
    if not isinstance(result, dict) or not isinstance(result.get("shots"), list) or not result["shots"]:
        raise ValueError("Plan requires a nonempty shots list")
    ids = set()
    for shot in result["shots"]:
        if (not isinstance(shot, dict) or not _text(shot.get("shot_id"))
                or shot["shot_id"] in ids or not isinstance(shot.get("dialogue"), list)):
            raise ValueError("Shots require unique IDs and explicit dialogue lists")
        ids.add(shot["shot_id"])
        del shot["dialogue"]
    return result


def assert_dialogue_only_revision(initial: dict, revised: dict) -> None:
    """Reject changes outside dialogue, including unknown fields and shot order.

    Dialogue speaker/text semantics and the complete schema must be validated by
    the owning validator/reviewer; a matching hash is not a quality judgment.
    """
    if json_hash(non_dialogue_plan(initial)) != json_hash(non_dialogue_plan(revised)):
        raise ValueError("Revision changed non-dialogue plan fields")


def shared_generation_payload(scene: dict, plan: dict, manifest: dict, settings: dict,
                              *, template_sha256: str) -> dict:
    """Build a shared identity, ignoring only manifest file locations.

    Include full scene, all non-dialogue plan fields, selected asset identities,
    closed generation settings and the compiler-template hash. Callers must also
    validate local asset bytes, plan semantics/structure and model capabilities.
    No URLs are fetched and no file paths are read here.
    """
    scene, plan, manifest, settings = _json_copy([scene, plan, manifest, settings])
    for label, value in (("scene", scene), ("plan", plan), ("settings", settings)):
        _generated_header(value, label)
    if not _sha256(template_sha256):
        raise ValueError("template_sha256 must be a lowercase SHA-256")
    if not _text(scene.get("scene_id")) or any(plan.get(k) != scene.get(k) for k in ("scene_id", "tone")):
        raise ValueError("Plan scene_id/tone must match scene")
    if set(settings) != GENERATION_SETTING_FIELDS:
        raise ValueError("Generation settings fields must exactly match the 1.1 contract")
    for field in ("model", "resolution", "aspect_ratio", "style", "sound"):
        if not _text(settings[field]):
            raise ValueError(f"settings.{field} must be nonempty")
    if settings["generate_audio"] is not True or type(settings["seed"]) is not int or settings["seed"] < 0:
        raise ValueError("Native audio and a nonnegative integer seed are required")
    characters = scene.get("characters")
    if (not isinstance(characters, list) or len(characters) != 2
            or any(not isinstance(c, dict) or not _text(c.get("id")) for c in characters)):
        raise ValueError("Scene requires two character IDs")
    ids = [c["id"] for c in characters]
    if len(set(ids)) != 2:
        raise ValueError("Scene character IDs must be unique")
    bindings = settings["characters"]
    if (not isinstance(bindings, list) or len(bindings) != 2
            or any(not isinstance(c, dict) or set(c) != {"id", "asset_id", "voice"} for c in bindings)
            or [c["id"] for c in bindings] != ids):
        raise ValueError("Settings character bindings must match scene order")
    asset_ids = scene.get("asset_ids")
    if (not isinstance(asset_ids, list) or not asset_ids or any(not _text(a) for a in asset_ids)
            or len(set(asset_ids)) != len(asset_ids)):
        raise ValueError("Scene requires unique asset IDs")
    if not isinstance(manifest, dict) or manifest.get("schema_version") != "1.0":
        raise ValueError("Use the existing AssetManifest 1.0")
    assets = manifest.get("assets")
    if not isinstance(assets, list):
        raise ValueError("Manifest requires assets")
    asset_map = {}
    for asset in assets:
        if (not isinstance(asset, dict) or not _text(asset.get("asset_id"))
                or asset["asset_id"] in asset_map):
            raise ValueError("Manifest asset IDs must be unique")
        asset_map[asset["asset_id"]] = asset
    references = []
    for aid in asset_ids:
        asset = asset_map.get(aid)
        if (asset is None or not _sha256(asset.get("sha256")) or asset.get("character_id") not in ids
                or asset.get("source_url") is not None and not _text(asset["source_url"])):
            raise ValueError("Selected asset requires valid content identity and character binding")
        references.append({k: asset.get(k) for k in ("asset_id", "character_id", "sha256", "source_url")})
    for binding in bindings:
        aid = binding["asset_id"]
        if (not _text(aid) or aid not in asset_ids or asset_map[aid]["character_id"] != binding["id"]
                or not _text(binding["voice"])):
            raise ValueError("Character reference/voice mapping is invalid")
    return {"contract_version": CONTRACT_VERSION, "scene": scene, "plan": non_dialogue_plan(plan),
            "references": references, "settings": settings, "template_sha256": template_sha256}


def shared_generation_sha256(scene: dict, plan: dict, manifest: dict, settings: dict,
                             *, template_sha256: str) -> str:
    """Hash a fresh payload; never trust an old declared hash without recomputing."""
    return json_hash(shared_generation_payload(scene, plan, manifest, settings,
                                               template_sha256=template_sha256))
