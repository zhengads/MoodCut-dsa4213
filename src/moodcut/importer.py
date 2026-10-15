"""Read local MovieAgent inputs without importing upstream tools or models."""

from copy import deepcopy
import json
from pathlib import Path


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON field: {key}")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError(f"Non-finite JSON value: {value}")


def import_synopsis(path: str) -> dict:
    """Return MovieScript/Character as story/character_names, preserving text.

    This imports a synopsis, not an automatically selected two-character scene.
    Full MovieAgent examples can contain more than two named characters.
    """
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8-sig"),
                          object_pairs_hook=_object,
                          parse_constant=_reject_constant)
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError(f"Cannot read synopsis: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("Synopsis must be a JSON object")
    story, names = data.get("MovieScript"), data.get("Character")
    if not isinstance(story, str) or not story.strip():
        raise ValueError("MovieScript must be a non-empty string")
    if (not isinstance(names, list) or not names
            or any(not isinstance(name, str) or not name.strip() for name in names)):
        raise ValueError("Character must be a non-empty list of non-empty strings")
    if len({name.strip().casefold() for name in names}) != len(names):
        raise ValueError("Character contains duplicate names")
    return {"story": story, "character_names": names.copy()}


def build_scene_from_synopsis(synopsis: dict, *, scene_id: str, tone: str,
                             characters: list[dict], beats: list[dict],
                             asset_ids: list[str], provenance: dict,
                             min_duration_s: float = 60,
                             max_duration_s: float = 90,
                             max_shots: int = 6) -> dict:
    """Build a SceneInput using an explicitly adapted two-character synopsis.

    Supply an already selected/adapted local synopsis. This function does not
    truncate a whole film, infer beats, choose a tone or invent source rights.
    Final scene/manifest checks run at planning preflight.
    """
    if not isinstance(synopsis, dict) or not isinstance(synopsis.get("story"), str):
        raise ValueError("synopsis must contain story and character_names")
    names = synopsis.get("character_names")
    if not isinstance(names, list) or len(names) != 2:
        raise ValueError("Explicitly adapt the synopsis to exactly two characters first")
    if (not isinstance(characters, list) or len(characters) != 2
            or any(not isinstance(c, dict) for c in characters)
            or {c.get("name") for c in characters} != set(names)):
        raise ValueError("characters must map the two synopsis names to explicit IDs")
    if not isinstance(provenance, dict) or not provenance.get("kind") or not provenance.get("adaptation"):
        raise ValueError("provenance must record kind and adaptation")
    return deepcopy({"schema_version": "1.0", "scene_id": scene_id,
                     "story": synopsis["story"], "tone": tone,
                     "characters": characters, "beats": beats,
                     "asset_ids": asset_ids, "min_duration_s": min_duration_s,
                     "max_duration_s": max_duration_s, "max_shots": max_shots,
                     "provenance": provenance})
