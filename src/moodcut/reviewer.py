"""Report checks and one bounded critique/revise/verify pass."""

from copy import deepcopy
import hashlib
from importlib.resources import files
import json
import logging

from .client import LLMClient
from . import validation
from .contracts import allowed_patch_fields, assert_dialogue_only_revision, _json_copy, json_hash


MAX_OUTPUT_TOKENS = 2048
TRACE_LOGGER = logging.getLogger("moodcut.review.trace")
GLOBAL_REVIEW = "global_v1"
ACTOR_REVIEW = "actor_self_review_v1"


def validate_review_protocol(review_protocol, output_mode):
    if review_protocol not in (GLOBAL_REVIEW, ACTOR_REVIEW):
        raise ValueError("Unknown review protocol")
    if review_protocol == ACTOR_REVIEW and output_mode != "generated":
        raise ValueError("Actor self-review requires explicit generated mode")


def _review_prompts(*, output_mode="animatic", review_protocol=GLOBAL_REVIEW):
    allowed_patch_fields(output_mode=output_mode)
    validate_review_protocol(review_protocol, output_mode)
    if review_protocol == ACTOR_REVIEW:
        return {name: files("moodcut").joinpath("prompts", f"review_actor_{name}.txt").read_text(encoding="utf-8")
                for name in ("generic", "moodcut", "revise")}
    prefix = "review_generated" if output_mode == "generated" else "review"
    return {name: files("moodcut").joinpath("prompts", f"{prefix}_{name}.txt").read_text(encoding="utf-8")
            for name in ("generic", "moodcut", "revise", "verify")}


def get_review_prompt_hashes(*, output_mode="animatic", review_protocol=GLOBAL_REVIEW):
    """Identity of the exact text supplied to the review client for this mode."""
    return {name: hashlib.sha256(text.encode("utf-8")).hexdigest()
            for name, text in _review_prompts(output_mode=output_mode, review_protocol=review_protocol).items()}


def _actor_lines(plan, actor_id):
    return [{"shot_id": shot["shot_id"], "line_index": index, "text": line["text"]}
            for shot in plan["shots"] for index, line in enumerate(shot["dialogue"])
            if line["character_id"] == actor_id]


def _merge_actor_reports(scene, plan, mode, records, *, partial=False):
    """Validate ownership and preserve raw reports while namespacing local IDs."""
    report = {"schema_version": "1.0", "scene_id": scene["scene_id"], "mode": mode, "issues": []}
    errors = []
    if (not isinstance(records, list) or len(records) > len(scene["characters"])
            or not partial and len(records) != len(scene["characters"])):
        return report, ["Exactly one report per actor is required"]
    shots = {shot["shot_id"]: shot for shot in plan["shots"]}
    for position, (actor, record) in enumerate(zip(scene["characters"], records), 1):
        if not isinstance(record, dict) or set(record) != {"actor_id", "response"} or record["actor_id"] != actor["id"]:
            errors.append("Actor report order/binding mismatch")
            continue
        response = record["response"]
        found = validate_report(scene, plan, response)
        if not isinstance(response, dict) or set(response) != {"schema_version", "scene_id", "mode", "actor_id", "issues"}:
            found.append("Actor response must contain only report fields and actor_id")
        if isinstance(response, dict) and (response.get("actor_id") != actor["id"] or response.get("mode") != mode):
            found.append("Actor response identity/mode mismatch")
        if found:
            errors.extend(found)
            continue
        for issue in response["issues"]:
            if set(issue) != {"issue_id", "shot_id", "dimension", "severity", "evidence", "suggestion", "line_indices"}:
                errors.append("Actor issues require only the standard fields and line_indices")
                continue
            indices = issue["line_indices"]
            dialogue = shots[issue["shot_id"]]["dialogue"]
            if (not isinstance(indices, list) or not indices
                    or any(type(i) is not int or i < 0 or i >= len(dialogue) for i in indices)
                    or len(set(indices)) != len(indices)
                    or any(dialogue[i]["character_id"] != actor["id"] for i in indices)):
                errors.append("Actor issue must reference only that actor's original dialogue lines")
                continue
            merged = deepcopy(issue)
            merged.update(issue_id=f"actor-{position}:" + issue["issue_id"],
                          source_issue_id=issue["issue_id"], actor_id=actor["id"])
            report["issues"].append(merged)
    return report, errors


def _disposition_errors(report, disposition):
    if not isinstance(disposition, dict) or set(disposition) != {"addressed_issue_ids", "unaddressed_issue_ids", "unaddressed_reasons"}:
        return ["Writer disposition requires addressed/unaddressed IDs and unaddressed_reasons"]
    errors = validate_verification(report, {"scene_id": report["scene_id"],
        "resolved_issue_ids": disposition["addressed_issue_ids"],
        "unresolved_issue_ids": disposition["unaddressed_issue_ids"], "new_concerns": []})
    reasons = disposition["unaddressed_reasons"]
    ids = disposition["unaddressed_issue_ids"]
    if (not isinstance(reasons, dict) or not isinstance(ids, list)
            or any(not isinstance(i, str) for i in ids) or set(reasons) != set(ids)
            or any(not isinstance(v, str) or not v.strip() for v in reasons.values())):
        errors.append("Every unaddressed actor issue requires its own recorded reason")
    return errors


def validate_actor_review_result(scene, initial, manifest, result, *, mode, project_root=None):
    """Recheck a saved actor result without model calls or changing its artifacts."""
    from .patches import apply_patch
    if not isinstance(result, dict) or result.get("review_protocol") != ACTOR_REVIEW:
        return ["Actor review protocol is missing"]
    report, errors = _merge_actor_reports(scene, initial, mode, result.get("actor_reports"))
    if errors:
        return errors
    if json_hash(report) != json_hash(result.get("report")):
        return ["Saved actor feedback was changed or dropped"]
    if result.get("verification") is not None or result.get("verification_kind") != "programmatic_only":
        errors.append("Actor protocol has no independent model verification")
    if result.get("actor_endorsement") != "not_requested":
        errors.append("The writer cannot claim final actor endorsement")
    disposition = result.get("feedback_disposition")
    errors.extend(_disposition_errors(report, disposition))
    writer = result.get("writer_response")
    if report["issues"]:
        if (not isinstance(writer, dict) or set(writer) != {"patch", "feedback_disposition"}
                or writer.get("patch") != result.get("patch") or writer.get("feedback_disposition") != disposition):
            errors.append("Saved unified writer response mismatch")
    elif writer is not None:
        errors.append("No-feedback result must not invent a writer response")
    if errors:
        return errors
    applied = apply_patch(scene, initial, manifest, report, result.get("patch"),
                          project_root=project_root, output_mode="generated")
    if (applied["status"] not in ("applied", "unchanged") or applied["status"] != result.get("status")
            or json_hash(applied["plan"]) != json_hash(result.get("plan"))):
        errors.append("Saved actor patch/plan/status mismatch")
        return errors
    expected_feedback = ("no_issues" if not report["issues"] else
                         "has_unaddressed" if disposition.get("unaddressed_issue_ids") else "writer_addressed")
    if result.get("actor_feedback_status") != expected_feedback:
        errors.append("Actor feedback status differs from the recorded disposition")
    if applied["status"] == "unchanged" and isinstance(disposition, dict) and disposition.get("addressed_issue_ids"):
        errors.append("Unchanged dialogue cannot claim addressed feedback")
    final = result.get("plan", {})
    if isinstance(final, dict) and isinstance(final.get("shots"), list):
        old_shots = {s["shot_id"]: s for s in initial["shots"]}
        new_shots = {s["shot_id"]: s for s in final["shots"]}
        allowed_lines = {(i["shot_id"], index) for i in report["issues"]
                         if i["issue_id"] in disposition["addressed_issue_ids"] for index in i["line_indices"]}
        for sid, shot in old_shots.items():
            new_lines = new_shots.get(sid, {}).get("dialogue", [])
            if [line["character_id"] for line in shot["dialogue"]] != [line.get("character_id") for line in new_lines]:
                errors.append("Unified writer must preserve dialogue speakers, order and line count")
            for index, (old_line, new_line) in enumerate(zip(shot["dialogue"], new_lines)):
                if old_line["text"] != new_line.get("text") and (sid, index) not in allowed_lines:
                    errors.append("Writer may revise only lines covered by addressed actor feedback")
        for issue in report["issues"]:
            if issue["issue_id"] not in disposition.get("addressed_issue_ids", []):
                continue
            old_lines = old_shots[issue["shot_id"]]["dialogue"]
            new_lines = new_shots.get(issue["shot_id"], {}).get("dialogue", [])
            if not any(i < len(new_lines) and new_lines[i].get("character_id") == issue["actor_id"]
                       and new_lines[i].get("text") != old_lines[i]["text"] for i in issue["line_indices"]):
                errors.append("Addressed feedback must change a referenced line belonging to that actor")
    return errors


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
                      client: LLMClient, *, mode: str, project_root=None, output_mode="animatic",
                      review_protocol=GLOBAL_REVIEW) -> dict:
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
    if review_protocol == ACTOR_REVIEW:
        result.update(review_protocol=ACTOR_REVIEW, actor_reports=[], writer_response=None,
                      verification_kind="programmatic_only", actor_endorsement="not_requested",
                      actor_feedback_status="incomplete",
                      feedback_disposition={"addressed_issue_ids": [], "unaddressed_issue_ids": [], "unaddressed_reasons": {}})
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
        validate_review_protocol(review_protocol, output_mode)
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
        prompts = _review_prompts(output_mode=output_mode, review_protocol=review_protocol)
        prompt = "generic" if mode == "generic_review" else "moodcut"
        if review_protocol == ACTOR_REVIEW:
            for actor in scene["characters"]:
                actor_context = {**deepcopy(context), "actor": deepcopy(actor),
                                 "own_dialogue": _actor_lines(original, actor["id"])}
                response = request("actor_critique", prompt, actor_context)
                result["actor_reports"].append({"actor_id": actor["id"], "response": response})
                # Validate immediately so a bad first actor cannot trigger another call.
                _, actor_errors = _merge_actor_reports(scene, original, mode, result["actor_reports"], partial=True)
                if actor_errors:
                    result["errors"] = actor_errors
                    return result
            result["report"], errors = _merge_actor_reports(scene, original, mode, result["actor_reports"])
            if errors:
                result["errors"] = errors
                return result
            result["actor_feedback_status"] = "awaiting_writer" if result["report"]["issues"] else "no_issues"
        else:
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
        revision_context = {**context, "report": result["report"],
                            "issues_by_shot": _issues_by_shot(original, result["report"])}
        if review_protocol == ACTOR_REVIEW:
            revision_context["actor_reports"] = deepcopy(result["actor_reports"])
            writer = request("actor_revise", "revise", revision_context)
            result["writer_response"] = writer
            if set(writer) != {"patch", "feedback_disposition"}:
                result["errors"] = ["Unified writer must return patch and feedback_disposition"]
                return result
            result["patch"] = writer["patch"]
            result["feedback_disposition"] = writer["feedback_disposition"]
            errors = _disposition_errors(result["report"], result["feedback_disposition"])
            if errors:
                result["errors"] = errors
                return result
            result["actor_feedback_status"] = ("has_unaddressed" if result["feedback_disposition"]["unaddressed_issue_ids"]
                                                else "writer_addressed")
        else:
            result["patch"] = request("revise", "revise", revision_context)
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
        if review_protocol == ACTOR_REVIEW:
            result.update(applied)
            errors = validate_actor_review_result(scene, original, manifest, result, mode=mode,
                                                  project_root=project_root)
            if errors:
                result.update(status="review_failed", plan=deepcopy(original), errors=errors)
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
