"""Prepare a generated-video pair offline; submit only with explicit paid flags."""
import argparse
from decimal import Decimal
import html
import json
from pathlib import Path
import shutil
import sys

from moodcut.client import BudgetError, OpenRouterError
from moodcut.pipeline import json_hash, read_json, write_json
from moodcut.video_client import OpenRouterVideoClient, check_video_model, fetch_video_models
from moodcut.video_generation import assemble_generated_clips, build_video_bundle


def load_source(run: Path):
    scene = read_json(run / "scene.json")
    manifest = read_json(run / "assets.json")
    initial = read_json(run / "baseline/initial.json")
    candidate = read_json(run / "moodcut/final.json")
    record = read_json(run / "moodcut/run.json")
    baseline = read_json(run / "baseline/run.json")
    review_status = record.get("review_status")
    if review_status not in ("applied", "unchanged", "no_changes") or record.get("run_status") != "completed":
        raise ValueError("A successful source review is required; failed fallback is not a revision")
    for item in (record, baseline):
        if item.get("initial_plan_sha256") != json_hash(initial):
            raise ValueError("Source initial-plan hash mismatch")
    if record.get("final_plan_sha256") != json_hash(candidate):
        raise ValueError("Source candidate-plan hash mismatch")
    if review_status in ("unchanged", "no_changes") and json_hash(candidate) != json_hash(initial):
        raise ValueError("Unchanged review must retain the exact initial plan")
    return scene, initial, candidate, manifest


def write_page(output, bundle, *, films=False):
    escape = lambda text: html.escape(str(text), quote=True)
    paragraphs = ["<!doctype html><html lang='zh-CN'><meta charset='utf-8'>",
                  "<title>MoodCut generated video pair</title><style>body{font:17px system-ui;max-width:1100px;margin:32px auto;padding:0 20px;color:#182028;background:#f5f3ee}video{width:100%;max-height:520px;background:#111}section{margin:30px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere}table{border-collapse:collapse;width:100%}td,th{text-align:left;vertical-align:top;border-bottom:1px solid #bbb;padding:12px}</style>",
                  "<h1>MoodCut · 台词修改前后</h1>",
                  "<p>开发演示；人物图作为参考，画面和声音由视频模型生成。此页展示方法和修改内容，不用于盲评。</p>" if films else
                  "<p><strong>离线请求预览：尚未提交视频生成，当前页面不包含模型生成视频。</strong></p>",
                  f"<p>模型：{escape(bundle['config']['model'])} · 每版 {bundle['duration_s_per_condition']} 秒 · 全部 {sum(len(c['jobs']) for c in bundle['conditions'])} 个镜头请求估算 ${escape(bundle['estimated_cost_usd'])}；不是账户硬费用上限。</p>",
                  "<p>只投影台词修改，原分镜旁白和其他修改不传给视频模型。中文对白、说话人、口型和人物一致性需要人工验收。</p>",
                  "<h2>台词差异</h2><table><tr><th>镜头</th><th>原台词</th><th>修改后</th></tr>"]
    def lines(items):
        return "<br>".join(escape(item["character_id"] + ": " + item["text"]) for item in items) or "（无台词）"
    for change in bundle["dialogue_changes"]:
        paragraphs.append(f"<tr><td>{escape(change['shot_id'])}</td><td>{lines(change['before'])}</td><td>{lines(change['after'])}</td></tr>")
    paragraphs.append("</table><p>被排除的非台词改动：" + escape(", ".join(bundle["ignored_non_dialogue_changes"]) or "无") + "。</p>")
    for condition in bundle["conditions"]:
        label = condition["condition"]
        paragraphs.append("<section><h2>" + ("原台词" if label == "baseline" else "修改后台词") + "</h2>")
        if films:
            paragraphs.append(f"<video controls preload='metadata' src='{label}/film.mp4'></video>")
        else:
            for job in condition["jobs"]:
                paragraphs.append(f"<h3>{escape(job['shot_id'])} · {job['request']['duration']}秒</h3><pre>{escape(job['request']['prompt'])}</pre>")
        paragraphs.append("</section>")
    paragraphs.append("</html>")
    target = output / ("comparison.html" if films else "preview.html")
    with target.open("x", encoding="utf-8") as stream:
        stream.write("\n".join(paragraphs))
    return target


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--run", help="Existing planning/review block; never reruns text models")
    group.add_argument("--resume-job", help="GET-only resume of one saved video job directory")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--config", default="configs/video.json")
    parser.add_argument("--output", help="New directory under project runs/")
    parser.add_argument("--allow-paid", action="store_true")
    parser.add_argument("--max-cost-usd")
    args = parser.parse_args(argv)
    root = Path(args.project_root).resolve()
    resolve = lambda path: (root / path).resolve()
    config = read_json(resolve(args.config))
    if args.resume_job:
        if args.allow_paid:
            raise ValueError("Resume is GET-only; omit --allow-paid")
        client = OpenRouterVideoClient(config, max_cost_usd="0.01")
        result = client.resume(str(resolve(args.resume_job)))
        print(json.dumps(result, ensure_ascii=False))
        return 0
    if not args.output:
        raise ValueError("--output is required for request preparation")
    output = resolve(args.output)
    output.relative_to(root / "runs")
    if output == root / "runs" or output.exists():
        raise FileExistsError("Choose a new output directory under runs/")
    source = load_source(resolve(args.run))
    bundle = build_video_bundle(*source, config, project_root=str(root))
    client = None
    if args.allow_paid:
        if not args.max_cost_usd:
            raise BudgetError("--max-cost-usd is required for paid video generation")
        limit = Decimal(args.max_cost_usd)
        if not limit.is_finite() or limit < Decimal(bundle["estimated_cost_usd"]):
            raise BudgetError("Budget is smaller than the complete pair's estimate")
        for tool in ("ffmpeg", "ffprobe"):
            if not shutil.which(tool):
                raise ValueError(f"Missing {tool}; no job submitted")
        client = OpenRouterVideoClient(config, allow_paid=True, max_cost_usd=args.max_cost_usd)
        if not client.credentials_available:
            raise ValueError("Set OPENROUTER_API_KEY in the process environment")
        models = fetch_video_models()
        check_video_model(config, models)
        bundle["live_model_preflight"] = next(m for m in models if m["id"] == config["model"])
    elif args.max_cost_usd:
        raise ValueError("Budget alone does not enable paid generation; use the default offline preview")
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "bundle.json", bundle)
    preview = write_page(output, bundle)
    if client is None:
        print(json.dumps({"status": "prepared_offline", "generation_posts": 0,
                          "estimated_cost_usd": bundle["estimated_cost_usd"], "preview": str(preview)}, ensure_ascii=False))
        return 0

    summary = {"status": "in_progress", "source_kind": "derived_development_video_pair",
               "generation_posts": 0, "provider_cost_usd": "0", "conditions": []}
    cache = {}
    try:
        for condition in bundle["conditions"]:
            directory = output / condition["condition"]
            directory.mkdir()
            record = {"condition": condition["condition"], "status": "in_progress", "jobs": []}
            summary["conditions"].append(record)
            paths, durations = [], []
            for index, job in enumerate(condition["jobs"], 1):
                fingerprint = job["request_sha256"]
                if fingerprint in cache:
                    receipt = {**cache[fingerprint], "reused_identical_request": True}
                else:
                    receipt = client.generate(job["request"], out_dir=str(directory / f"shot-{index:02d}"))
                    cache[fingerprint] = receipt
                record["jobs"].append({"shot_id": job["shot_id"], **receipt})
                paths.append(receipt["video_path"])
                durations.append(job["request"]["duration"])
                if client.spent_usd is None:
                    raise BudgetError("Video downloaded but charge unknown; stop and reconcile before proceeding")
            record["media"] = assemble_generated_clips(paths, durations=durations, out_path=str(directory / "film.mp4"))
            record["status"] = "assembled_requires_manual_inspection"
        summary["status"] = "assembled_requires_manual_inspection"
        page = write_page(output, bundle, films=True)
        summary["comparison_path"] = str(page)
    except Exception:
        summary["status"] = "failed_or_interrupted"
        raise
    finally:
        summary["generation_posts"] = client.post_attempts
        summary["provider_cost_usd"] = client.spent_usd
        write_json(output / "generation.json", summary)
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, BudgetError, OpenRouterError) as error:
        # Provider errors are sanitized at the transport boundary.
        print(f"Video generation stopped: {error}", file=sys.stderr)
        raise SystemExit(1)
