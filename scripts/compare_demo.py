"""Create an offline video/shot comparison from one existing MoodCut block.

No API calls, rendering, scoring or plan edits. Open the generated HTML locally.
"""

import argparse
from html import escape
import json
import os
from pathlib import Path
import sys
from urllib.parse import quote

from moodcut.pipeline import CONDITIONS, json_hash, read_json


LABELS = {"baseline": "初稿 / baseline", "generic_review": "通用审查 / generic_review",
          "moodcut": "情绪审查 / moodcut"}


def plan_changes(before, after):
    """List actual field differences, including unexpected structural changes."""
    if not isinstance(before, dict) or not isinstance(after, dict):
        return None
    changes = []
    for field in sorted((set(before) | set(after)) - {"shots"}):
        if before.get(field) != after.get(field):
            changes.append({"shot_id": "plan", "field": field,
                            "before": before.get(field), "after": after.get(field)})
    left, right = before.get("shots", []), after.get("shots", [])
    before_ids, after_ids = [s["shot_id"] for s in left], [s["shot_id"] for s in right]
    if before_ids != after_ids:
        changes.append({"shot_id": "plan", "field": "shot_order",
                        "before": before_ids, "after": after_ids})
    left, right = {s["shot_id"]: s for s in left}, {s["shot_id"]: s for s in right}
    for shot_id in dict.fromkeys([*before_ids, *after_ids]):
        a, b = left.get(shot_id), right.get(shot_id)
        if a is None or b is None:
            changes.append({"shot_id": shot_id, "field": "shot", "before": a, "after": b})
            continue
        for field in sorted(set(a) | set(b)):
            if a.get(field) != b.get(field):
                changes.append({"shot_id": shot_id, "field": field,
                                "before": a.get(field), "after": b.get(field)})
    return changes


def collect_comparison(run_dir):
    root = Path(run_dir).resolve()
    block = read_json(root / "block.json")
    rows = block["runs"]
    if len(rows) != 3 or {r["condition"] for r in rows} != set(CONDITIONS):
        raise ValueError("Comparison needs one block with all three condition records")
    hashes = {r.get("initial_plan_sha256") for r in rows}
    if len(hashes) != 1 or block.get("initial_plan_sha256") not in hashes:
        raise ValueError("Initial plan hash differs between conditions")
    conditions = []
    for name in CONDITIONS:
        record = next(r for r in rows if r["condition"] == name)
        folder = root / name
        initial = read_json(folder / "initial.json")
        if (json_hash(initial) if initial is not None else None) != record.get("initial_plan_sha256"):
            raise ValueError(f"{name}: initial artifact does not match recorded hash")
        final_file = folder / "final.json"
        final = read_json(final_file) if final_file.exists() else None
        if record.get("final_plan_sha256") is not None and json_hash(final) != record["final_plan_sha256"]:
            raise ValueError(f"{name}: final artifact does not match recorded hash")
        review_file = folder / "review.json"
        review = read_json(review_file) if review_file.exists() else None
        conditions.append({"record": record, "review": review,
                           "changes": plan_changes(initial, final)})
    return block, conditions


def _json(value):
    return escape(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False))


def _total(rows, field):
    return None if any(r.get(field) is None for r in rows) else sum(r[field] for r in rows)


def write_comparison(run_dir, output):
    """Create a local HTML artifact exclusively; preserve existing results."""
    root, output = Path(run_dir).resolve(), Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"Comparison output already exists: {output}")
    block, conditions = collect_comparison(root)
    cards, sections = [], []
    for item in conditions:
        row, review, changes = item["record"], item["review"], item["changes"]
        name = row["condition"]
        video = "<p>无已生成视频；请检查运行错误。</p>"
        if row.get("render_status") == "rendered" and row.get("video_path"):
            path = Path(row["video_path"]).resolve()
            if not path.is_relative_to(root):
                raise ValueError("Video path must remain inside the supplied run directory")
            if path.is_file():
                url = quote(os.path.relpath(path, output.parent).replace(os.sep, "/"), safe="/.")
                video = f'<video controls preload="metadata" src="{escape(url, quote=True)}"></video>'
        status = {field: row.get(field) for field in ("run_status", "review_status", "render_status",
                  "calls", "real_http_calls", "provider_cost_usd", "errors")}
        cards.append(f"<article><h2>{LABELS[name]}</h2>{video}<pre>{_json(status)}</pre></article>")
        if name == "baseline":
            continue
        if changes is None:
            differences = "<p>无可比较的最终分镜，不能将失败记为没有变化。</p>"
        elif not changes:
            differences = "<p>最终分镜与初稿一致，没有实际字段变化。</p>"
        else:
            cells = "".join(f"<tr><td>{escape(str(c['shot_id']))}<br>{escape(c['field'])}</td>"
                            f"<td><pre>{_json(c['before'])}</pre></td>"
                            f"<td><pre>{_json(c['after'])}</pre></td></tr>" for c in changes)
            differences = ("<table><thead><tr><th>镜头 / 字段</th><th>修改前</th><th>修改后</th>"
                           f"</tr></thead><tbody>{cells}</tbody></table>")
        # These are model opinions and verification records, never human scores.
        details = "<p>无审查记录。</p>" if review is None else (
            f"<h3>审查意见</h3><pre>{_json(review.get('report'))}</pre>"
            f"<details><summary>补丁、复查与错误</summary><pre>{_json({k: review.get(k) for k in ('status','patch','verification','errors')})}</pre></details>")
        sections.append(f"<section><h2>{LABELS[name]}：逐镜头变化</h2>{differences}{details}</section>")
    usage = [block["planning"], *block["runs"]]
    totals = {field: _total(usage, field) for field in
              ("calls", "real_http_calls", "estimated_cost_usd", "provider_cost_usd")}
    meta = {"model_id": block.get("model_id"), "source_kind": block.get("source_kind"),
            "mock": block.get("mock"), "status": block.get("status"),
            "shared_initial_plan_sha256": block.get("initial_plan_sha256"),
            "all_phases_planning_counted_once": totals, "planning_errors": block["planning"].get("errors")}
    source = ("离线 mock 软件夹具，不是实际模型结果。" if block.get("mock") is True else
              "真实客户端记录；实际请求数、费用与失败状态见下方账目。" if block.get("mock") is False else
              "来源标记缺失，请先核对运行记录。")
    html = """<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>MoodCut 前后对比</title>
<style>body{font-family:system-ui,sans-serif;max-width:1500px;margin:32px auto;padding:0 20px;color:#202020;background:#f7f7f5}
.videos{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}article,section{background:white;border:1px solid #ddd;padding:16px;margin:16px 0}
video{width:100%;background:#202020}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}table{border-collapse:collapse;width:100%;table-layout:fixed}
th,td{text-align:left;vertical-align:top;border:1px solid #ddd;padding:12px}th:first-child{width:14%}summary{cursor:pointer}
@media(max-width:900px){.videos{grid-template-columns:1fr}body{margin:16px auto}}</style>
<h1>MoodCut：初稿与两类审查对比</h1>
<p>只显示实际视频、字段差异与模型意见。模型复查不是人工评分，字段变化也不等于情绪表达改善。固定图片不会产生新动作。</p>
""" + f"<p><strong>{source}</strong></p><pre>{_json(meta)}</pre><div class='videos'>{''.join(cards)}</div>{''.join(sections)}</html>"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(html)
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, help="Existing run directory containing block.json")
    parser.add_argument("--output", help="New HTML file; default <run>/comparison.html")
    args = parser.parse_args(argv)
    try:
        output = write_comparison(args.run, args.output or Path(args.run) / "comparison.html")
    except (ValueError, TypeError, KeyError, OSError) as exc:
        print(f"Comparison failed: {exc}", file=sys.stderr)
        return 1
    print(f"Comparison saved: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
