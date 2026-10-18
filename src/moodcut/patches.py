"""Atomic constrained patches, without model calls or input mutations."""

from copy import deepcopy
from . import validation
from .reviewer import validate_report
from .contracts import allowed_patch_fields, assert_dialogue_only_revision, _json_copy, json_hash


def apply_patch(scene: dict, plan: dict, manifest: dict,
                report: dict, patch: dict, *, project_root=None, output_mode="animatic") -> dict:
    """Apply one edit per shot, then defer plan validity to MC-01.

    Missing or failing shared validation rejects the entire transaction.
    Text is subtitle content; structural checks cannot prove story fidelity
    or that a described action was generated in an image.
    """
    original = deepcopy(plan)

    def rejected(errors):
        return {"plan": original, "status": "rejected", "errors": errors}

    try:
        allowed = allowed_patch_fields(output_mode=output_mode)
        if output_mode == "generated":
            _json_copy([scene, plan, manifest, report, patch])
    except (ValueError, RecursionError) as exc:
        return rejected([str(exc)])
    errors = validate_report(scene, plan, report)
    if errors:
        return rejected(errors)
    if not isinstance(patch, dict):
        return rejected(["patch must be an object"])
    if set(patch) != {"schema_version", "scene_id", "edits"}:
        errors.append("patch fields must be schema_version, scene_id, edits")
    if patch.get("schema_version") != "1.0":
        errors.append("patch.schema_version must be 1.0")
    if patch.get("scene_id") != scene.get("scene_id") or patch.get("scene_id") != plan.get("scene_id"):
        errors.append("patch.scene_id must match scene and plan")
    if not isinstance(patch.get("edits"), list):
        return rejected(errors + ["patch.edits must be an array"])
    candidate = deepcopy(plan)
    # Index only unambiguous targets; complete plan validation remains in MC-01.
    shot_list = candidate.get("shots")
    if not isinstance(shot_list, list):
        return rejected(["plan.shots must be an array"])
    shots = {}
    for shot in shot_list:
        if (not isinstance(shot, dict) or not isinstance(shot.get("shot_id"), str)
                or not shot["shot_id"].strip() or shot["shot_id"] in shots):
            return rejected(["plan.shots must have unique nonempty shot_id values"])
        shots[shot["shot_id"]] = shot
    issues = {i["issue_id"]: i["shot_id"] for i in report["issues"]}
    seen_shots, seen_issues = set(), set()
    for index, edit in enumerate(patch["edits"]):
        prefix = f"edits[{index}]"
        if not isinstance(edit, dict) or set(edit) != {"issue_id", "shot_id", "set"}:
            errors.append(f"{prefix}: expected issue_id, shot_id, set")
            continue
        sid, iid = edit["shot_id"], edit["issue_id"]
        if not isinstance(sid, str) or sid not in shots:
            errors.append(f"{prefix}: unknown shot_id")
            continue
        if not isinstance(iid, str) or iid not in issues or issues[iid] != sid:
            errors.append(f"{prefix}: issue_id must reference an issue for this shot")
            continue
        if sid in seen_shots or iid in seen_issues:
            errors.append(f"{prefix}: conflicting or duplicate edit")
        seen_shots.add(sid)
        seen_issues.add(iid)
        changes = edit["set"]
        if not isinstance(changes, dict) or not changes:
            errors.append(f"{prefix}.set must be a nonempty object")
            continue
        if set(changes) - allowed:
            errors.append(f"{prefix}: forbidden field")
            continue
        if "dialogue" in changes:
            dialogue = changes["dialogue"]
            if (not isinstance(dialogue, list)
                    or any(not isinstance(line, dict)
                           or set(line) != {"character_id", "text"} for line in dialogue)):
                errors.append(f"{prefix}: dialogue entries must contain only character_id and text")
                continue
        if "visuals" in changes:
            visuals = changes["visuals"]
            old = shots[sid].get("visuals", [])
            if (not isinstance(visuals, list) or not isinstance(old, list)
                    or len(visuals) != len(old)
                    or any(not isinstance(v, dict) or set(v) != {"asset_id", "crop"}
                           or not isinstance(o, dict)
                           or v.get("asset_id") != o.get("asset_id")
                           for v, o in zip(visuals, old))):
                errors.append(f"{prefix}: visuals may change only crop, preserving assets and order")
                continue
        shots[sid].update(deepcopy(changes))
    if errors:
        return rejected(errors)
    if output_mode == "generated":
        try:
            assert_dialogue_only_revision(original, candidate)
        except ValueError as exc:
            return rejected([str(exc)])
    validator = getattr(validation, "validate_plan", None)
    if not callable(validator):
        return rejected(["MC-01 dependency unavailable: validation.validate_plan"])
    try:
        options = {"project_root": project_root} if project_root is not None else {}
        if output_mode == "generated":
            options["output_mode"] = output_mode
        errors = validator(deepcopy(scene), deepcopy(candidate), deepcopy(manifest), **options)
        if not isinstance(errors, list) or any(not isinstance(e, str) for e in errors):
            return rejected(["validate_plan must return list[str]"])
    except Exception as exc:
        return rejected([f"validate_plan failed: {type(exc).__name__}: {exc}"])
    if errors:
        return rejected(errors)
    unchanged = json_hash(candidate) == json_hash(original) if output_mode == "generated" else candidate == original
    return {"plan": candidate, "status": "unchanged" if unchanged else "applied", "errors": []}
