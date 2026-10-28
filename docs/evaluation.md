# MoodCut 资格、盲评与评价

[文档状态](README.md) · [使用命令](usage.md#检查与评价生成视频) · [VBench 工具](vbench.md) · [历史验收](history/evaluation-acceptance.md)

本页维护输入要求、评分口径和证据边界。真实试跑记录在 pilots/；人工评分、模型自评、媒体完整性和 VBench 分数分开解释。PR #58 的历史视频审计与图像质量结果已合入，保留下方带日期的证据；不据此宣称当前 12 个剧本的正式评价完成。

## 软件流程验证

从仓库根目录运行，先配置 FFmpeg/ffprobe 与字体，使用新输出目录：

```powershell
.venv/Scripts/python scripts/verify_workflow.py --output runs/workflow-check-01
```

该入口检查三条件 mock 视频、匿名导出、无评分覆盖、任务 dry-run 和 generated 集成。查看 verification.json、阶段日志及 generated-tests.xml。软件视频、回执和评分夹具不作为独立效果证据；历史实测和贡献署名见[验收记录](history/evaluation-acceptance.md)。

## 方法身份

同一比较使用一致的协议和 writer contract。v3 的有效最终分歧可保留 disputed 状态进入准备，不自动计为成功、失败或人工认可；详见[演员方法](ACTOR_REVIEW_METHOD.md)。公开对比页暴露条件、目标和台词，不用于盲评分发。

## 配对人工评价

主 CLI 的 evaluate 完全离线，不启动模型。configs/experiment.json 是开发分配示例，包含已有软件夹具；--dry-run 仅列出任务，不改变原 SceneInput，也不自动批量生成。配置显式提供 `tones` 时保留 scene×tone×replicate×condition；省略 `tones` 时使用每个 scene 自己的受支持 `tone`，用于 S07–S12 和 S13–S18 这类固定故事–情绪配对，避免错误笛卡尔积。S13–S18 的独立 `draft-dialogue.json` 是人工编写的审查压力测试材料，evaluate 不会自动读取它；生成脚本调用方须把它显式传给 `pipeline.run_experiment` 的 `authored_dialogue_draft` 参数。适配器在共同规划后、条件拆分前只替换单镜头对白，并保存与重检初稿哈希；dry-run 本身仍不能当成共享初稿执行。实际请求准备使用 run 命令，一次一个明确输入的 block。configs/pilot.json 保留原 VBench 提议配置，不能作为人工评价的 scene 路径配置。

```bash
python -m moodcut evaluate --config configs/experiment.json --dry-run
python -m moodcut evaluate --config configs/basic-emotions-experiment.json --dry-run
python -m moodcut evaluate --config configs/basic-emotions-challenge-experiment.json --dry-run
python -m moodcut evaluate --records runs/demo/block.json --blind-output runs/blind-demo
python -m moodcut evaluate --records runs/demo/block.json --output runs/demo/coverage.json
python -m moodcut evaluate --records runs/demo/block.json --ratings runs/blind-demo/public/ratings.csv --private-key runs/blind-demo/PRIVATE/private_key.csv --output runs/demo/human-summary.json
```

输出目录/文件必须新建。只分发 public/，包含匿名 MP4、blind_items.csv 和空 ratings.csv；PRIVATE/private_key.csv 含条件、目标 tone、初稿与视频 SHA-256，单独保管。匿名导出只核查已有非空 MP4，不能代替实际播放检查。填写评分前，团队明确评价者分配，避免同一人连续看同一故事的不同版本；导出本身不自动保证实验盲法。默认 mock 材料只用于操作检查。

每个已完成的评分行需 rater_id（匿名）、item_id、perceived_tone、confidence、naturalness、story_clarity、overstatement；后四项必须为 1–5 整数。S01–S06 使用 affectionate／hostile／tense／uncertain；解析器额外保留 suspicious 以读取旧协议。S07–S12 使用 VEMOCLAP 原生 anger／disgust／fear／joy／sadness／surprise／uncertain。两套标签保持独立，不互相映射。混淆矩阵、命中率、uncertain 未命中、clip 等权、共同 block 差值和失败覆盖的公式不变。不能把空模板交给汇总；只汇总已完成行，未评分 clip 仍由原始记录留在覆盖分母。重复 rater/item、未知 item、旧映射或视频哈希不符均报错。实际评分解释和正式样本由团队确认，程序不代填答案。

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

## Public pilot media audit and evaluation readiness (2026-10-25)

P5 audited the actual downloadable Anna/Elsa pilot videos against their release
manifests and published result records. All **8 distinct videos** passed byte,
metadata and full audio/video decode checks. They represent **9 condition
entries**, because actor-v1 baseline and generic_review share one video. This is
media integrity evidence, not a VBench result, independent rating, full source
qualification or approval for formal inclusion.

### Versioned evidence inventory

Repository snapshot: `f45590de4a89d9c5d787771dcc59308e41f274d3` (main).
The v3 public result record was read separately at
`c7e6bd87437bef05dad45805f55c184ad4e1b041` (Draft PR #52).

| Pilot protocol | Condition entries | Distinct videos | Interpretation |
| --- | ---: | ---: | --- |
| global-v1 | 3 | 3 | Historical global review; keep separate from actor self-review. |
| actor-v1 | 3 | 2 | baseline and unchanged generic_review reuse identical bytes; retain both condition entries without inventing an independent generation. |
| actor-v3 | 3 | 3 | Historical bounded actor negotiation; public record says completed_requires_manual_inspection. |
| Total inventory | 9 | 8 | An inventory count across protocols, not nine independent experimental samples. |

Public releases and pinned records:

- [Historical global-v1 / actor-v1 release](https://github.com/zhengads/MoodCut-dsa4213/releases/tag/pilot-anna-elsa-20261024):
  [manifest](https://github.com/zhengads/MoodCut-dsa4213/releases/download/pilot-anna-elsa-20261024/manifest.json),
  [global result](https://github.com/zhengads/MoodCut-dsa4213/blob/f45590de4a89d9c5d787771dcc59308e41f274d3/docs/pilots/anna-elsa-agent.results.json),
  [actor-v1 result](https://github.com/zhengads/MoodCut-dsa4213/blob/f45590de4a89d9c5d787771dcc59308e41f274d3/docs/pilots/anna-elsa-actor.results.json).
- [Historical actor-v3 release](https://github.com/zhengads/MoodCut-dsa4213/releases/tag/pilot-anna-elsa-v3-20261024):
  [manifest](https://github.com/zhengads/MoodCut-dsa4213/releases/download/pilot-anna-elsa-v3-20261024/manifest.json),
  [pinned result](https://github.com/zhengads/MoodCut-dsa4213/blob/c7e6bd87437bef05dad45805f55c184ad4e1b041/docs/pilots/anna-elsa-actor-v3-captured.results.json).
  Its executed code is `7817623a76de5d5ff68b7da5c12aa943e28798c4`, with
  `dialogue_by_shot_v1`. The commit hosting the published record is not the
  executed commit. Do not relabel these clips as outputs of the newer
  `dialogue_by_shot_json_schema_v2` contract in PR #52.

Release manifest SHA-256 values, in the release order above:

```text
b89b95de4577cbe8d2611df4e210dc49e91400170aaf1359fed26e4875b0472b
b3d479ef1b6141165ecee8bed374318a575fa9e02c4fa1bb41aaa14bbe06abd3
```

### Observed file checks

Every listed MP4 matched its manifest size/hash and GitHub asset size/digest
(where the API supplied a digest). Each mapped condition's published video hash,
width, height and encoded duration matched the downloaded file. All videos have
1344 x 768 video, reported frame rate 24/1, an audio stream and encoded duration
5.258344 seconds. Total downloaded MP4 size: **8,662,796 bytes**. Full decoding
reported no errors for all eight files with FFmpeg 9.0.1 Essentials.

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `global-v1-baseline.mp4` | 923,816 | `4cdadb0ab1d66868caad62bb7c11e8c8b9c24e43a89f73f5f88767539f1c85e1` |
| `global-v1-generic_review.mp4` | 1,090,596 | `8badfe78d6a9253cdf7f081112d64d5af933704015db235e51fcc7fb6e11c2a4` |
| `global-v1-moodcut.mp4` | 1,023,858 | `bab555e2b4dfeef1d4183baaee857ded13540502cc14284d01d7baa1f61bee4b` |
| `actor-v1-baseline-and-generic.mp4` | 1,261,699 | `bdda0b1bbb79ce0942b6cd867d77e8e804839a575b1597f8ee4fc29bb55668a7` |
| `actor-v1-moodcut.mp4` | 1,036,129 | `cf0aaaf662f76df3ca2166ce33f2690663451783fba068b5346b5efc5dc771c8` |
| `actor-v3-baseline.mp4` | 1,070,733 | `c4c527b7a9f8bfd3ab7e0cec41bf077d980226d4e147a55d65979a6ed734050c` |
| `actor-v3-generic_review.mp4` | 1,156,634 | `dba7f08313592ba258f820eb78c6f01d2dd16620e8c05c5c2cedcaba545fcff8` |
| `actor-v3-moodcut.mp4` | 1,099,331 | `0948eb88ae5b82a283b38c07d4225db3ec5aaa438ecbc3b0b4c11ecb60c74ca7` |

To reproduce, download the MP4 assets and manifests from the two releases into
separate ignored run directories, retain their SOURCE.md attribution, and first
verify the manifest hashes above. Compare each file's byte count and SHA-256
with the manifest and pinned per-condition result. Probe both streams using
P4's existing media probe (or `ffprobe -v error -show_format -show_streams
-of json <clip.mp4>`), then decode each file with:

```text
ffmpeg -v error -xerror -i <clip.mp4> -map 0:v:0 -map 0:a:0 -f null -
```

The audit's local evidence is under `runs/release-audit-20261025/`: `audit.json`,
`videos.csv`, downloaded manifests/source records, per-file ffprobe JSON and
decode logs. These artifacts and videos remain ignored. The pinned links,
checksums, observations and reproduction procedure above are the public record.

Audio presence and successful decoding do not establish intelligible speech,
correct speaker attribution, emotional delivery or visual quality. This audit
made zero provider calls, ran no benchmark inference and collected no ratings.
It did not independently reconcile the published spending with original receipts.

### Project status and next evidence handoff

At this snapshot, PR #46 (P5 anonymous-label regressions) and PR #57 (review
coverage and repeatable offline verification, authored by `fanx9905-blip`) are
merged. The PR #46 status in the dated contribution table above is historical.
PR #52 remains Draft: the later S06 attempts stopped before video generation;
the latest recorded stop was invalid actor dialogue ownership. The subsequent
schema/ownership fixes have offline evidence, but no new successful S06 video
is established by the eight historical Anna/Elsa files.

The [six-story clear-emotion inputs](studies/six-story-clear-emotions-20261024/README.md)
define affectionate/hostile/tense scenes and 18 planned condition entries. They
are an input design, not 18 completed results. Do not merge the older Anna/Elsa
pilot into that dataset or combine global-v1, actor-v1 and actor-v3 into a paired
method-effect estimate.

| Next activity | Available evidence / dependency | Required interpretation |
| --- | --- | --- |
| Inspect historical pilot media | The eight files are now locally available and byte-checked. | A human can inspect speech, speakers and emotion; no answers have been filled automatically. |
| Requalify actual source records | Still needs final block records, frozen inputs, preparation artifacts, configuration and original receipts with relative relationships intact. Published summary JSON and MP4 files alone are insufficient. | Reuse P1 source rechecks and P5 qualification; retain failures, unknown costs and each final ledger once. |
| Run real-clip VBench | Freeze the accepted clip inventory and obtain the required model, scale and compute/budget approval. | Existing adapter covers imaging_quality; it does not measure dialogue emotion or constitute full VBench. Report protocol and reused-file mappings alongside scores. |
| Collect independent ratings | Needs source-qualified export, agreed protocol/rater assignment and blank templates. | Reuse existing export/import rechecks; keep private mappings private and human answers independent. |
| Compare the current method | Needs a frozen common protocol, completed approved runs and independent evidence for the intended study. | Preserve failed/unchanged/reused entries and coverage; do not infer effectiveness from these integrity checks. |

The [public viewing page](https://zhengads.github.io/MoodCut-dsa4213/) reveals
conditions and target tones. It is suitable for team inspection, not blind
rating distribution. Use the existing anonymous export route after complete
source handoff; account for prior exposure when assigning independent raters.

P5 contribution in this increment: independently retrieved and audited the
published media, reconciled condition-to-file reuse and protocol versions, and
recorded the remaining evaluation dependencies. Generation, protocol changes
and the shared verification workflow remain attributed to their original authors.

### Current offline integration verification

Reused the team's existing workflow on the same main snapshot:

```text
python scripts/verify_workflow.py --output runs/workflow-verification-20261025
```

All five stages passed: three-condition mock run, anonymous export, coverage
without ratings, assignment dry-run and generated integration. The final stage
passed **12 tests**, with zero failures/errors/skips. The mock run produced three
clips; all three remained unrated and score means remained null. Local evidence
is `runs/workflow-verification-20261025/verification.json`, stage logs and
`generated-tests.xml`. These synthetic fixtures verify software integration;
they do not requalify the real pilot media audited above. No full-suite rerun
is claimed for this documentation-only increment.

## Real pilot imaging_quality results (2026-10-25)

Following explicit approval of the eight-video CPU scope, the existing pinned
VBench adapter evaluated all eight audited files with cached MUSIQ-SPAQ weights.
**8 succeeded, 0 failed, 0 missing, 0 timed out.** Total worker elapsed time was
393.202 seconds (including per-worker setup); each file took 47.795-55.513 seconds,
within its 300-second timeout. There were no retries, GPU runs, model downloads
or paid API calls. External API spending was $0. This supersedes the pending
benchmark status in the earlier audit snapshot; full source qualification and
independent human ratings remain outstanding.

### Measured scores

Each row is one distinct downloaded file, linked by the exact filename and
SHA-256 in the audit table above. Actor-v3 denotes the historical
`actor_self_review_v3` / `dialogue_by_shot_v1` outputs, not the later schema fixes.
Scores are descriptive development-media measurements; formal inclusion remains
false. The adapter's method label is a unique protocol/file identifier so its
summary cannot silently pool different protocols.

| Video ID (MP4 basename) | Mapped condition(s) | Raw mean MUSIQ | imaging_quality (0-1) | Worker seconds |
| --- | --- | ---: | ---: | ---: |
| `global-v1-baseline` | baseline | 76.547845840 | 0.765478458405 | 55.513 |
| `global-v1-generic_review` | generic_review | 76.734780896 | 0.767347808961 | 47.850 |
| `global-v1-moodcut` | moodcut | 75.797529713 | 0.757975297128 | 47.875 |
| `actor-v1-baseline-and-generic` | baseline + generic_review | 76.851614368 | 0.768516143676 | 47.821 |
| `actor-v1-moodcut` | moodcut | 75.617978004 | 0.756179780037 | 47.902 |
| `actor-v3-baseline` | baseline | 75.800705756 | 0.758007057559 | 49.606 |
| `actor-v3-generic_review` | generic_review | 76.946241994 | 0.769462419941 | 48.840 |
| `actor-v3-moodcut` | moodcut | 74.978804250 | 0.749788042499 | 47.795 |

The shared actor-v1 file was scored once. Its baseline and generic_review entries
refer to that same score, not two independent samples. No pooled cross-protocol
mean, overall VBench score, significance test or method-effect estimate is
reported. In each of these three historical protocol groups, the moodcut file
has a lower imaging_quality value than its baseline file. Preserve that
observation; it does not establish worse emotional delivery or general method
performance from one story and one clip per condition.

### Score derivation and reproducibility

- VBench source: `fd18b3d055cb0fc6f066ca90fe2c3c8cbb698490`, clean pinned checkout.
- Model: cached MUSIQ-SPAQ, SHA-256
  `358bb6af275e28ea56821d44fb55c6cb83645db11f394d3ad65b2d149965ab50`.
- CPU, two PyTorch threads, seed 0, `longer` preprocessing, `custom_input` mode.
  Generation seed 4213 in the metadata is distinct from the evaluator seed.
- The pinned implementation loads all decoded video frames, resizes inputs whose
  longer edge exceeds 512 pixels, computes MUSIQ per frame, averages within the
  video, then divides the raw mean by 100. Audio and prompt text are not scored.
  The manifest retains the published scene story and explicitly identifies it as
  different from the unavailable original compiled provider prompt.
- Environment recorded in the batch checkpoint includes torch 2.5.1+cpu,
  torchvision 0.20.1+cpu, pyiqa 0.1.13, timm 1.0.12, decord 0.6.0 and
  transformers 4.37.2. See the earlier setup section for the pinned environment.

Formula: `imaging_quality = mean(frame MUSIQ scores) / 100`. For example,
`76.5478458404541 / 100 = 0.765478458404541` for global-v1 baseline. This is a
normalized perceptual-quality score, not a 76.55% accuracy or probability.

The actual invocation used the existing adapter without production-code changes:

```powershell
$env:PYTHONPATH = 'src'
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
.venv/Scripts/python -B -m moodcut.evaluation batch --manifest runs/pilot-vbench-plan-20261025/manifest.json --video-root runs/release-audit-20261025 --upstream references/upstream/vbench --cache runs/vbench-cache --output runs/pilot-vbench-results-20261025 --timeout 300
```

A new invocation must use a fresh output directory. This command records the
completed execution; it does not approve further or broader compute runs.

### Evidence and verification

Local artifacts remain under ignored `runs/` directories:

- `pilot-vbench-plan-20261025/manifest.json`: eight unique inputs;
  `condition-map.json`: nine condition entries mapped to the eight video IDs;
  `plan.json`: original pre-approval plan, with subsequent scope approval recorded
  separately in `approval.json`. The original plan snapshot is preserved.
- `pilot-vbench-results-20261025/checkpoint.json`: original input/configuration
  identity and results; `normalized_results.json` and `summary.csv`: existing
  adapter outputs. Each summary group contains one unique file.
- `pilot-vbench-results-20261025/item-*/`: native VBench results and worker logs.
- `pilot-vbench-results-20261025/public_results.json` and `public_results.csv`:
  sanitized per-file results with hashes, protocol, condition mapping and timing.
  Raw local checkpoints/logs can contain machine paths and should not be copied
  into public PR text.

Post-run checks matched every successful normalized score to its native raw
score divided by 100 and to the native aggregate. All eight original media hashes
still match the input manifest and audit. Checkpoint/normalized rows agree;
summary totals retain all eight files with zero missing/failed entries; all nine
condition mappings remain present. The exact CPU/thread/timeout configuration
was checked. No human judgments were generated and no receipt or media was
rewritten. This documentation-only increment does not claim a new full-suite
local test run; the earlier offline workflow result remains separate evidence.

The next evaluation dependencies are unchanged: complete original source records
and receipts for qualification, independent human inspection/ratings, and an
agreed formal study protocol. These historical image-quality measurements alone
do not satisfy those dependencies or evaluate speech, emotion, audio quality,
temporal consistency or the other VBench dimensions.

## Qualitative case: explicit affection versus contextual naturalness (2026-10-25)

A non-blind team discussion raised a contextual concern about Elsa's moodcut line,
"谢谢你，安娜。你真好。" ("Thank you, Anna. You are so kind."). Praising Anna's kindness
may be excessive for the routine return of a borrowed umbrella unless additional
context motivates it. This is an open naturalness/overstatement concern, not a
confirmed error: affectionate relationships and delivery could make the line
plausible. The English account below is an edited paraphrase of feedback, not a
verbatim independent-rater response.

### Trace to the saved review

The [pinned actor-v3 public record](https://github.com/zhengads/MoodCut-dsa4213/blob/c7e6bd87437bef05dad45805f55c184ad4e1b041/docs/pilots/anna-elsa-actor-v3-captured.results.json)
contains the following trace for `return-umbrella-shot`, character `b` (Elsa):

1. The baseline line is "谢谢你，安娜。". Elsa's moodcut actor report
   `actor-2:tone_underwhelming` describes it as insufficiently warm and explicitly
   proposes adding "你真好" as one possible revision.
2. `writer_response.dialogue_by_shot` adopts the added phrase, and the writer's
   `addressed_issue_ids` includes that actor issue. The saved final plan contains
   the same line. This establishes the phrase's presence in the script before
   video generation; it does not verify exactly what is audible in the clip.
3. The saved result is `applied` with `verification_kind=programmatic_only`,
   `actor_endorsement=not_requested`, `actor_confirmation_status=not_needed` and
   an empty `actor_confirmations` list. Writer-declared feedback resolution is not
   an independent judgment that the resulting dialogue is natural.

The corresponding video is `actor-v3-moodcut.mp4`, SHA-256
`0948eb88ae5b82a283b38c07d4225db3ec5aaa438ecbc3b0b4c11ecb60c74ca7`.
This trace concerns the historical `actor_self_review_v3` /
`dialogue_by_shot_v1` run, not the later S06/schema fixes.

### Evaluation interpretation and follow-up

The case suggests a possible trade-off: making the target affection explicit may
weaken conversational motivation. Treat this as a qualitative hypothesis for
future independent assessment, not a numeric score, causal finding, universal
rule against gratitude or evidence that the method generally fails. It is also
not an explanation for this clip's lower imaging_quality value; that metric does
not score dialogue meaning.

The discussion had access to conditions, target tone, expected lines and prior
image-quality scores, with assistant discussion before the feedback was recorded.
It is not blind or independent. No timestamped transcript, complete technical
checklist, numeric naturalness/overstatement rating or other-condition judgment
was supplied. Those fields remain unfilled. The existing independent-rating
counts and all benchmark scores are unchanged.

Local evidence is `runs/actor-v3-technical-review-20261025/qualitative_concern_001.json`;
the original blank technical template, public source record, videos and benchmark
results remain intact. Preserve the case for discussion with the review-module
owner. Any future prompt revision should be a separately versioned prospective
change; do not rewrite these historical scripts or replace their evaluation
results. Independent ratings must still follow the agreed source-qualified
export and assignment workflow.

### 简短中文总结

8 段真实视频的 VBench imaging_quality 已全部算完，零失败/超时，耗时约 6 分 33 秒，外部 API 费用 $0。三个协议下 moodcut 的该项分数均低于对应 baseline，已如实保留；这只是画面质量，不能代表情绪效果或整体方法优劣。9 条条件记录中有一段视频复用，完整来源核验和独立人工评分仍待完成。

补充发现：情绪角色建议、编剧采纳了“你真好”，但其场景自然度受到非盲讨论质疑。已保留为待进一步核实的定性案例，不计作独立评分，也未修改原台词或视频。
