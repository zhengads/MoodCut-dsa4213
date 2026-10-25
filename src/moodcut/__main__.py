"""MoodCut CLI: offline by default, explicit opt-in for metered OpenRouter calls."""

import argparse
from copy import deepcopy
import csv
import hashlib
import json
import logging
from pathlib import Path
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="moodcut", description="MoodCut: Emotion-aware storyboard review and constrained revision.")
    parser.add_argument("--version", action="version", version="MoodCut 0.0.0")
    commands = parser.add_subparsers(dest="command")

    def common(name, help_text):
        sub = commands.add_parser(name, help=help_text)
        sub.add_argument("--project-root", default=".")
        return sub

    def inputs(sub, *, defaults=False, plan=False):
        sub.add_argument("--scene", default="tests/fixtures/scene.json" if defaults else None, required=not defaults)
        sub.add_argument("--assets", default="tests/fixtures/assets.json" if defaults else None, required=not defaults)
        if plan:
            sub.add_argument("--plan", required=True)

    def client_options(sub):
        mode = sub.add_mutually_exclusive_group()
        mode.add_argument("--mock", action="store_true", help="Use offline synthetic responses (default).")
        mode.add_argument("--allow-paid", action="store_true", help="Explicitly enable live OpenRouter requests.")
        sub.add_argument("--max-cost-usd", type=float)
        sub.add_argument("--model-config", default="configs/model.json")
        sub.add_argument("--responses", help="Offline JSON response list; never usable with --allow-paid.")

    plan = common("plan", "Generate an initial storyboard plan.")
    inputs(plan)
    client_options(plan)
    plan.add_argument("--output", required=True, help="New ShotPlan JSON path; trace/calls use sibling paths.")

    review = common("review", "Review and revise an existing storyboard.")
    inputs(review, plan=True)
    client_options(review)
    review.add_argument("--mode", required=True, choices=("generic_review", "moodcut"))
    review.add_argument("--output", required=True, help="New ReviewResult JSON path.")

    render = common("render", "Render a fixed-image animatic without model calls.")
    render.add_argument("--plan", required=True)
    render.add_argument("--assets", required=True)
    render.add_argument("--font")
    render.add_argument("--output", required=True, help="New render output directory.")

    smoke = common("smoke", "Check all three JSON paths offline, without video rendering.")
    inputs(smoke, defaults=True)
    smoke.add_argument("--mock", action="store_true", help="Offline mode is always enabled.")
    smoke.add_argument("--responses", help="Optional offline JSON response list.")
    smoke.add_argument("--output", required=True)

    run = common("run", "Plan once and run all three conditions; default offline.")
    inputs(run, defaults=True)
    client_options(run)
    run.add_argument("--font")
    run.add_argument("--no-render", action="store_true")
    run.add_argument("--output", required=True, help="New block output directory.")
    run.add_argument("--replicate", type=int, default=1)
    run.add_argument("--cache-dir", help="Optional verified initial-plan cache.")
    run.add_argument("--source-kind", choices=("synthetic", "development", "formal"), default="development")
    run.add_argument("--output-mode", choices=("animatic", "generated"), default="animatic")
    run.add_argument("--source-block", help="Existing generated script block.json (or its directory); no replanning.")
    run.add_argument("--shot-id", help="Prepare only this original shot in all three generated conditions.")
    run.add_argument("--pricing-config", help="Local video pricing JSON; no live price lookup.")

    execution = common("execute-generated", "Execute saved three-condition requests; default collects offline without HTTP.")
    execution.add_argument("--preparation", required=True)
    execution.add_argument("--pricing-config", required=True)
    execution.add_argument("--output", required=True, help="New execution directory; no automatic restart.")
    execution.add_argument("--media-origin", required=True, choices=("synthetic", "provided_local"))
    execution.add_argument("--allow-paid", action="store_true", help="Enable video HTTP only after separate approval, including GET recovery.")
    execution.add_argument("--max-cost-usd", help="Video budget including prior task charges on continuation; text fees excluded; GET has no hard cap.")
    prior = execution.add_mutually_exclusive_group()
    prior.add_argument("--resume-execution", help="Earlier execution directory; recovery never creates new tasks.")
    prior.add_argument("--continue-execution", help="Explicitly continue only unsubmitted jobs after all attempted tasks and charges reconcile.")
    execution.add_argument("--resume-condition", choices=("baseline", "generic_review", "moodcut"))
    execution.add_argument("--resume-shot-id", help="Original shot ID of one owned task to recover by GET only.")

    records = common("assemble-generated-records", "Assemble local video receipts and accounting; no network.")
    records.add_argument("--preparation", required=True, help="Existing generated request-preparation directory.")
    records.add_argument("--evidence", required=True, help="Local three-condition receipt/media manifest JSON.")
    records.add_argument("--pricing-config", required=True, help="Same local pricing JSON used in preparation.")
    records.add_argument("--output", required=True, help="New record output directory; never overwrite.")

    qualification = common("qualify-generated-records", "Recheck saved generated evidence offline; keep export disabled.")
    qualification.add_argument("--records", required=True, help="Final P1 record directory or block.json.")
    qualification.add_argument("--pricing-config", required=True, help="Same local pricing JSON used in preparation.")
    qualification.add_argument("--output", required=True, help="New qualification report directory; never overwrite.")

    imported = common("import-synopsis", "Normalize a local MovieAgent synopsis without selecting scenes.")
    imported.add_argument("--input", required=True)
    imported.add_argument("--output", required=True)

    evaluate = common("evaluate", "Prepare assignments or summarize supplied human ratings offline.")
    evaluate.add_argument("--config", default="configs/experiment.json")
    evaluate.add_argument("--dry-run", action="store_true", help="Enumerate assignments only; no execution or requests.")
    evaluate.add_argument("--records", nargs="+", help="Run JSON, block JSON or JSON list paths.")
    evaluate.add_argument("--blind-output", help="New anonymous clip export directory.")
    evaluate.add_argument("--ratings", help="Completed human ratings CSV, never generated by this command.")
    evaluate.add_argument("--private-key", help="PRIVATE/private_key.csv from the matching blind export.")
    evaluate.add_argument("--pricing-config", help="Required for generated evidence rechecks; local JSON only.")
    evaluate.add_argument("--seed", type=int, default=0)
    evaluate.add_argument("--output", help="New assignment/summary JSON; otherwise prints JSON.")

    check = common("check-client", "Check local OpenRouter configuration; no requests.")
    check.add_argument("--config", default="configs/model.json")
    check.add_argument("--max-cost-usd", type=float, required=True)
    return parser


def _path(root, value):
    candidate = Path(value)
    return candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()


def _new_outputs(*paths):
    for path in paths:
        if path.exists():
            raise FileExistsError(f"Output already exists; choose a new path: {path}")


def _load_inputs(args, root):
    from .pipeline import read_json
    from .validation import validate_scene
    scene, manifest = read_json(_path(root, args.scene)), read_json(_path(root, args.assets))
    errors = validate_scene(scene, manifest, project_root=root)
    if errors:
        raise ValueError("; ".join(errors))
    return scene, manifest


def _client(args, root, scene, manifest, *, planning=False, initial_plan=None, conditions=()):
    from .client import FakeClient, OpenRouterClient
    from .pipeline import make_mock_client, read_json
    paid = getattr(args, "allow_paid", False)
    responses = getattr(args, "responses", None)
    if paid:
        if responses:
            raise ValueError("--responses cannot be used with --allow-paid")
        if args.max_cost_usd is None:
            raise ValueError("--allow-paid requires --max-cost-usd")
        try:
            return OpenRouterClient.from_env(_path(root, args.model_config), allow_paid=True,
                                             max_cost_usd=args.max_cost_usd)
        except (ValueError, OSError) as exc:
            raise ValueError("Invalid OpenRouter configuration; check environment key, model, prices and positive budget") from exc
    if getattr(args, "max_cost_usd", None) is not None:
        raise ValueError("--max-cost-usd requires --allow-paid; use --mock for offline runs")
    if responses:
        return FakeClient(read_json(_path(root, responses)))
    return make_mock_client(scene, manifest, include_planning=planning,
                            initial_plan=initial_plan, conditions=conditions)


def _plan(args, root):
    from .client import FakeClient, capture_text_responses
    from .pipeline import usage_totals, write_json
    from .planner import PlanningError, make_plan_with_trace
    output = _path(root, args.output)
    trace = output.with_suffix(".trace.json")
    calls = output.with_suffix(".calls.json")
    error = output.with_suffix(".error.json")
    if len({output, trace, calls, error}) != 4:
        raise ValueError("--output must have an ordinary filename ending in .json")
    _new_outputs(output, trace, calls, error)
    scene, manifest = _load_inputs(args, root)
    client = _client(args, root, scene, manifest, planning=True)
    status = 0
    try:
        with capture_text_responses(output.parent):
            result = make_plan_with_trace(scene, manifest, client, project_root=root)
        write_json(output, result["plan"])
        write_json(trace, {"source_kind": "synthetic" if isinstance(client, FakeClient) else "development",
                           "mock": isinstance(client, FakeClient), **result})
    except PlanningError as exc:
        write_json(error, {"status": "planning_failed", "stage": exc.stage,
                           "errors": exc.errors, "raw_responses": exc.raw_responses})
        print(f"Planning failed at {exc.stage}; diagnostics: {error}", file=sys.stderr)
        status = 1
    finally:
        write_json(calls, {**usage_totals(client.calls, mock=isinstance(client, FakeClient)),
                           "call_records": client.calls})
    if status == 0:
        print(f"Plan saved: {output}")
    return status


def _review(args, root):
    from .client import FakeClient, capture_text_responses
    from .pipeline import read_json, usage_totals, write_json
    from .reviewer import review_and_revise
    from .validation import validate_plan
    output = _path(root, args.output)
    calls, trace = output.with_suffix(".calls.json"), output.with_suffix(".trace.jsonl")
    if len({output, calls, trace}) != 3:
        raise ValueError("--output must have an ordinary filename ending in .json")
    _new_outputs(output, calls, trace)
    scene, manifest = _load_inputs(args, root)
    plan = read_json(_path(root, args.plan))
    errors = validate_plan(scene, plan, manifest, project_root=root)
    if errors:
        raise ValueError("; ".join(errors))
    client = _client(args, root, scene, manifest, initial_plan=plan, conditions=(args.mode,))
    output.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("moodcut.review.trace")
    prior_level = logger.level
    handler = logging.FileHandler(trace, mode="x", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    try:
        with capture_text_responses(output.parent):
            result = review_and_revise(scene, plan, manifest, client, mode=args.mode, project_root=root)
        write_json(output, result)
    finally:
        logger.removeHandler(handler)
        handler.close()
        logger.setLevel(prior_level)
        write_json(calls, {**usage_totals(client.calls, mock=isinstance(client, FakeClient)),
                           "call_records": client.calls, "mock": isinstance(client, FakeClient)})
    print(f"Review saved ({result['status']}): {output}")
    return 1 if result["status"] in ("review_failed", "rejected") else 0


def _run(args, root):
    from .pipeline import CONDITIONS, run_experiment
    output = _path(root, args.output)
    _new_outputs(output)
    if getattr(args, "output_mode", "animatic") == "generated":
        from .pipeline import prepare_generated_run
        if not args.source_block:
            raise ValueError("generated requires --source-block; prepare scripts first")
        if (args.allow_paid or args.max_cost_usd is not None or args.responses or args.cache_dir
                or args.font or args.no_render or args.replicate != 1 or args.source_kind != "development"
                or args.scene != "tests/fixtures/scene.json" or args.assets != "tests/fixtures/assets.json"
                or args.model_config != "configs/model.json"):
            raise ValueError("generated preparation is offline and reads saved block inputs; do not pass live/planning/render overrides")
        result = prepare_generated_run(_path(root, args.source_block), out_dir=output, project_root=root,
                                       shot_id=args.shot_id, pricing_config=_path(root, args.pricing_config or "configs/video.json"))
        print(f"Requests prepared offline (no video submitted): {output / 'preparation.json'}")
        return 0 if result["status"] == "prepared_offline" else 1
    if any(getattr(args, option, None) is not None for option in ("source_block", "shot_id", "pricing_config")):
        raise ValueError("--source-block/--shot-id/--pricing-config require explicit generated mode")
    scene, manifest = _load_inputs(args, root)
    render = args.command == "run" and not args.no_render
    font = None
    if render:
        from .pipeline import resolve_render_dependencies
        font = resolve_render_dependencies(project_root=root, font_path=args.font)
    # None lets the pipeline place mock planning responses correctly on a cache hit.
    if getattr(args, "allow_paid", False) or getattr(args, "responses", None):
        client = _client(args, root, scene, manifest, planning=True, conditions=CONDITIONS)
    else:
        if getattr(args, "max_cost_usd", None) is not None:
            raise ValueError("--max-cost-usd requires --allow-paid")
        client = None
    block = run_experiment(scene, manifest, client, out_dir=str(output), project_root=str(root),
                           font_path=font, render=render, replicate=getattr(args, "replicate", 1),
                           cache_dir=str(_path(root, args.cache_dir)) if getattr(args, "cache_dir", None) else None,
                           source_kind=getattr(args, "source_kind", "development"))
    print(f"Block {block['status']}: {output / 'block.json'}")
    return 0 if block["status"] == "completed" else 1


def _records(paths, root):
    from .pipeline import read_json
    records = []
    for path in paths:
        source = _path(root, path)
        data = read_json(source / "block.json" if source.is_dir() else source)
        if isinstance(data, dict) and "runs" in data:
            data = data["runs"]
        records.extend(data if isinstance(data, list) else [data])
    return records


def _csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _block_accounting(paths, root, records):
    """Keep shared planning separate, then include it exactly once per block."""
    from .pipeline import read_json
    blocks = {}
    for path in paths:
        source = _path(root, path)
        data = read_json(source / "block.json" if source.is_dir() else source)
        if isinstance(data, dict) and "runs" in data and "planning" in data:
            block_id = data["block_id"]
            if block_id in blocks:
                raise ValueError("Duplicate block ledger; supply each block.json once")
            blocks[block_id] = data
    expected = {row["block_id"] for row in records}
    complete = expected == set(blocks)
    fields = ("calls", "real_http_calls", "input_tokens", "output_tokens",
              "estimated_cost_usd", "provider_cost_usd")

    def totals(rows):
        return {field: (None if any(row.get(field) is None for row in rows)
                        else sum(row[field] for row in rows)) for field in fields}

    planning = [data["planning"] for data in blocks.values()]
    return {"complete": complete, "blocks_with_planning": len(blocks),
            "blocks_in_records": len(expected), "shared_planning": totals(planning),
            "all_phases": totals([*planning, *records]) if complete else None,
            "note": "Each block.json includes shared planning once; run.json alone cannot reconstruct it."}


def _evaluate(args, root):
    from .evaluation import (build_assignments, export_blind_items, summarize,
                             export_generated_blind_items, summarize_generated_records)
    from .pipeline import read_json, write_json
    output = _path(root, args.output) if args.output else None
    if output:
        _new_outputs(output)
    if args.dry_run:
        if args.records or args.ratings or args.blind_output or args.private_key or args.pricing_config:
            raise ValueError("--dry-run only enumerates config assignments")
        config = read_json(_path(root, args.config))
        if not isinstance(config, dict) or not isinstance(config.get("scenes"), list) or not config["scenes"]:
            raise ValueError("Experiment config requires a non-empty scenes path list")
        scenes = [read_json(_path(root, path)) for path in config["scenes"]]
        assignments = build_assignments(scenes, replicates=config.get("replicates", 1),
                                       tones=config.get("tones"), conditions=config.get("conditions"))
        result = {"status": "dry_run", "config_status": config.get("status"),
                  "paid_calls": 0, "planned_runs": len(assignments), "assignments": assignments,
                  "note": "Assignments only; this does not approve formal samples, ratings, models or costs."}
    else:
        if not args.records:
            raise ValueError("Use --dry-run or provide --records for offline export/summary")
        if args.ratings and not args.private_key:
            raise ValueError("--ratings requires the matching --private-key")
        if args.private_key and not args.ratings:
            raise ValueError("--private-key is used only with --ratings")
        records = _records(args.records, root)
        if args.blind_output and args.ratings:
            raise ValueError("Export blind items and summarize completed ratings in separate commands")
        if (any(row.get("output_mode") == "generated" for row in records)
                and (args.blind_output or args.ratings or args.pricing_config)):
            if not args.pricing_config:
                raise ValueError("Generated evaluation requires --pricing-config for fresh qualification")
            options = dict(pricing_config=_path(root, args.pricing_config), project_root=root)
            paths = [_path(root, p) for p in args.records]
            if args.blind_output:
                result = export_generated_blind_items(paths, out_dir=_path(root, args.blind_output),
                                                      seed=args.seed, **options)
            else:
                result = summarize_generated_records(paths, _csv(_path(root, args.ratings)) if args.ratings else [],
                    private_key=_path(root, args.private_key) if args.private_key else None, **options)
        elif args.blind_output:
            result = export_blind_items(records, out_dir=str(_path(root, args.blind_output)), seed=args.seed)
        else:
            ratings = []
            if args.ratings:
                key = _csv(_path(root, args.private_key))
                records_by_id = {row["run_id"]: row for row in records}
                mapping, seen = {}, set()
                for row in key:
                    run_id, item_id = row.get("run_id"), row.get("item_id")
                    if not run_id or not item_id or run_id in mapping or item_id in seen:
                        raise ValueError("Private key has missing or duplicate run/item IDs")
                    if run_id not in records_by_id:
                        raise ValueError("Private key contains unknown run IDs")
                    record = records_by_id[run_id]
                    expected = {field: record.get(field) for field in
                                ("block_id", "scene_id", "replicate", "condition", "initial_plan_sha256")}
                    expected.update(target_tone=record.get("tone"),
                                    source_kind=record.get("source_kind", "unspecified"))
                    if any(row.get(field) != str(value) for field, value in expected.items()):
                        raise ValueError("Private key metadata does not match the supplied run records")
                    video = Path(record.get("video_path", ""))
                    if (not video.is_file() or not row.get("video_sha256")
                            or hashlib.sha256(video.read_bytes()).hexdigest() != row["video_sha256"]):
                        raise ValueError("Private key video hash does not match the supplied clip")
                    mapping[run_id] = item_id
                    seen.add(item_id)
                records = [dict(row, item_id=mapping[row["run_id"]]) if row["run_id"] in mapping else deepcopy(row)
                           for row in records]
                ratings = _csv(_path(root, args.ratings))
            result = summarize(records, ratings)
            result["block_ledger_accounting"] = _block_accounting(args.records, root, records)
    if output:
        write_json(output, result)
        print(f"Evaluation artifact saved: {output}")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    root = Path(args.project_root).resolve()
    try:
        if args.command == "check-client":
            from .client import OpenRouterClient
            try:
                client = OpenRouterClient.from_env(_path(root, args.config), max_cost_usd=args.max_cost_usd)
            except (ValueError, OSError) as exc:
                parser.error("Invalid OpenRouter configuration; check key, model, prices and budget")
            print(f"OpenRouter configuration valid for {client.model}; no network request sent.")
            return 0
        if args.command == "plan":
            return _plan(args, root)
        if args.command == "review":
            return _review(args, root)
        if args.command in ("smoke", "run"):
            return _run(args, root)
        if args.command == "execute-generated":
            from .pipeline import execute_generated_run
            result = execute_generated_run(_path(root, args.preparation),
                out_dir=_path(root, args.output), pricing_config=_path(root, args.pricing_config), project_root=root,
                allow_paid=args.allow_paid, max_cost_usd=args.max_cost_usd, media_origin=args.media_origin,
                resume_execution=_path(root, args.resume_execution) if args.resume_execution else None,
                resume_condition=args.resume_condition, resume_shot_id=args.resume_shot_id,
                continue_execution=_path(root, args.continue_execution) if args.continue_execution else None)
            activity = "video HTTP enabled" if result["video_http_enabled"] else "no video HTTP attempted"
            print(f"Generated execution {result['status']}: {_path(root, args.output)}; {activity}.")
            return 1 if result["status"] in ("stopped", "incomplete") else 0
        if args.command == "assemble-generated-records":
            from .pipeline import assemble_generated_records
            result = assemble_generated_records(_path(root, args.preparation), evidence=_path(root, args.evidence),
                out_dir=_path(root, args.output), pricing_config=_path(root, args.pricing_config), project_root=root)
            print(f"Generated records {result['status']}: {_path(root, args.output)}; no network request sent.")
            return 1 if result["status"] == "failed" else 0
        if args.command == "qualify-generated-records":
            from .evaluation import qualify_generated_records
            from .pipeline import write_json
            output = _path(root, args.output)
            _new_outputs(output)
            result = qualify_generated_records(_path(root, args.records),
                pricing_config=_path(root, args.pricing_config), project_root=root)
            output.mkdir(parents=True, exist_ok=False)
            write_json(output / "qualification.json", result)
            print(f"Offline qualification {result['comparison_status']}: {output / 'qualification.json'}; export remains disabled.")
            return 0 if result["comparison_status"] == "eligible" else 1
        if args.command == "render":
            from .pipeline import read_json, resolve_render_dependencies, write_json
            from .renderer import render_plan
            output = _path(root, args.output)
            _new_outputs(output)
            font = resolve_render_dependencies(project_root=root, font_path=args.font)
            result = render_plan(read_json(_path(root, args.plan)), read_json(_path(root, args.assets)),
                                 project_root=str(root), out_dir=str(output), font_path=font)
            write_json(output / "render.json", result)
            print(f"Render {result['status']}: {output}")
            return 0 if result["status"] == "rendered" else 1
        if args.command == "import-synopsis":
            from .importer import import_synopsis
            from .pipeline import write_json
            output = _path(root, args.output)
            _new_outputs(output)
            write_json(output, import_synopsis(_path(root, args.input)))
            print(f"Synopsis imported: {output}")
            return 0
        if args.command == "evaluate":
            return _evaluate(args, root)
    except (ValueError, TypeError, KeyError, OSError, RuntimeError) as exc:
        print(f"MoodCut failed: {exc}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
