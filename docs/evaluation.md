# MoodCut 资格、盲评与评价

[文档状态](README.md) · [使用命令](usage.md#检查与评价生成视频) · [VBench 工具](vbench.md) · [历史验收](history/evaluation-acceptance.md)

本页维护输入要求、评分口径和证据边界。真实试跑记录在 pilots/；人工评分、模型自评、媒体完整性和 VBench 分数分开解释。PR #58 的历史视频审计与图像质量结果仍为独立待合并增量，不据此宣称六故事实验完成。

[S02 / S03 teammate handoff](evaluation-handoffs/s02-s03-20261025/README.md): portable inputs and offline checks, awaiting v4 confirmation and execution scope.

## 软件流程验证

从仓库根目录运行，先配置 FFmpeg/ffprobe 与字体，使用新输出目录：

```powershell
.venv/Scripts/python scripts/verify_workflow.py --output runs/workflow-check-01
```

该入口检查三条件 mock 视频、匿名导出、无评分覆盖、任务 dry-run 和 generated 集成。查看 verification.json、阶段日志及 generated-tests.xml。软件视频、回执和评分夹具不作为独立效果证据；历史实测和贡献署名见[验收记录](history/evaluation-acceptance.md)。

## 方法身份

同一比较使用一致的协议和 writer contract。v3 的有效最终分歧可保留 disputed 状态进入准备，不自动计为成功、失败或人工认可；详见[演员方法](ACTOR_REVIEW_METHOD.md)。公开对比页暴露条件、目标和台词，不用于盲评分发。

## 配对人工评价

主 CLI 的 evaluate 完全离线，不启动模型。configs/experiment.json 是开发分配示例，包含已有软件夹具；--dry-run 仅列出 scene×tone×replicate×condition，不改变原 SceneInput，也不自动批量生成。实际生成使用 run 命令，一次一个明确输入的 block。configs/pilot.json 保留原 VBench 提议配置，不能作为人工评价的 scene 路径配置。

```bash
python -m moodcut evaluate --config configs/experiment.json --dry-run
python -m moodcut evaluate --records runs/demo/block.json --blind-output runs/blind-demo
python -m moodcut evaluate --records runs/demo/block.json --output runs/demo/coverage.json
python -m moodcut evaluate --records runs/demo/block.json --ratings runs/blind-demo/public/ratings.csv --private-key runs/blind-demo/PRIVATE/private_key.csv --output runs/demo/human-summary.json
```

输出目录/文件必须新建。只分发 public/，包含匿名 MP4、blind_items.csv 和空 ratings.csv；PRIVATE/private_key.csv 含条件、目标 tone、初稿与视频 SHA-256，单独保管。匿名导出只核查已有非空 MP4，不能代替实际播放检查。填写评分前，团队明确评价者分配，避免同一人连续看同一故事的不同版本；导出本身不自动保证实验盲法。默认 mock 材料只用于操作检查。

每个已完成的评分行需 rater_id（匿名）、item_id、perceived_tone（affectionate/suspicious/hostile/tense/uncertain）、confidence、naturalness、story_clarity、overstatement；后四项必须为 1–5 整数。当前六故事 v2 的观看选项采用亲密 affectionate／敌对 hostile／紧张 tense／无法判断 uncertain；解析器额外保留 suspicious 以读取旧协议，不能将旧怀疑评分改成紧张。新增 tense 混淆矩阵行列，命中率、uncertain 未命中、clip 等权、共同 block 差值和失败覆盖的公式不变。不能把空模板交给汇总；只汇总已完成行，未评分 clip 仍由原始记录留在覆盖分母。重复 rater/item、未知 item、旧映射或视频哈希不符均报错。实际评分解释和正式样本由团队确认，程序不代填答案。

统计实现 summarize：每个有评分 clip 先算其 tone 命中比例和各 1–5 项均值，再按 clip 等权汇总；多评分 clip 不获得更大权重。uncertain 计作 tone 未命中并单列。混淆矩阵是 rating 次数，与 clip 等权均值的分母不同。自然度、剧情清楚度、过度表达和 confidence 分列，零评分分母返回 null。它们衡量被观看并评分的成片，不证明所有生成尝试有效，也不把 Agent verification 当人工结果。

coverage 保留所有提供的运行：planned_runs、rendered_runs、review_failed/rejected、缺失评分、零调用、费用未知等。M/G 的差值只取两者均有人工评分的共同 block，逐 block 等权，显示共同数及其占已提供配对 block、全部 block 的覆盖；这不是所有运行的无条件提升。渲染成功的 review 失败回退片仍可进入观看/覆盖，必须结合 review_status 披露。planned_runs 的分母是输入记录数，工具不会自动发现未提供的丢失记录；正式汇总需传全量计划对应记录。

overall.usage 和 by_condition 只统计条件运行，失败费用也保留；未知不当零，显示已知小计与未知数。完整 block.json 提供的共享规划由 CLI 另记入 block_ledger_accounting：planning 只加一次，all_phases 合计规划与三条件；只传 run.json 无法重建规划费用，all_phases 返回 null。调用完成、渲染成功和情绪识别正确是不同字段。指标没有训练模型，也没有读取测试后自动调参。


## 审查与渲染覆盖


`summarize`、generated 私有导出摘要及评分汇总在 overall 和每个 by_condition
使用同一组计数：`review_applied_runs`、`review_unchanged_runs`、
`review_not_applicable_runs`、`review_unknown_status_runs`，与原有
`review_failed_runs`、`review_rejected_runs` 合计等于 `planned_runs`。
只按保存的精确状态统计；缺失、未知及旧 `no_changes` 不推断为 unchanged。

`rendered_review_failure_runs` 是 render_status=rendered 且 review_status 为
review_failed/rejected 的交集，用于显示可播放的审查失败/回退记录；它不认证
回退内容与原稿相同，也不把这些片段判为有效修订。
`no_rendered_video_runs = planned_runs - rendered_runs`，包括未开始、未提交、
失败、中断和未知渲染状态，不直接声称文件物理不存在。它与 missing_ratings
可能重叠，不能相加当运行总数；rendered 标签也不能代替实际媒体重检。

这些是原始记录诊断，不改变评分、M/G 配对、生成式资格门禁、费用或正式纳入
规则。没有评分时主观均值仍为 null，没有记录时所有新增计数为 0。

## Generated comparison input prerequisites


`validate_generated_comparison` checks one three-condition block against its
actual source objects. Supply `project_root` for root-relative reference assets;
omitting it preserves the original current-directory behavior.

```python
from moodcut.evaluation import validate_generated_comparison

errors = validate_generated_comparison(
    records, scene=scene, initial=initial, plans=plans,
    manifest=manifest, settings=settings, template_sha256=template_sha256,
    project_root=project_root,
)
```

`plans` maps `baseline`, `generic_review`, and `moodcut` to complete plans.
The function returns diagnostic strings, or an empty list when these input
prerequisites pass. It performs no network calls and does not mutate inputs.
It recomputes initial, final and shared generation hashes using the public
contract helpers, validates local reference assets, and checks that changes are
restricted to dialogue. Baseline must equal the complete initial plan; an
`unchanged` review must also equal it. The three records must share their block,
replicate, source kind, text model and ordered shot selection. Missing or duplicate
conditions, invalid review outcomes and explicit failed/interrupted runs fail.

This helper checks input prerequisites, not complete generated-run eligibility.
An empty error list does not certify receipts, reused jobs, media bytes, human
quality checks, costs or formal inclusion. Offline prepared fixtures may pass
these input checks. The function never sets `comparison_status=eligible` and
does not release generated exports/ratings without the independent rechecks. Final
`records` remain the accounting source; `preflight_records` must not be added as
another set of runs. Unknown costs remain unknown. Receipt and media evidence
are connected through the existing P1/P4 interfaces in CONTRACTS 6.14–6.17.


### Media and receipt helpers

| Helper | Checks | Does not establish alone |
| --- | --- | --- |
| validate_generated_media_file | Final-file path and current byte hash | Source clips, receipts, decoding or human quality |
| validate_generated_source_bindings | Ordered shot/request/clip identity and assembly sidecar | Authenticity of an arbitrarily supplied bundle or provider |
| validate_generated_receipt_binding | Saved receipt hash, request/model/task/path binding | Reuse ownership, charges or quality |
| validate_generated_media_evidence | Combined per-condition file/source/receipt diagnostics | Block eligibility or formal inclusion |

Use the complete qualification entrypoint below, which combines these checks with P1 source replay and the actual compiler. Individual helpers never promote a record or bypass export checks. Contract details remain in CONTRACTS 6.9 and 6.13–6.15.

## Offline qualification of final generated records (2026-10-23)

```bash
python -m moodcut qualify-generated-records --records runs/video-inspection/records --pricing-config configs/video.json --output runs/qualification
```

Use one final P1 `records` directory (or its `block.json`), the same local pricing
configuration and an explicit `--project-root` if invoked outside the checkout.
Source/preparation/receipt/media files must still exist at their recorded local
locations. Do not supply the earlier `preflight_records` snapshot as another run.
The output directory must be new. `qualification.json` is written on both eligible
and ineligible checks; exit status is 0 only when all three conditions pass.
Malformed/unavailable source evidence produces diagnostics, not a repaired record.

P1 `recheck_generated_records` reuses the computation behind
`assemble_generated_records` without creating intermediate directories. It rereads
source scripts and preparation snapshots, recompiles requests with the actual P4
compiler/template and original shot indices, and replays the existing P1 receipt,
same-block reuse, A/V probe and accounting logic. The saved source/request/receipt
snapshots, on-disk run files and full block ledger must agree with that replay.
Quotes stay separate from spending. Unknown costs/counters and known subtotals
must remain identical; unknown spending alone does not veto input eligibility.
An invalid reuse declaration or a changed ledger is not accepted as free usage.

P5 `qualify_generated_records(records, pricing_config=..., project_root=...)`
then combines the input and per-condition media checks from PR #37. The report
contains the original complete `record_block`, its canonical `records_sha256`,
three condition results and diagnostic strings, and a block-level result.
`accounting_verified` means the saved evidence and ledger agree with the P1
recomputation; it does not authenticate provider billing. An original failed
condition remains in the report and ledger. Its ineligible result does not delete
otherwise valid condition records. Global source/accounting failures reject the
block. Missing source data cannot establish eligibility.

The report is a separate point-in-time artifact. It never changes original
`comparison_status`, source kind, fees, raw media or blank human checklists.
`eligible` describes the selected shot scope's software evidence only; it is not
approval of speech, emotion, provider authenticity, formal inclusion or spending.
`formal_inclusion_approved` and `export_enabled` remain false, and human quality is
`not_reviewed`. Activity counters describe this offline check only (zero new HTTP,
POST, GET and provider cost), not historical generation costs.

The qualification report alone still cannot release an export. The generated
entrypoints below perform fresh source and copy-boundary checks and bind the
private mapping to exported bytes. Generation status summaries are available
below; formal protocol choices and independent human evaluation remain separate decisions. No new sample, experiment condition, model call,
model download, GPU evaluation or subjective score is introduced here.


## Generated blind export and rating import (2026-10-23)

```bash
python -m moodcut evaluate --records runs/video-inspection/records --pricing-config configs/video.json --blind-output runs/generated-blind --seed 17
python -m moodcut evaluate --records runs/video-inspection/records --pricing-config configs/video.json --output runs/generated-coverage.json
python -m moodcut evaluate --records runs/video-inspection/records --pricing-config configs/video.json --ratings runs/completed-ratings.csv --private-key runs/generated-blind/PRIVATE/private_key.csv --output runs/generated-scores.json
```

Supply each complete final block once, not individual run files, preflight
snapshots, or an old qualification report. Multiple final blocks can follow
`--records`; do not mix source kinds. The same local pricing config and saved
source locations are required. Outside the checkout, give `--project-root`.
All output paths must be new. These commands perform only local checks/copies;
they do not submit, resume, download, or score anything using a model.

The export reuses the anonymous copier and seeded shuffle. Only whole blocks
whose three conditions pass current offline qualification are copied. Failed or
inconsistent blocks retain all original records in `PRIVATE/summary.json`, with
per-condition errors, coverage, missing scores and original ledgers. This
conservative software gate does not settle formal failure/unchanged inclusion.
A successful command with zero exported clips creates an empty diagnostic
package; it does not establish a distributable comparison.

Only `public/` is for viewers: anonymous MP4s, `blind_items.csv` and an empty
`ratings.csv`. Do not distribute `PRIVATE/`, CLI metadata or inspection pages.
`PRIVATE/generated_export.json` binds complete block identities (including
selected-shot scope), item/run mapping, actual copied video hashes, private key
and public index. Hashes establish local consistency, not signed authenticity.
The copier checks source and destination bytes before/after copying, requalifies
sources afterwards and publishes only the finished package. Keep the original
sources and entire package for rating import. Moving/editing them requires a new
export; a matching old qualification report alone is insufficient.

Before joining supplied scores, the importer requalifies sources and checks all
exported files and mappings, including unrated items. Source-only video checks
are insufficient. Missing/duplicate/subset keys, swapped files or arbitrary
run-ID ratings fail. Blank template rows are invalid scores; the export never
fills them. The no-ratings command above reports coverage directly. Test CSVs
use explicitly synthetic arithmetic fixtures, not human observations.

The original score formulas remain: average votes within each clip, give clips
equal weight, count uncertain as a miss, compare M/G only on jointly rated blocks
and report coverage separately. All original rows stay in denominators and
condition usage. `block_ledger_accounting.blocks` preserves each original final
ledger once, including shared planning, request reuse, null totals and known
subtotals; do not add preflight or condition usage to those ledgers again.
Current accounting verification flags are reported separately. The exporter and
importer set `formal_inclusion_approved=false`; human quality remains
`not_reviewed`. Existing software media cannot establish speech, emotion, acting
or model effectiveness. Coordinators must inspect clips for content/metadata
that reveals conditions before distribution; the tool does not infer semantic
anonymity. Generation status reporting is described below. Formal protocol approval and independent viewer assignment remain separate decisions.

## Generation status summaries (2026-10-23)

Generated evaluation reports now add `overall.generation` and
`by_condition.<condition>.generation`. The same fields are returned by raw
`evaluate --records ...`, source-qualified summaries and rating imports, and
the private blind-export summary. No new command/parameter is needed. This
counts saved states without changing P1 receipt mapping, costs, eligibility or
human scores. Pure legacy/empty reports keep their original shape.

`generation.by_status` has seven mutually exclusive run counts:
`not_started`, `prepared_offline` (offline requests not submitted), `in_progress`,
`assembled_requires_manual_inspection`, `failed`, `interrupted`, `unknown`.
Missing/null/unrecognized states remain unknown. The counts sum to
`generated_runs`; adding `not_applicable_runs` gives the original
`coverage.planned_runs`. Each condition uses its own supplied-record denominator.
Input records omitted by a caller cannot be discovered automatically.

Use the other fields as overlapping diagnostic axes, not extra runs:

- `failed_run_causes`: original `failure_kind` among failed runs; includes
  generation, local media and pre-generation review/validation failures.
  Missing causes are `unspecified`; do not call every failed run a provider failure.
- `pre_generation_failed_runs`: failed runs still at `not_started`.
- `awaiting_assembly_runs`: in progress, not rendered, with a nonempty list of
  downloaded clips; provider `completed` alone does not qualify.
- `runs_with_unsubmitted_jobs`: at least one prepared-offline job, including
  mixed runs that already have failed/interrupted/other clips.
- `jobs.by_status`: saved clip entries, including separate failed/interrupted
  counts even when P1's run state gives failure precedence. Counts sum to
  `jobs.recorded_jobs`. `declared_reused_jobs` is an observation, not a new
  provider task or certified reuse; never add these counts to POSTs or costs.
- `jobs.remote_status_counts` preserves recorded remote strings such as
  `polling_timeout`, `download_interrupted`, `expired`. Missing remote status
  (`jobs_without_remote_status`) does not establish no submission; reused clips
  can also lack this field.
- Empty job lists and invalid/missing job records have separate run counters.
  Non-object entries count as unknown jobs; an unreadable whole job field does
  not invent a clip or establish zero attempts.

The existing render counters retain their meanings for compatibility. A failed
generation can still be in `render_pending_or_skipped_runs`; the new generation
axis exposes its actual saved failure/interruption instead of changing rendering
history. Neither axis establishes speech, emotion or final human acceptance.
The legacy `timeout_runs` counts only `failure_kind=timeout`; video polling
timeouts saved as generation failures appear in `interrupted` and the raw
`remote_status_counts.polling_timeout`, without rewriting the old counter.
All records remain in costs, missing-rating counts and common-pair denominators;
unknown expenses and original once-per-block ledgers are retained. Clip weighting,
uncertain misses and M/G score formulas are unchanged. See CONTRACTS 6.16 for the
complete field meanings. Tests reuse synthetic software fixtures, never provider
histories, formal experiments or independent subjective judgments.


## 正式评价前待冻结

| 项目 | 需要明确的内容 |
| --- | --- |
| 输入与版本 | 开发/正式来源、故事与 tone、方法/提示/Schema 版本、选中镜头及共同身份 |
| 规模与复用 | 故事数、重复数、同视频复用是否作为独立样本、失败和 unchanged 的纳入规则 |
| 模型与预算 | 模型、共同生成设置、文本/视频费用、历史未知账目、停止与 GET 恢复范围 |
| 人工评价 | 技术检查人、评分人数、每 clip 评分数、同故事版本分配、随机化及暴露风险 |
| 分析 | 评分指标、缺失/排除规则、配对分母、覆盖与费用报告，不在看结果后选择口径 |

[六故事 v2](studies/six-story-clear-emotions-20261024/README.md)已有输入范围，执行和正式纳入仍需确认。2026-10-23 的最初单镜头提议及后续批准/失败保留在[还伞记录](pilots/umbrella-single-shot.md)，不再把其中旧占位图、旧报价或“从未试跑”当作当前状态。

## VBench 辅助评价

安装、固定权重、归一化、失败计数、批量和 resume 见[VBench 工具](vbench.md)。imaging_quality 不评价对白、情绪、音频或全部视频质量维度。独立人工评价仍是检验研究问题的必要证据。

## 历史贡献与交接快照

以下保留原 2026-10-24 贡献表和交接原文，其“open / outstanding / this checkout”均指该快照。软件验证由原 P5 作者 chessloverr 和后续团队集成共同完成；FAN XUYANG 的覆盖计数与工作流验收见[原记录](history/evaluation-acceptance.md)。当前状态以[文档入口](README.md)和各 PR 为准。

## P5 contribution and evidence record (2026-10-24)

The table attributes deliveries to their public PR authors. It distinguishes the
P5 work submitted by `chessloverr` from subsequent team integration; it is not a
claim of sole authorship of the complete evaluation pipeline.

| Delivery | Authored contribution | Evidence and status |
| --- | --- | --- |
| [PR #14](https://github.com/zhengads/MoodCut-dsa4213/pull/14) | `chessloverr`: original VBench imaging_quality adapter, normalization, batch reporting, failure accounting and resumable execution | Merged; CPU synthetic-media smoke/batch evidence is recorded above. Other VBench dimensions and formal model performance are not established. |
| [PR #37](https://github.com/zhengads/MoodCut-dsa4213/pull/37) | `chessloverr`: generated input, file, source/request and receipt identity checks; combined media diagnostics; integration coverage for valid, unknown-cost and failed records | Merged; final scoped local regression reported 51 tests and 88 subtests passed. FakeClient and synthetic media verify software behavior only. |
| [PR #46](https://github.com/zhengads/MoodCut-dsa4213/pull/46) | `chessloverr`: regression tests rejecting wrong private condition/tone labels even after recalculating the CSV checksum | Open at this snapshot; 3 targeted cases passed locally, including the normal export/rating path. Use the PR Checks tab for current CI, not this dated record. |
| [PR #38](https://github.com/zhengads/MoodCut-dsa4213/pull/38), [#39](https://github.com/zhengads/MoodCut-dsa4213/pull/39), [#40](https://github.com/zhengads/MoodCut-dsa4213/pull/40) | `zhengads`: offline qualification integration, generated blind export/rating integration and generation-status reporting | Merged team integration building on existing modules. Do not attribute these complete deliveries solely to the P5 prerequisite work. |

### Report-ready contribution statement

I implemented the VBench imaging_quality evaluation adapter and resumable batch
reporting, then added checks tying generated comparison inputs, media and saved
receipts to their recorded identities. I tested these checks against actual team
interfaces using synthetic media, including failed runs and unknown costs. I
also added regressions protecting blind-evaluation condition and target-tone
labels. Teammates subsequently integrated qualification, export, scoring and
status reporting. These contributions establish evaluation tooling and evidence
integrity; they do not demonstrate an improvement in generated-video quality.

### Remaining evidence handoff

For real-run verification, provide a sanitized copy of the final records together
with the referenced preparation/source inputs, configuration and receipts,
preserving relative directory relationships and checksums. Include media and
inspection artifacts when they exist; a failed run without media remains a
failure record. Exclude credentials and personal rater identities. Original
snapshots must remain intact, and missing costs must remain unknown.

Actual receipt/media rechecks, VBench runs on accepted real clips and independent
human ratings remain outstanding in this checkout. No formal sample size,
participant assignment or new paid execution is approved by this document.
