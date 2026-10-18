"""Report checks and one bounded critique/revise/verify pass."""

from copy import deepcopy
import hashlib
from importlib.resources import files
import json
import logging

from .client import LLMClient
from . import validation
from .contracts import allowed_patch_fields, assert_dialogue_only_revision, _json_copy


MAX_OUTPUT_TOKENS = 2048
TRACE_LOGGER = logging.getLogger("moodcut.review.trace")


def _review_prompts(*, output_mode="animatic"):
    allowed_patch_fields(output_mode=output_mode)
    prefix = "review_generated" if output_mode == "generated" else "review"
    return {name: files("moodcut").joinpath("prompts", f"{prefix}_{name}.txt").read_text(encoding="utf-8")
            for name in ("generic", "moodcut", "revise", "verify")}


def get_review_prompt_hashes(*, output_mode="animatic"):
    """Identity of the exact text supplied to the review client for this mode."""
    return {name: hashlib.sha256(text.encode("utf-8")).hexdigest()
            for name, text in _review_prompts(output_mode=output_mode).items()}


def _issues_by_shot(plan, report):
    """Group all validated opinions in shot order, without dropping issue IDs."""
    return [{"shot_id": shot["shot_id"], "issues": deepcopy(issues)} for shot in plan["shots"]
            if (issues := [issue for issue in report["issues"] if issue["shot_id"] == shot["shot_id"]])]


def validate_report(scene: dict, plan: dict, report: dict) -> list[str]:
    """Check report structure and references; opinions are not ground truth."""
    errors = []
    if not isinstance(scene, dict) or not isinstance(plan, dict):
        return ["scene and plan must be objects"]
    if not isinstance(report, dict):
        return ["report must be an object"]
    if report.get("schema_version") != "1.0":
        errors.append("report.schema_version must be 1.0")
    if (not isinstance(report.get("scene_id"), str) or not report["scene_id"].strip()
            or report["scene_id"] != scene.get("scene_id")
            or report["scene_id"] != plan.get("scene_id")):
        errors.append("report.scene_id must match scene and plan")
    if report.get("mode") not in ("generic_review", "moodcut"):
        errors.append("report.mode is invalid")
    issues = report.get("issues")
    if not isinstance(issues, list):
        return errors + ["report.issues must be an array"]
    shot_list = plan.get("shots")
    if not isinstance(shot_list, list):
        return errors + ["plan.shots must be an array"]
    shots = {s.get("shot_id") for s in shot_list
             if isinstance(s, dict) and isinstance(s.get("shot_id"), str)}
    seen = set()
    for index, issue in enumerate(issues):
        prefix = f"issues[{index}]"
        if not isinstance(issue, dict):
            errors.append(f"{prefix} must be an object")
            continue
        for field in ("issue_id", "shot_id", "evidence", "suggestion"):
            if not isinstance(issue.get(field), str) or not issue[field].strip():
                errors.append(f"{prefix}.{field} must be a nonempty string")
        issue_id = issue.get("issue_id")
        if isinstance(issue_id, str):
            if issue_id in seen:
                errors.append(f"{prefix}: duplicate issue_id {issue_id}")
            seen.add(issue_id)
        if not isinstance(issue.get("shot_id"), str) or issue["shot_id"] not in shots:
            errors.append(f"{prefix}: unknown shot_id")
        if issue.get("dimension") not in ("tone", "naturalness", "story", "renderability"):
            errors.append(f"{prefix}.dimension is invalid")
        if issue.get("severity") not in ("minor", "major"):
            errors.append(f"{prefix}.severity is invalid")
    return errors


def validate_verification(report: dict, verification: dict) -> list[str]:
    """Check complete, disjoint issue coverage without judging the opinion."""
    if not isinstance(verification, dict):
        return ["verification must be an object"]
    errors = []
    if verification.get("scene_id") != report["scene_id"]:
        errors.append("verification.scene_id must match report")
    expected = {issue["issue_id"] for issue in report["issues"]}
    groups = []
    for field in ("resolved_issue_ids", "unresolved_issue_ids"):
        values = verification.get(field)
        if not isinstance(values, list) or any(not isinstance(v, str) or not v.strip() for v in values):
            errors.append(f"verification.{field} must be an array of nonempty IDs")
            groups.append(set())
            continue
        group = set(values)
        if len(group) != len(values):
            errors.append(f"verification.{field} contains duplicate IDs")
        groups.append(group)
    if groups[0] & groups[1]:
        errors.append("verification resolved and unresolved IDs overlap")
    if groups[0] | groups[1] != expected:
        errors.append("verification IDs must cover exactly the report issues")
    concerns = verification.get("new_concerns")
    if not isinstance(concerns, list) or any(not isinstance(c, str) for c in concerns):
        errors.append("verification.new_concerns must be an array of strings")
    return errors


def review_and_revise(scene: dict, initial_plan: dict, manifest: dict,
                      client: LLMClient, *, mode: str, project_root=None, output_mode="animatic") -> dict:
    """Return ReviewResult; make at most three calls through the supplied client.

    Attach an INFO handler to moodcut.review.trace to persist request/response
    diagnostics. The client exposes parsed JSON, not provider raw HTTP text.
    This function performs no file writes and never retries a failed request.
    """
    # Local import avoids the report-validator dependency in patches.py.
    from .patches import apply_patch

    original = deepcopy(initial_plan)
    scene_id = scene.get("scene_id") if isinstance(scene, dict) else None
    result = {
        "plan": deepcopy(original),
        "report": {"schema_version": "1.0", "scene_id": scene_id, "mode": mode, "issues": []},
        "patch": {"schema_version": "1.0", "scene_id": scene_id, "edits": []},
        "verification": None,
        "status": "review_failed",
        "errors": [],
    }
    calls = 0
    stage = "preflight"

    def trace(event, **data):
        TRACE_LOGGER.info(json.dumps({"event": event, "mode": mode, "scene_id": scene_id,
                                     **data}, ensure_ascii=False, default=repr))

    def request(name, prompt, payload):
        nonlocal calls, stage
        stage = name
        system = prompts[prompt]
        user = json.dumps(payload, ensure_ascii=False, allow_nan=False)
        calls += 1
        trace("request", stage=name, max_output_tokens=MAX_OUTPUT_TOKENS,
              system=system, user=payload)
        response = client.complete_json(stage=name, system=system, user=user,
                                        max_output_tokens=MAX_OUTPUT_TOKENS)
        trace("response", stage=name, response=response)
        if not isinstance(response, dict):
            raise ValueError(f"{name} response must be a JSON object")
        json.dumps(response, allow_nan=False)
        if output_mode == "generated":
            _json_copy(response)
        return deepcopy(response)

    try:
        if mode not in ("generic_review", "moodcut"):
            raise ValueError("mode must be generic_review or moodcut")
        allowed_patch_fields(output_mode=output_mode)
        options = {"project_root": project_root} if project_root is not None else {}
        if output_mode == "generated":
            options["output_mode"] = output_mode
        errors = validation.validate_plan(deepcopy(scene), deepcopy(original), deepcopy(manifest),
                                          **options)
        if not isinstance(errors, list) or any(not isinstance(e, str) for e in errors):
            raise ValueError("validate_plan must return list[str]")
        if errors:
            result["errors"] = errors
            return result
        context = {"scene": deepcopy(scene), "plan": deepcopy(original),
                   "manifest": deepcopy(manifest), "mode": mode}
        if output_mode == "generated":
            context["output_mode"] = output_mode
        prompts = _review_prompts(output_mode=output_mode)
        prompt = "generic" if mode == "generic_review" else "moodcut"
        result["report"] = request("critique", prompt, context)
        errors = validate_report(scene, original, result["report"])
        if result["report"].get("mode") != mode:
            errors.append("report.mode must match requested mode")
        if errors:
            result["errors"] = errors
            return result
        if not result["report"]["issues"]:
            result["status"] = "unchanged"
            return result
        result["patch"] = request("revise", "revise",
                                  {**context, "report": result["report"],
                                   "issues_by_shot": _issues_by_shot(original, result["report"])})
        applied = apply_patch(deepcopy(scene), deepcopy(original), deepcopy(manifest),
                              deepcopy(result["report"]), deepcopy(result["patch"]), **options)
        if applied["status"] == "rejected":
            result.update(applied)
            return result
        if applied["status"] not in ("applied", "unchanged"):
            raise ValueError("Unexpected patch application status")
        if output_mode == "generated":
            try:
                # Check the actual plan before verifying it. Never verify a
                # multi-field candidate and then project it to a different plan.
                assert_dialogue_only_revision(original, applied["plan"])
            except ValueError as exc:
                result.update(status="rejected", plan=deepcopy(original), errors=[str(exc)])
                return result
        result["verification"] = request("verify", "verify",
                                         {**context, "revised_plan": applied["plan"],
                                          "report": result["report"], "patch": result["patch"]})
        errors = validate_verification(result["report"], result["verification"])
        if errors:
            result["errors"] = errors
            return result
        result.update(applied)
        return result
    except Exception as exc:
        result["plan"] = deepcopy(original)
        result["status"] = "review_failed"
        result["errors"] = [f"{stage}: {type(exc).__name__}: {exc}"]
        trace("error", stage=stage, errors=result["errors"])
        return result
    finally:
        trace("finished", calls=calls, status=result["status"], errors=result["errors"])
