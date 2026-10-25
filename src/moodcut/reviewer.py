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
ACTOR_REVIEW_V2 = "actor_self_review_v2"
ACTOR_REVIEW_V3 = "actor_self_review_v3"
ACTOR_REVIEW_V4 = "actor_self_review_v4"
ACTOR_PROTOCOLS = (ACTOR_REVIEW, ACTOR_REVIEW_V2, ACTOR_REVIEW_V3, ACTOR_REVIEW_V4)
BOUNDED_PROTOCOLS = (ACTOR_REVIEW_V3, ACTOR_REVIEW_V4)
GLOBAL_REVIEWER_ID = "__global_reviewer__"
SHOT_WRITER_CONTRACT = "dialogue_by_shot_json_schema_v2"
WRITER_ONLY_SCHEMA_CONTRACT = "dialogue_by_shot_json_schema_v1"
JSON_OBJECT_WRITER_CONTRACT = "dialogue_by_shot_v1"
LEGACY_WRITER_CONTRACT = "issue_patch_v1"
WRITER_CONTRACTS = (SHOT_WRITER_CONTRACT, WRITER_ONLY_SCHEMA_CONTRACT,
                    JSON_OBJECT_WRITER_CONTRACT, LEGACY_WRITER_CONTRACT)


def get_writer_json_schema(*, second_round=False):
    """Shape-only provider constraint; spoken words and issue decisions remain model output."""
    def obj(properties):
        return {"type": "object", "properties": properties, "required": list(properties),
                "additionalProperties": False}
    text = {"type": "string"}
    ids = {"type": "array", "items": text}
    reasons = {"type": "object", "additionalProperties": text}
    fields = {
        "dialogue_by_shot": {"type": "object", "additionalProperties": {
            "type": "array", "items": obj({"character_id": text, "text": text})}},
        "feedback_disposition": obj({"addressed_issue_ids": ids, "unaddressed_issue_ids": ids,
                                      "unaddressed_reasons": reasons})}
    if second_round:
        fields["objection_responses"] = reasons
    return obj(fields)


def validate_review_protocol(review_protocol, output_mode):
    if review_protocol not in (GLOBAL_REVIEW, *ACTOR_PROTOCOLS):
        raise ValueError("Unknown review protocol")
    if review_protocol in ACTOR_PROTOCOLS and output_mode != "generated":
        raise ValueError("Actor self-review requires explicit generated mode")


def _review_prompts(*, output_mode="animatic", review_protocol=GLOBAL_REVIEW, writer_output_contract=None):
    allowed_patch_fields(output_mode=output_mode)
    validate_review_protocol(review_protocol, output_mode)
    if review_protocol == ACTOR_REVIEW_V4:
        if writer_output_contract not in (None, SHOT_WRITER_CONTRACT):
            raise ValueError("v4 requires the current shot writer contract")
        return {name: files("moodcut").joinpath("prompts", f"review_v4_{name}.txt").read_text(encoding="utf-8")
                for name in ("generic", "moodcut", "revise", "negotiate", "confirm")}
    if review_protocol in ACTOR_PROTOCOLS:
        names = ("generic", "moodcut", "revise") + (("confirm",) if review_protocol in (ACTOR_REVIEW_V2, ACTOR_REVIEW_V3) else ())
        if review_protocol == ACTOR_REVIEW_V3:
            names += ("negotiate",)
        sources = {name: name for name in names}
        if review_protocol == ACTOR_REVIEW_V3:
            contract = writer_output_contract or SHOT_WRITER_CONTRACT
            if contract not in WRITER_CONTRACTS:
                raise ValueError("Unknown v3 writer output contract")
            sources["confirm"] = "confirm_bounded"
            if contract in (SHOT_WRITER_CONTRACT, WRITER_ONLY_SCHEMA_CONTRACT):
                sources.update(revise="revise_by_shot_schema", negotiate="negotiate_by_shot_schema")
                if contract == SHOT_WRITER_CONTRACT:
                    sources.update(generic="generic_schema", moodcut="moodcut_schema")
            elif contract == JSON_OBJECT_WRITER_CONTRACT:
                sources.update(revise="revise_by_shot", negotiate="negotiate_by_shot")
        return {name: files("moodcut").joinpath("prompts", f"review_actor_{source}.txt").read_text(encoding="utf-8")
                for name, source in sources.items()}
    prefix = "review_generated" if output_mode == "generated" else "review"
    return {name: files("moodcut").joinpath("prompts", f"{prefix}_{name}.txt").read_text(encoding="utf-8")
            for name in ("generic", "moodcut", "revise", "verify")}


def get_review_prompt_hashes(*, output_mode="animatic", review_protocol=GLOBAL_REVIEW, writer_output_contract=None):
    """Identity of the exact text supplied to the review client for this mode."""
    return {name: hashlib.sha256(text.encode("utf-8")).hexdigest()
            for name, text in _review_prompts(output_mode=output_mode, review_protocol=review_protocol,
                                             writer_output_contract=writer_output_contract).items()}


def _actor_lines(plan, actor_id):
    return [{"shot_id": shot["shot_id"], "line_index": index, "text": line["text"]}
            for shot in plan["shots"] for index, line in enumerate(shot["dialogue"])
            if actor_id == GLOBAL_REVIEWER_ID or line["character_id"] == actor_id]


def get_reviewers(scene, mode, review_protocol):
    """Only v4 generic review has one global reviewer; old identities stay intact."""
    if review_protocol == ACTOR_REVIEW_V4 and mode == "generic_review":
        return [{"id": GLOBAL_REVIEWER_ID, "name": "Global reviewer"}]
    return scene["characters"]


def get_actor_json_schema(scene, plan, actor_id, mode):
    """Constrain references using existing ownership, without supplying an opinion."""
    def obj(properties):
        return {"type": "object", "properties": properties, "required": list(properties),
                "additionalProperties": False}

    text = {"type": "string"}
    by_shot = {}
    for line in _actor_lines(plan, actor_id):
        by_shot.setdefault(line["shot_id"], []).append(line["line_index"])

    def issue(shot_id=None, indices=None):
        return obj({"issue_id": text,
                    "shot_id": {"type": "string", **({"enum": [shot_id]} if shot_id is not None else {})},
                    "line_indices": {"type": "array", "minItems": 1, "items": {
                        "type": "integer", **({"enum": indices} if indices is not None else {})}},
                    "dimension": {"type": "string", "enum": ["tone", "naturalness", "story", "renderability"]},
                    "severity": {"type": "string", "enum": ["minor", "major"]},
                    "evidence": text, "suggestion": text})

    issues = {"type": "array", "items": {"anyOf": [issue(s, indices) for s, indices in by_shot.items()]}
              if by_shot else issue()}
    if not by_shot:
        issues["maxItems"] = 0
    return obj({"schema_version": {"type": "string", "enum": ["1.0"]},
                "scene_id": {"type": "string", "enum": [scene["scene_id"]]},
                "mode": {"type": "string", "enum": [mode]},
                "actor_id": {"type": "string", "enum": [actor_id]}, "issues": issues})


def _merge_actor_reports(scene, plan, mode, records, *, partial=False, reviewers=None):
    """Validate ownership and preserve raw reports while namespacing local IDs."""
    report = {"schema_version": "1.0", "scene_id": scene["scene_id"], "mode": mode, "issues": []}
    errors = []
    actors = scene["characters"] if reviewers is None else reviewers
    if (not isinstance(records, list) or len(records) > len(actors)
            or not partial and len(records) != len(actors)):
        return report, ["Exactly one report per actor is required"]
    shots = {shot["shot_id"]: shot for shot in plan["shots"]}
    for position, (actor, record) in enumerate(zip(actors, records), 1):
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
                    or actor["id"] != GLOBAL_REVIEWER_ID and any(dialogue[i]["character_id"] != actor["id"] for i in indices)):
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


def _actor_confirmation_errors(scene, initial, result, mode, *, partial=False, issue_ids=None,
                               acceptance="accept_omission", reviewers=None, confirmation_round=1):
    """Check only the owning actor can consent to an omitted, candidate-bound issue."""
    omitted = result["feedback_disposition"]["unaddressed_issue_ids"] if issue_ids is None else issue_ids
    issues = [i for i in result["report"]["issues"] if i["issue_id"] in omitted]
    actors = ([a for a in scene["characters"] if any(i["actor_id"] == a["id"] for i in issues)]
              if reviewers is None else reviewers)
    records = result.get("actor_confirmations")
    if (not isinstance(records, list) or len(records) > len(actors)
            or not partial and len(records) != len(actors)):
        return ["Exactly one omission confirmation per affected actor is required"], []
    errors, disputed = [], []
    for actor, record in zip(actors, records):
        if not isinstance(record, dict) or set(record) != {"actor_id", "response"} or record["actor_id"] != actor["id"]:
            errors.append("Actor omission confirmation order/owner mismatch")
            continue
        response = record["response"]
        fields = {"schema_version", "scene_id", "mode", "actor_id", "initial_plan_sha256", "candidate_plan_sha256", "decisions"}
        if reviewers is not None:
            fields.add("new_issues")
        if not isinstance(response, dict) or set(response) != fields:
            errors.append("Actor omission confirmation has invalid fields")
            continue
        if (response["schema_version"] != "1.0" or response["scene_id"] != scene["scene_id"]
                or response["mode"] != mode or response["actor_id"] != actor["id"]
                or response["initial_plan_sha256"] != json_hash(initial)
                or response["candidate_plan_sha256"] != json_hash(result["writer_candidate_plan"])):
            errors.append("Actor omission confirmation identity/candidate mismatch")
            continue
        decisions = response["decisions"]
        if not isinstance(decisions, list):
            errors.append("Actor omission decisions must be an array")
            continue
        ids = []
        for decision in decisions:
            if (not isinstance(decision, dict) or set(decision) != {"issue_id", "decision", "reason"}
                    or not isinstance(decision["issue_id"], str)
                    or decision["decision"] not in (("resolved", "withdrawn", "maintain_objection")
                        if reviewers is not None else (acceptance, "maintain_objection"))
                    or not isinstance(decision["reason"], str) or not decision["reason"].strip()):
                errors.append("Each actor omission decision requires an issue, decision and reason")
                continue
            ids.append(decision["issue_id"])
            if decision["decision"] == "maintain_objection":
                disputed.append(decision["issue_id"])
        expected = {i["issue_id"] for i in issues if i["actor_id"] == actor["id"]}
        if len(set(ids)) != len(ids) or set(ids) != expected:
            errors.append("Actor omission decisions must cover exactly its own unaddressed issues")
        if reviewers is not None:
            # New feedback is allowed only for candidate-introduced regressions.
            raw = [{"actor_id": a["id"], "response": {"schema_version": "1.0", "scene_id": scene["scene_id"],
                "mode": mode, "actor_id": a["id"], "issues": response["new_issues"] if a == actor else []}}
                for a in reviewers]
            new_report, found = _merge_actor_reports(scene, initial, mode, raw, reviewers=reviewers)
            errors.extend(found)
            old = initial if confirmation_round == 1 else result["negotiation_rounds"][confirmation_round-2]["plan"]
            old_shots = {s["shot_id"]: s for s in old["shots"]}
            new_shots = {s["shot_id"]: s for s in result["writer_candidate_plan"]["shots"]}
            for issue in new_report["issues"]:
                if old_shots[issue["shot_id"]]["dialogue"] == new_shots[issue["shot_id"]]["dialogue"]:
                    errors.append("New revisit issues require changed dialogue in the referenced shot")
                prefix, local = issue["issue_id"].split(":", 1)
                new_id = f"{prefix}:revisit-{confirmation_round}:{local}"
                if new_id in {i["issue_id"] for i in result["report"]["issues"]}:
                    errors.append("New revisit issue ID collides with existing feedback")
                disputed.append(new_id)
    return errors, disputed


def _v4_reports(result, before_round):
    """Replay prior candidate regressions without mutating the initial raw opinions."""
    records = deepcopy(result["actor_reports"])
    for index, current in enumerate(result["negotiation_rounds"][:before_round], 1):
        for confirmation in current["actor_confirmations"]:
            owner = next(r["response"] for r in records if r["actor_id"] == confirmation["actor_id"])
            owner["issues"].extend(dict(deepcopy(i), issue_id=f"revisit-{index}:" + i["issue_id"])
                                   for i in confirmation["response"]["new_issues"])
    return records


def validate_actor_review_result(scene, initial, manifest, result, *, mode, project_root=None,
                                require_confirmation=True):
    """Recheck a saved actor result without model calls or changing its artifacts."""
    if not isinstance(result, dict) or result.get("review_protocol") not in ACTOR_PROTOCOLS:
        return ["Actor review protocol is missing"]
    if result["review_protocol"] in BOUNDED_PROTOCOLS:
        try:
            return _validate_bounded_actor_result(scene, initial, manifest, result, mode=mode, project_root=project_root)
        except (KeyError, TypeError, StopIteration, AttributeError) as exc:
            if result["review_protocol"] != ACTOR_REVIEW_V4:
                raise
            return [f"Invalid v4 saved result: {type(exc).__name__}"]
    return _validate_actor_candidate(scene, initial, manifest, result, mode=mode,
        project_root=project_root, require_confirmation=require_confirmation)


def _validate_actor_candidate(scene, initial, manifest, result, *, mode, project_root=None,
                              require_confirmation=True, reviewers=None, actor_reports=None):
    from .patches import apply_patch
    report, errors = _merge_actor_reports(scene, initial, mode,
        result.get("actor_reports") if actor_reports is None else actor_reports, reviewers=reviewers)
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
    try:
        assert_dialogue_only_revision(initial, result["plan"])
    except (ValueError, TypeError, KeyError) as exc:
        return [str(exc)]
    expected_feedback = ("no_issues" if not report["issues"] else
                         "has_unaddressed" if disposition.get("unaddressed_issue_ids") else "writer_addressed")
    if result.get("actor_feedback_status") != expected_feedback:
        errors.append("Actor feedback status differs from the recorded disposition")
    if result["review_protocol"] == ACTOR_REVIEW_V2:
        if result.get("writer_candidate_plan") != applied["plan"]:
            errors.append("Actor confirmation must bind the actual writer candidate")
            return errors
        if require_confirmation:
            confirmation_errors, disputed = _actor_confirmation_errors(scene, initial, result, mode)
            errors.extend(confirmation_errors)
            expected_confirmation = ("not_needed" if not disposition["unaddressed_issue_ids"] else
                                     "disputed" if disputed else "accepted")
            if result.get("actor_confirmation_status") != expected_confirmation:
                errors.append("Actor confirmation status differs from saved decisions")
            if disputed:
                errors.append("Actor maintains objection to omission; human resolution is required")
    if applied["status"] == "unchanged" and isinstance(disposition, dict) and any(
            i["issue_id"] in disposition.get("addressed_issue_ids", [])
            and (reviewers is None or not i["source_issue_id"].startswith("revisit-")) for i in report["issues"]):
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
            if reviewers is not None and issue["source_issue_id"].startswith("revisit-"):
                # Reverting an introduced regression to the original is a valid repair.
                continue
            old_lines = old_shots[issue["shot_id"]]["dialogue"]
            new_lines = new_shots.get(issue["shot_id"], {}).get("dialogue", [])
            if not any(i < len(new_lines) and (issue["actor_id"] == GLOBAL_REVIEWER_ID
                       or new_lines[i].get("character_id") == issue["actor_id"])
                       and new_lines[i].get("text") != old_lines[i]["text"] for i in issue["line_indices"]):
                errors.append("Addressed feedback must change a referenced line belonging to that actor")
    return errors


_ROUND_FIELDS = ("writer_response", "patch", "feedback_disposition", "writer_candidate_plan", "plan", "status",
                 "actor_feedback_status", "actor_confirmations", "actor_confirmation_status",
                 "confirmation_issue_ids", "disputed_issue_ids")


def _bounded_writer_response(scene, initial, report, writer, *, contract, second_round):
    """Translate one model-selected dialogue per shot; never merge or choose between edits."""
    field = "patch" if contract == LEGACY_WRITER_CONTRACT else "dialogue_by_shot"
    if contract not in WRITER_CONTRACTS:
        raise ValueError("Unknown v3 writer output contract")
    expected = {field, "feedback_disposition"} | ({"objection_responses"} if second_round else set())
    if not isinstance(writer, dict) or set(writer) != expected:
        raise ValueError("Invalid bounded writer response fields")
    if contract == LEGACY_WRITER_CONTRACT:
        return {k: deepcopy(writer[k]) for k in ("patch", "feedback_disposition")}
    by_shot = writer["dialogue_by_shot"]
    if not isinstance(by_shot, dict):
        raise ValueError("dialogue_by_shot must be an object with one complete dialogue per shot ID")
    groups = _issues_by_shot(initial, report)
    targets = {g["shot_id"]: g for g in groups}
    if any(not isinstance(sid, str) or sid not in targets for sid in by_shot):
        raise ValueError("dialogue_by_shot contains an unknown or feedback-free shot")
    patch = {"schema_version": "1.0", "scene_id": scene["scene_id"], "edits": [
        {"issue_id": g["issues"][0]["issue_id"], "shot_id": g["shot_id"],
         "set": {"dialogue": deepcopy(by_shot[g["shot_id"]])}} for g in groups if g["shot_id"] in by_shot]}
    return {"patch": patch, "feedback_disposition": deepcopy(writer["feedback_disposition"])}


def _negotiation_revision_errors(report, previous, current, *, allow_unresolved=False):
    """Require a real second attempt on every objection, without judging its quality."""
    disputed = previous["disputed_issue_ids"]
    writer = current["writer_response"]
    responses = writer.get("objection_responses")
    errors = []
    if (not isinstance(responses, dict) or set(responses) != set(disputed)
            or any(not isinstance(v, str) or not v.strip() for v in responses.values())):
        errors.append("Second writer must respond to every maintained actor objection")
    if allow_unresolved:
        # A reasoned refusal is valid; the revisit, not the writer, settles the concern.
        for issue in report["issues"]:
            if (issue["source_issue_id"].startswith("revisit-")
                    and issue["issue_id"] in current["feedback_disposition"]["addressed_issue_ids"]):
                old = next(s for s in previous["plan"]["shots"] if s["shot_id"] == issue["shot_id"])
                new = next(s for s in current["plan"]["shots"] if s["shot_id"] == issue["shot_id"])
                if old["dialogue"] == new["dialogue"]:
                    errors.append("Addressed regression must change dialogue in its referenced candidate shot")
        return errors
    old_addressed = set(previous["feedback_disposition"]["addressed_issue_ids"])
    addressed = set(current["feedback_disposition"]["addressed_issue_ids"])
    if not old_addressed.union(disputed) <= addressed:
        errors.append("Second writer must retain earlier addressed feedback and attempt all objections")
    old_shots = {s["shot_id"]: s for s in previous["plan"]["shots"]}
    new_shots = {s["shot_id"]: s for s in current["plan"]["shots"]}
    for issue in report["issues"]:
        if issue["issue_id"] in disputed and not any(
                old_shots[issue["shot_id"]]["dialogue"][i]["text"] !=
                new_shots[issue["shot_id"]]["dialogue"][i]["text"] for i in issue["line_indices"]):
            errors.append("Second writer must actually revise each disputed actor's referenced dialogue")
    return errors


def _validate_bounded_actor_result(scene, initial, manifest, result, *, mode, project_root=None):
    v4 = result["review_protocol"] == ACTOR_REVIEW_V4
    reviewers = get_reviewers(scene, mode, result["review_protocol"]) if v4 else None
    rounds = result.get("negotiation_rounds")
    if not isinstance(rounds, list) or len(rounds) > 2:
        return ["Bounded actor negotiation requires at most two rounds"]
    # Reuse the v1 checks for all original feedback, ownership, patch and plan invariants.
    base = deepcopy(result)
    base["review_protocol"] = ACTOR_REVIEW
    contract = result.get("writer_output_contract", LEGACY_WRITER_CONTRACT)
    if v4 and contract != SHOT_WRITER_CONTRACT:
        return ["v4 requires the current shot writer contract"]
    if contract not in WRITER_CONTRACTS:
        return ["Unknown v3 writer output contract"]
    if base.get("writer_response") is not None:
        try:
            base["writer_response"] = _bounded_writer_response(scene, initial, result["report"], base["writer_response"],
                contract=contract, second_round=len(rounds) == 2)
        except (ValueError, TypeError, KeyError) as exc:
            return [str(exc)]
    errors = _validate_actor_candidate(scene, initial, manifest, base, mode=mode,
        project_root=project_root, reviewers=reviewers,
        actor_reports=_v4_reports(result, max(0, len(rounds)-1)) if v4 else None)
    if errors:
        return errors
    if bool(result["report"]["issues"]) != bool(rounds):
        return ["Actor issues require a recorded writer/confirmation round"]
    previous = None
    for index, current in enumerate(rounds):
        if not isinstance(current, dict) or set(current) != set(_ROUND_FIELDS):
            return ["Invalid actor negotiation round fields"]
        writer = current["writer_response"]
        check = {**deepcopy(base), **deepcopy(current)}
        records = _v4_reports(result, index) if v4 else None
        if v4:
            check["report"], errors = _merge_actor_reports(scene, initial, mode, records, reviewers=reviewers)
            if errors:
                return errors
        try:
            check["writer_response"] = _bounded_writer_response(scene, initial, check["report"], writer,
                contract=contract, second_round=bool(index))
        except (ValueError, TypeError, KeyError) as exc:
            return [str(exc)]
        errors = _validate_actor_candidate(scene, initial, manifest, check, mode=mode,
            project_root=project_root, reviewers=reviewers, actor_reports=records)
        if errors:
            return errors
        if current["writer_candidate_plan"] != current["plan"]:
            return ["Negotiation confirmation must bind the actual candidate"]
        if previous is not None:
            if not previous["disputed_issue_ids"]:
                return ["An extra writer round requires a maintained actor objection"]
            errors = _negotiation_revision_errors(result["report"], previous, current, allow_unresolved=v4)
            if errors:
                return errors
        target = set(current["feedback_disposition"]["unaddressed_issue_ids"])
        if previous is not None:
            target.update(previous["disputed_issue_ids"])
        if v4:
            target = {i["issue_id"] for i in check["report"]["issues"]}
        expected_ids = [i["issue_id"] for i in check["report"]["issues"] if i["issue_id"] in target]
        errors, disputed = _actor_confirmation_errors(scene, initial, check, mode,
            issue_ids=expected_ids, acceptance="accept_candidate", reviewers=reviewers, confirmation_round=index+1)
        if errors:
            return errors
        if v4:
            expected_ids += [i for i in disputed if i not in target]
        if current["confirmation_issue_ids"] != expected_ids:
            return ["Actor confirmation must cover omissions and all prior objections"]
        confirmation_status = "not_needed" if not target else "disputed" if disputed else "accepted"
        if current["disputed_issue_ids"] != disputed or current["actor_confirmation_status"] != confirmation_status:
            return ["Actor negotiation decisions and summary differ"]
        previous = current
    if rounds:
        if any(result.get(k) != rounds[-1][k] for k in _ROUND_FIELDS):
            return ["Final actor negotiation summary/candidate differs from last round"]
        if len(rounds) == 1 and previous["disputed_issue_ids"]:
            return ["Maintained objections require the bounded second revision"]
    elif (result.get("actor_confirmations") != [] or result.get("confirmation_issue_ids") != []
            or result.get("disputed_issue_ids") != [] or result.get("actor_confirmation_status") != "not_needed"
            or result.get("writer_candidate_plan") != initial):
        return ["No-issue negotiation must not invent confirmations or a candidate"]
    expected = "no_issues" if not rounds else "disputed" if previous["disputed_issue_ids"] else "complete"
    if result.get("negotiation_status") != expected or type(result.get("negotiation_round_count")) is not int or result["negotiation_round_count"] != len(rounds):
        return ["Actor negotiation completion/disagreement summary mismatch"]
    return []


def _run_bounded_actor_negotiation(scene, original, manifest, result, context, request, *, mode, project_root):
    """Two rounds maximum; valid final disagreement is a viewable draft, never approval."""
    from .patches import apply_patch
    v4 = result["review_protocol"] == ACTOR_REVIEW_V4
    reviewers = get_reviewers(scene, mode, result["review_protocol"])
    for index in range(2):
        previous = deepcopy(result["negotiation_rounds"][-1]) if index else None
        records = _v4_reports(result, index) if v4 else None
        if v4:
            result["report"], errors = _merge_actor_reports(scene, original, mode, records, reviewers=reviewers)
            if errors:
                raise ValueError("; ".join(errors))
        payload = {**deepcopy(context), "report": deepcopy(result["report"]),
                   "issues_by_shot": _issues_by_shot(original, result["report"]),
                   "actor_reports": deepcopy(result["actor_reports"]),
                   "writer_output_contract": SHOT_WRITER_CONTRACT,
                   "revision_slots": [{"shot_id": s["shot_id"], "original_dialogue": deepcopy(s["dialogue"]),
                       "issue_ids": [i["issue_id"] for i in result["report"]["issues"] if i["shot_id"] == s["shot_id"]]}
                       for s in original["shots"] if any(i["shot_id"] == s["shot_id"] for i in result["report"]["issues"])]}
        if v4:
            # The shared writer gets no branch label from which to invent an objective.
            payload.pop("mode", None)
            payload["report"].pop("mode", None)
            for record in payload["actor_reports"]:
                record["response"].pop("mode", None)
        if previous is not None:
            payload.update(previous_round=previous, required_objection_ids=previous["disputed_issue_ids"])
            if v4:
                for record in payload["previous_round"]["actor_confirmations"]:
                    record["response"].pop("mode", None)
        # Save the raw attempted round before validation or any further call.
        current = {k: deepcopy(result[k]) for k in _ROUND_FIELDS}
        current.update(actor_confirmations=[], confirmation_issue_ids=[], disputed_issue_ids=[],
                       actor_confirmation_status="pending")
        result["negotiation_rounds"].append(current)
        writer = request("actor_revise", "negotiate" if index else "revise", payload)
        current["writer_response"] = writer
        normalized = _bounded_writer_response(scene, original, result["report"], writer,
            contract=SHOT_WRITER_CONTRACT, second_round=bool(index))
        current.update(patch=normalized["patch"], feedback_disposition=normalized["feedback_disposition"])
        errors = _disposition_errors(result["report"], current["feedback_disposition"])
        if errors:
            raise ValueError("; ".join(errors))
        applied = apply_patch(scene, original, manifest, result["report"], current["patch"],
                              project_root=project_root, output_mode="generated")
        current.update(applied)
        if applied["status"] not in ("applied", "unchanged"):
            raise ValueError("; ".join(applied["errors"]))
        current["writer_candidate_plan"] = deepcopy(applied["plan"])
        current["actor_feedback_status"] = "has_unaddressed" if current["feedback_disposition"]["unaddressed_issue_ids"] else "writer_addressed"
        check = {**deepcopy(result), **deepcopy(current), "review_protocol": ACTOR_REVIEW}
        check["writer_response"] = normalized
        errors = _validate_actor_candidate(scene, original, manifest, check, mode=mode,
            project_root=project_root, reviewers=reviewers if v4 else None, actor_reports=records)
        if previous is not None and not errors:
            errors = _negotiation_revision_errors(result["report"], previous, current, allow_unresolved=v4)
        if errors:
            raise ValueError("; ".join(errors))
        targets = set(current["feedback_disposition"]["unaddressed_issue_ids"])
        if previous is not None:
            targets.update(previous["disputed_issue_ids"])
        if v4:
            targets = {i["issue_id"] for i in result["report"]["issues"]}
        current["confirmation_issue_ids"] = [i["issue_id"] for i in result["report"]["issues"] if i["issue_id"] in targets]
        for actor in reviewers:
            own = [i for i in result["report"]["issues"] if i["actor_id"] == actor["id"] and i["issue_id"] in targets]
            if not own and not v4:
                continue
            reasons = current["feedback_disposition"]["unaddressed_reasons"]
            confirm_payload = {"scene": deepcopy(scene), "mode": mode, "actor": deepcopy(actor),
                "initial_plan": deepcopy(original), "revised_plan": deepcopy(current["plan"]),
                "initial_plan_sha256": json_hash(original), "candidate_plan_sha256": json_hash(current["plan"]),
                "actor_report": deepcopy(next(r["response"] for r in result["actor_reports"] if r["actor_id"] == actor["id"])),
                "issues_to_confirm": [dict(deepcopy(i), writer_reason=reasons.get(i["issue_id"]),
                    writer_response=writer.get("objection_responses", {}).get(i["issue_id"])) for i in own],
                "previous_own_decisions": [] if previous is None else deepcopy(next(
                    (r["response"]["decisions"] for r in previous["actor_confirmations"] if r["actor_id"] == actor["id"]), [])),
                "own_original_dialogue": _actor_lines(original, actor["id"]),
                "own_revised_dialogue": _actor_lines(current["plan"], actor["id"]), "round": index + 1}
            response = request("actor_confirm", "confirm", confirm_payload)
            current["actor_confirmations"].append({"actor_id": actor["id"], "response": response})
            errors, _ = _actor_confirmation_errors(scene, original, {**result, **current}, mode,
                partial=True, issue_ids=current["confirmation_issue_ids"], acceptance="accept_candidate",
                reviewers=reviewers if v4 else None, confirmation_round=index+1)
            if errors:
                raise ValueError("; ".join(errors))
        errors, disputed = _actor_confirmation_errors(scene, original, {**result, **current}, mode,
            issue_ids=current["confirmation_issue_ids"], acceptance="accept_candidate",
            reviewers=reviewers if v4 else None, confirmation_round=index+1)
        if errors:
            raise ValueError("; ".join(errors))
        if v4:
            current["confirmation_issue_ids"] += [i for i in disputed if i not in targets]
        current.update(disputed_issue_ids=disputed,
                       actor_confirmation_status="not_needed" if not targets else "disputed" if disputed else "accepted")
        # Exclude apply_patch diagnostics from the exact serialized round contract.
        for key in list(current):
            if key not in _ROUND_FIELDS:
                current.pop(key)
        result.update(deepcopy(current), negotiation_round_count=index + 1,
                      negotiation_status="disputed" if disputed else "complete")
        if not disputed:
            break
    errors = validate_actor_review_result(scene, original, manifest, result, mode=mode, project_root=project_root)
    if errors:
        raise ValueError("; ".join(errors))
    return result


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
    """Return ReviewResult; v4 uses at most 5 generic / 8 MoodCut calls.

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
    if review_protocol in ACTOR_PROTOCOLS:
        result.update(review_protocol=review_protocol, actor_reports=[], writer_response=None,
                      verification_kind="programmatic_only", actor_endorsement="not_requested",
                      actor_feedback_status="incomplete",
                      feedback_disposition={"addressed_issue_ids": [], "unaddressed_issue_ids": [], "unaddressed_reasons": {}})
    if review_protocol in (ACTOR_REVIEW_V2, *BOUNDED_PROTOCOLS):
        result.update(actor_confirmations=[], actor_confirmation_status="not_needed",
                      writer_candidate_plan=deepcopy(original))
    if review_protocol in BOUNDED_PROTOCOLS:
        result.update(negotiation_rounds=[], negotiation_round_count=0, negotiation_status="failed",
                      confirmation_issue_ids=[], disputed_issue_ids=[], writer_output_contract=SHOT_WRITER_CONTRACT)
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
        options = {}
        if review_protocol in BOUNDED_PROTOCOLS and name == "actor_revise":
            options["json_schema"] = get_writer_json_schema(second_round=prompt == "negotiate")
        elif review_protocol in BOUNDED_PROTOCOLS and name == "actor_critique":
            options["json_schema"] = get_actor_json_schema(scene, original, payload["actor"]["id"], mode)
        token_limit = MAX_OUTPUT_TOKENS // len(get_reviewers(scene, mode, review_protocol)) if (
            review_protocol == ACTOR_REVIEW_V4 and name in ("actor_critique", "actor_confirm")) else MAX_OUTPUT_TOKENS
        trace("request", stage=name, max_output_tokens=token_limit,
              system=system, user=payload, **({"json_schema_sha256": json_hash(options["json_schema"])} if options else {}))
        response = client.complete_json(stage=name, system=system, user=user,
                                        max_output_tokens=token_limit, **options)
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
        if review_protocol in ACTOR_PROTOCOLS:
            for actor in get_reviewers(scene, mode, review_protocol):
                actor_context = {**deepcopy(context), "actor": deepcopy(actor),
                                 "own_dialogue": _actor_lines(original, actor["id"])}
                response = request("actor_critique", prompt, actor_context)
                result["actor_reports"].append({"actor_id": actor["id"], "response": response})
                # Validate immediately so a bad first actor cannot trigger another call.
                _, actor_errors = _merge_actor_reports(scene, original, mode, result["actor_reports"], partial=True,
                    reviewers=get_reviewers(scene, mode, review_protocol))
                if actor_errors:
                    result["errors"] = actor_errors
                    return result
            result["report"], errors = _merge_actor_reports(scene, original, mode, result["actor_reports"],
                reviewers=get_reviewers(scene, mode, review_protocol))
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
            if review_protocol in BOUNDED_PROTOCOLS:
                result["negotiation_status"] = "no_issues"
            return result
        if review_protocol in BOUNDED_PROTOCOLS:
            return _run_bounded_actor_negotiation(scene, original, manifest, result, context, request,
                mode=mode, project_root=project_root)
        revision_context = {**context, "report": result["report"],
                            "issues_by_shot": _issues_by_shot(original, result["report"])}
        if review_protocol in ACTOR_PROTOCOLS:
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
        if review_protocol in ACTOR_PROTOCOLS:
            result.update(applied)
            if review_protocol == ACTOR_REVIEW_V2:
                result["writer_candidate_plan"] = deepcopy(applied["plan"])
            errors = validate_actor_review_result(scene, original, manifest, result, mode=mode,
                                                  project_root=project_root, require_confirmation=False)
            if errors:
                result.update(status="review_failed", plan=deepcopy(original), errors=errors)
                return result
            if review_protocol == ACTOR_REVIEW_V2:
                omitted = result["feedback_disposition"]["unaddressed_issue_ids"]
                if omitted:
                    result["actor_confirmation_status"] = "pending"
                for actor in scene["characters"]:
                    own = [i for i in result["report"]["issues"]
                           if i["issue_id"] in omitted and i["actor_id"] == actor["id"]]
                    if not own:
                        continue
                    payload = {"scene": deepcopy(scene), "mode": mode, "actor": deepcopy(actor),
                        "initial_plan": deepcopy(original), "revised_plan": deepcopy(applied["plan"]),
                        "initial_plan_sha256": json_hash(original), "candidate_plan_sha256": json_hash(applied["plan"]),
                        "actor_report": deepcopy(next(r["response"] for r in result["actor_reports"] if r["actor_id"] == actor["id"])),
                        "unaddressed_issues": [dict(deepcopy(i), writer_reason=result["feedback_disposition"]["unaddressed_reasons"][i["issue_id"]]) for i in own],
                        "own_original_dialogue": _actor_lines(original, actor["id"]),
                        "own_revised_dialogue": _actor_lines(applied["plan"], actor["id"])}
                    response = request("actor_confirm", "confirm", payload)
                    result["actor_confirmations"].append({"actor_id": actor["id"], "response": response})
                    errors, _ = _actor_confirmation_errors(scene, original, result, mode, partial=True)
                    if errors:
                        result.update(status="review_failed", plan=deepcopy(original), errors=errors,
                                      actor_confirmation_status="failed")
                        return result
                _, disputed = _actor_confirmation_errors(scene, original, result, mode)
                result["actor_confirmation_status"] = "not_needed" if not omitted else "disputed" if disputed else "accepted"
                errors = validate_actor_review_result(scene, original, manifest, result, mode=mode, project_root=project_root)
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
        if review_protocol in BOUNDED_PROTOCOLS:
            if result["negotiation_rounds"]:
                result.update({k: deepcopy(v) for k, v in result["negotiation_rounds"][-1].items() if k in _ROUND_FIELDS})
            result.update(negotiation_status="failed", negotiation_round_count=len(result["negotiation_rounds"]),
                          actor_confirmation_status="failed")
        if review_protocol == ACTOR_REVIEW_V2 and stage == "actor_confirm":
            result["actor_confirmation_status"] = "failed"
        result["plan"] = deepcopy(original)
        result["status"] = "review_failed"
        result["errors"] = [f"{stage}: {type(exc).__name__}: {exc}"]
        trace("error", stage=stage, errors=result["errors"])
        return result
    finally:
        trace("finished", calls=calls, status=result["status"], errors=result["errors"])
