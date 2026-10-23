# MoodCut 配对人工评价与 VBench 工具

Issue: https://github.com/zhengads/MoodCut-dsa4213/issues/9

## 配对人工评价

主 CLI 的 evaluate 完全离线，不启动模型。configs/experiment.json 是开发分配示例，包含已有软件夹具；--dry-run 仅列出 scene×tone×replicate×condition，不改变原 SceneInput，也不自动批量生成。实际生成使用 run 命令，一次一个明确输入的 block。configs/pilot.json 保留原 VBench 提议配置，不能作为人工评价的 scene 路径配置。

```bash
python -m moodcut evaluate --config configs/experiment.json --dry-run
python -m moodcut evaluate --records runs/demo/block.json --blind-output runs/blind-demo
python -m moodcut evaluate --records runs/demo/block.json --output runs/demo/coverage.json
python -m moodcut evaluate --records runs/demo/block.json --ratings runs/blind-demo/public/ratings.csv --private-key runs/blind-demo/PRIVATE/private_key.csv --output runs/demo/human-summary.json
```

输出目录/文件必须新建。只分发 public/，包含匿名 MP4、blind_items.csv 和空 ratings.csv；PRIVATE/private_key.csv 含条件、目标 tone、初稿与视频 SHA-256，单独保管。匿名导出只核查已有非空 MP4，不能代替实际播放检查。填写评分前，团队明确评价者分配，避免同一人连续看同一故事的不同版本；导出本身不自动保证实验盲法。默认 mock 材料只用于操作检查。

每个已完成的评分行需 rater_id（匿名）、item_id、perceived_tone（affectionate/suspicious/hostile/uncertain）、confidence、naturalness、story_clarity、overstatement；后四项必须为 1–5 整数。不能把空模板交给汇总；只汇总已完成行，未评分 clip 仍由原始记录留在覆盖分母。重复 rater/item、未知 item、旧映射或视频哈希不符均报错。实际评分解释和正式样本由团队确认，程序不代填答案。

统计实现 summarize：每个有评分 clip 先算其 tone 命中比例和各 1–5 项均值，再按 clip 等权汇总；多评分 clip 不获得更大权重。uncertain 计作 tone 未命中并单列。混淆矩阵是 rating 次数，与 clip 等权均值的分母不同。自然度、剧情清楚度、过度表达和 confidence 分列，零评分分母返回 null。它们衡量被观看并评分的成片，不证明所有生成尝试有效，也不把 Agent verification 当人工结果。

coverage 保留所有提供的运行：planned_runs、rendered_runs、review_failed/rejected、缺失评分、零调用、费用未知等。M/G 的差值只取两者均有人工评分的共同 block，逐 block 等权，显示共同数及其占已提供配对 block、全部 block 的覆盖；这不是所有运行的无条件提升。渲染成功的 review 失败回退片仍可进入观看/覆盖，必须结合 review_status 披露。planned_runs 的分母是输入记录数，工具不会自动发现未提供的丢失记录；正式汇总需传全量计划对应记录。

overall.usage 和 by_condition 只统计条件运行，失败费用也保留；未知不当零，显示已知小计与未知数。完整 block.json 提供的共享规划由 CLI 另记入 block_ledger_accounting：planning 只加一次，all_phases 合计规划与三条件；只传 run.json 无法重建规划费用，all_phases 返回 null。调用完成、渲染成功和情绪识别正确是不同字段。指标没有训练模型，也没有读取测试后自动调参。

## VBench 辅助工具

以下保留单独 VBench 入口与已有协议说明。它衡量图像/视频质量，不能替代上面的情绪与叙事人工评价。

## Current delivery

Offline helpers validate video metadata and summarize per-video scores. The second
increment adds a pinned native imaging_quality adapter and an explicitly invoked
CPU smoke runner. Neither synthetic-video scores nor tool success establish that
the project generates high-quality videos. The paired human-rating interfaces described below are implemented independently of these VBench helpers; neither replaces the other.

## Proposed evaluation protocol

Use original VBench custom-input evaluation as the initial integration target,
subject to team confirmation for formal runs. The smoke test and native-output
adapter use the immutable upstream revision recorded below. Start with imaging_quality
for an environment smoke check; this is not a claim that it is the cheapest metric.
The official README lists six custom-input dimensions: subject_consistency,
background_consistency, motion_smoothness, dynamic_degree, aesthetic_quality,
and imaging_quality. Do not label this subset a complete VBench benchmark.

Source checked 2026-10-14: https://github.com/Vchitect/VBench#usage

Propose individual generated shots as the initial evaluation unit. Keep full-film
analysis separate: intended scene cuts can change subjects/backgrounds. Do not
pool shot and film scores or synthetic, development, and formal data. Preserve
prompts, generation settings, seeds, video hashes, benchmark revision, weight
versions, runtime environment and raw results for formal runs. Match generation
inputs and evaluation settings across methods. Agree on sample size and dimensions
before inspecting formal outcomes.

VBench video-quality dimensions alone do not establish emotion recognition,
narrative quality, or audio quality. The paired human emotion evaluation below remains the primary assessment of the project hypothesis. Report dimensions separately, without inventing a total score.

## Proposed video metadata

A manifest is a nonempty JSON list. Paths are relative POSIX-style MP4 paths.
Unknown generation seeds are null, not zero. This validator checks metadata only;
the batch runner resolves paths within an explicit video root, rejects path
escapes and duplicate resolved paths, checks existence, hashes input bytes, and
records decoder failures returned by the isolated VBench worker.

```json
[
  {
    "video_id": "dev_001",
    "story_id": "story_001",
    "method": "baseline",
    "prompt": "A character walks through a garden.",
    "video_path": "videos/dev_001.mp4",
    "seed": null,
    "evaluation_unit": "shot",
    "source_kind": "development"
  }
]
```

IDs must be unique. Method labels are not hardcoded to the previous three-condition
experiment. An empty manifest is an input error; a planned video with no result is
counted as missing.

## Normalized result schema

This is a proposed internal format, NOT VBench's native JSON format. The imaging_quality adapter supports the pinned original VBench revision below.
Other native dimensions are not yet supported.
Each video/dimension has at most one result. Scores use the dimension's normalized
[0, 1] scale; preserve raw outputs separately and verify conversion in the adapter.

```json
[
  {"video_id": "dev_001", "dimension": "imaging_quality", "status": "success", "score": 0.5}
]
```

The example score is illustrative, not measured. Failure example:

```json
[
  {"video_id": "dev_001", "dimension": "imaging_quality", "status": "failed", "score": null, "error": "Video could not be decoded"}
]
```

Successful video scores receive equal weight within each method and dimension.
This descriptive mean is our aggregation, not necessarily the official VBench
aggregate. CSV includes planned, succeeded, failed and missing counts. No successful
scores yields null (blank CSV cell), never zero. Comparisons with unequal coverage
are not evidence of an unconditional improvement. Paired comparison, confidence
intervals, other native dimensions and plots remain future work. Batch execution is described below.

## Run the offline tools

From the repository root in PowerShell:

```powershell
$env:PYTHONPATH = 'src'
python -B -m unittest discover -s tests -p 'test_evaluation.py' -v
python -B -m moodcut.evaluation --manifest manifest.json --results results.json --dimensions imaging_quality --output summary.csv
```

The second command requires user-created inputs following the schemas above.
The output parent must exist. Existing output files are never overwritten.
This module entry point does not implement the shared project CLI.

## Environment and remaining decisions

Read-only hardware check found NVIDIA GeForce RTX 3060 Laptop GPU, 6144 MiB.
Availability does not establish sufficient memory or compatible dependencies.
The original offline increment did not install VBench or weights. The follow-up
installs isolated CPU dependencies and one checkpoint; GPU evaluation and paid
API requests remain outside the performed checks. Reference-cache validation found the 33 upstream
MovieAgent/FilmAgent files absent; they were not downloaded. These offline helpers
do not depend on those files.

Before formal evaluation or expansion to other metrics, confirm:

- Original VBench versus VBench++ / VBench 2.0, and an immutable revision.
- Selected dimensions and shot versus full-film evaluation.
- Available environment, model-weight storage and compute budget.
- Metadata agreement with the generation owner and formal experimental conditions.

## Contribution and validation boundaries

This increment provides original project glue code, metadata validation, explicit
coverage accounting, CSV reporting and hand-calculated regression tests. Credit
VBench for the underlying metrics. Tests use synthetic data only. No formal scores,
emotion improvements or full-pipeline evaluation success are claimed.


## Pinned imaging-quality integration

Upstream commit: `fd18b3d055cb0fc6f066ca90fe2c3c8cbb698490`.
The upstream checkout is not modified and is excluded from project commits.
Native `imaging_quality` output is `[aggregate, per_video_entries]`. Each entry's
`video_results` uses a 0..100 scale; the aggregate is divided by 100 upstream.
Our adapter divides each per-video score by 100 exactly once, checks the aggregate,
and rejects unknown/duplicate paths, invalid scores and paths outside the root.
Missing videos stay missing; they are not inferred to have failed.

Source: https://github.com/Vchitect/VBench/blob/fd18b3d055cb0fc6f066ca90fe2c3c8cbb698490/vbench/imaging_quality.py

The smoke runner generates eight 256x256 frames at 8 fps using OpenCV: a colored
circle moves over a gradient. This is a one-second software fixture, not a model
output or representative natural-video benchmark. The actual MUSIQ-SPAQ model
scores the encoded/decoded MP4 using VBench's unmodified implementation and
`longer` preprocessing. Inference runs on CPU with two PyTorch threads.

Checkpoint: `musiq_spaq_ckpt-358bb6af.pth` (108610983 bytes).
SHA-256: `358bb6af275e28ea56821d44fb55c6cb83645db11f394d3ad65b2d149965ab50`.
Source: https://github.com/chaofengc/IQA-PyTorch/releases/download/v0.1-weights/musiq_spaq_ckpt-358bb6af.pth

### Environment setup

Use a dedicated virtual environment. These commands are for the Windows CPU smoke
check, not a declaration that every VBench dimension works on Windows or CPU.

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cpu
.venv/Scripts/python -m pip install torch==2.5.1 torchvision==0.20.1 numpy==1.26.4 pyiqa==0.1.13 timm==1.0.12 transformers==4.37.2 decord==0.6.0 opencv-python==4.10.0.84 opencv-python-headless==4.10.0.84 bitsandbytes==0.45.5 accelerate==1.2.1
git clone https://github.com/Vchitect/VBench.git references/upstream/vbench
git -C references/upstream/vbench checkout fd18b3d055cb0fc6f066ca90fe2c3c8cbb698490
```

Download the checkpoint from the source above into
`runs/vbench-cache/pyiqa_model/`; the runner checks its complete SHA-256 and will
refuse missing or different weights. It does not automatically download weights.

### Run a fresh smoke check

From the project root, choose an output directory that does not already exist:

```powershell
$env:PYTHONPATH = 'src'
.venv/Scripts/python -B -c "from moodcut.evaluation import run_imaging_quality_smoke; print(run_imaging_quality_smoke(upstream_dir='references/upstream/vbench', cache_dir='runs/vbench-cache', output_dir='runs/vbench-smoke-new'))"
```

The runner records metadata, video/checkpoint hashes, package versions, raw native
JSON, normalized JSON and a summary CSV. Failure details are saved in `run.json`
when execution fails after the output directory is created. Initial revision,
checkpoint and output-path validation errors occur before output creation.
Keep failed attempts; use a new directory for a retry. Never report a failed
attempt as zero quality. Video/weights/runtime files stay in ignored directories.


## Verified smoke result (2026-10-14)

- Status: success, using the unmodified pinned VBench implementation on CPU.
- Test video: 1 second, 8 frames, 256x256, generated locally by the smoke runner.
- Native per-video MUSIQ score: 55.884440422058105.
- Normalized imaging_quality: 0.558844404220581.
- Elapsed time including imports/model loading: approximately 14.77 seconds.
- Video SHA-256: `6f58b4e90ca2d61a4fed94bbe42e9c90b7a4f467cba346d0d33a1ed9dba0c21c`.
- Local evidence: `runs/vbench-smoke-01/run.json`, `smoke_eval_results.json`,
  `normalized_results.json`, `manifest.json`, `summary.csv`, and the test MP4.
- Full local dependency snapshot: `runs/vbench-environment.txt`.
- Dependency consistency check: `pip check` passed.

This is a real model-computed score on a synthetic software fixture, not a mock
score and not a formal MoodCut result. It verifies only imaging_quality on this
CPU environment. It does not verify GPU execution, other dimensions, full-length
films, or scientific validity of an experimental comparison. No paid API was used.

The original VBench implementation and MUSIQ-SPAQ weights supply the metric; our
contribution is reproducible invocation, input/output adaptation, validation,
provenance and reporting. Preserve upstream attribution in any project report.


## Offline validation record

On 2026-10-14, the following command passed all 17 tests (11 evaluation tests
and 6 existing reference-tool tests) in the isolated Python 3.12.1 environment:

```powershell
$env:PYTHONPATH = 'src'
.venv/Scripts/python -B -m unittest discover -s tests -v
```

Coverage includes hand-calculated means, missing/failed counts, input validation,
source separation, duplicate rejection, native score conversion, aggregate
consistency, CSV output and refusal to overwrite results. The dependency check
also passed. These offline tests do not invoke model inference; the real smoke
result is documented separately above. Upstream source, weights, videos and the
virtual environment are excluded from the commit.

## 中文速览

已完成 VBench 单指标批量评估、失败记录及断点续跑；本次新增三条件输入身份和仅台词修改校验。
通过输入校验不等于视频合格或正式实验完成；当前媒体/资格和匿名导出接线见文末，正式实验仍待完成。


## Batch evaluation and resume

The `batch` entry point accepts the metadata list above and evaluates each video
with original VBench imaging_quality on CPU. Dependencies and verified weights
must already exist. Each clip runs in an isolated process, with a default timeout
of 300 seconds including imports and model loading. The model is loaded per clip;
this trades throughput for simple failure isolation. No paid API or automatic
weight download is involved. Use a fresh output directory for a new experiment.

```powershell
$env:PYTHONPATH = 'src'
.venv/Scripts/python -B -m moodcut.evaluation batch --manifest manifest.json --video-root assets/raw --upstream references/upstream/vbench --cache runs/vbench-cache --output runs/batch-01 --timeout 300
```

To continue the same run, repeat the identical command with `--resume`. Before
reusing results, the runner verifies the entire manifest, resolved video paths,
SHA-256 hashes of present inputs, missing-file state, benchmark/weight versions,
reporting module hash, Python environment/package versions, device, preprocessing
and timeout. Changed data, code or configuration requires a new output directory.
A previously missing file appearing is also a change. A manifest cannot mix formal,
development and synthetic sources or shot and film units.

A completed success or failure is not evaluated again. Interrupted, unfinished
items are evaluated on resume in a fresh attempt directory. Failed attempts are
retained; retrying failures or testing repaired videos requires a new run. Ordinary
Ctrl+C preserves committed items and releases the lock. Forced termination can
leave `batch.lock`: first verify that the recorded process is no longer running,
then remove only that stale lock before resuming. Do not run two writers against
the same output directory.

Artifacts:

- `checkpoint.json`: input/configuration identity and completed per-video records;
  written atomically after each item. This is the recovery source of truth.
- `normalized_results.json`: completed successes and explicit failures, including
  score/error, elapsed time, video hash and attempt directory.
- `summary.csv`: per-method means and planned/succeeded/failed/missing counts.
  Missing means not yet completed; an attempted absent file is an explicit failure.
- `item-*/worker.log`: decoder/model diagnostics for each attempted clip.
- `item-*/batch_eval_results.json` and `native_result.json`: raw successful results.

Derived JSON/CSV reports are regenerated from the checkpoint, including at resume.
No-success means remain null/blank. Exit code 0 means all items succeeded, 2 means
the batch finished with failed/missing items, and 1 indicates invalid input or a
setup failure. Setup problems in an individual worker are recorded as item failures
with details in its log. Check the counts and logs rather than interpreting any
CSV's existence as complete success. The runner does not certify cross-method
experimental comparability; formal pairing and analysis remain separate work.


### Batch validation evidence (2026-10-14)

- All 23 offline tests passed: 17 evaluation tests and 6 existing reference tests.
- Real CPU batch: valid video, deliberately corrupt MP4, second valid video,
  and missing file. Both valid videos completed; corrupt and absent files were
  retained as two failures, with zero unfinished items.
- Both valid inputs were copies of the same procedural fixture, so their measured
  scores were identical (0.558844404220581). They are not independent research samples.
- Resume completed in approximately 1.76 seconds, returned exit code 2 because
  failures remain, left checkpoint bytes unchanged, and created no new attempt
  directories (four before and after). No model was rerun.
- A separate offline KeyboardInterrupt test verifies that a completed first item
  survives interruption at the second item, and resume evaluates only unfinished
  items. Input-byte/configuration/metadata changes and newly appearing files are
  rejected on resume. Concurrent-writer locks and changed-during-evaluation files
  are also covered by tests.
- Local evidence: `runs/batch-validation-01/summary.csv`,
  `normalized_results.json`, `checkpoint.json`, `resume-validation.json`, and
  per-attempt worker logs. These runtime artifacts remain excluded from Git.

GPU performance, representative long videos, formal method comparisons and other
metrics have not been validated. This increment proves batch orchestration and
failure accounting, not MoodCut generation quality.


## Generated comparison input prerequisites (2026-10-20)

Current integration: the individual checks below are composed by the offline
qualification entry point described at the end of this document. Earlier test
counts are historical increment records. Generated blind export and ratings now
require the independent source/export rechecks described below; a qualification
report does not authorize a formal experiment.

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

This is the first increment of issue #9, not complete generated-run eligibility.
An empty error list does not certify receipts, reused jobs, media bytes, human
quality checks, costs or formal inclusion. Offline prepared fixtures may pass
these input checks. The function never sets `comparison_status=eligible` and
does not release generated exports/ratings without the independent rechecks. Final
`records` remain the accounting source; `preflight_records` must not be added as
another set of runs. Unknown costs remain unknown. Receipt and media evidence
must be connected through the existing P1/P4 interfaces in the next increment.

Before a formal run, the team still needs to freeze the following decisions:

| Decision | Current status |
| --- | --- |
| Development versus formal stories and repeat count | Not approved by this increment |
| Rater assignment and exclusion rules | Not approved by this increment |
| Inclusion of unchanged reviews and failed runs | Input validity only; analysis policy pending |
| Generation models, settings and budget stop | No paid run authorized by these tests |
| Emotion outcomes versus VBench quality dimensions | Separate outcomes; no formal claim from fixtures |

The comparison concerns dialogue-specific review versus generic review and the
baseline within the existing pipeline. These checks do not establish improved
actions, facial expressions, visual consistency or an effect of agent count.

Offline regression coverage includes spoofed identities, non-dialogue extensions,
changed shared settings, false unchanged labels, incomplete blocks, shot scopes,
malformed input and preservation of unknown cost fields. Fixtures are software
test inputs, not generated-video research results. No API, GPU, model download or
VBench inference is required. The reference-cache check currently reports missing
upstream files; these tests use repository contracts and local fixtures only.

Validation command: `python -B -m pytest tests/test_evaluation_paired.py tests/test_evaluation.py tests/test_contracts.py tests/test_validation.py -q`.
Result: 169 passed and 61 subtests passed. `git diff --check` also passed.


### Final-file identity check

`validate_generated_media_file(record, project_root=...)` is a separate, small
read-only prerequisite for a P1 final record. It requires completed generated
assembly, matching record/check paths, and a SHA-256 matching the current file
bytes. Relative paths resolve against the explicit project root. Replaced,
missing or malformed evidence returns diagnostics; inputs and unknown costs stay
unchanged. Reuse the existing file-hash implementation; no decoding is added.

This only detects stale final-file evidence at the time of checking. It does not
verify source clips, receipts, decoding, human judgments or experiment eligibility,
and is not yet wired into export. The export integration must check again at its
copy boundary to avoid relying on an earlier check. Synthetic byte fixtures in
these tests are deliberately not playable videos and do not certify quality.


### Ordered source bindings

`validate_generated_source_bindings(record, compiled_condition, project_root=...)`
adds a read-only source check. Supply one condition from an independently
validated P4 bundle and its final P1 record. It recomputes each complete request
hash, checks downloaded source-file bytes, and compares the ordered shot/request/
clip identities with the saved assembly sidecar. The sidecar's canonical JSON
hash and final-file fingerprint must match the P1 record. A single-clip record
without an assembly sidecar is accepted only when its final fingerprint equals
that clip's fingerprint, matching P1's single-shot path.

This check cannot authenticate an arbitrarily supplied bundle, validate provider
receipts or reuse accounting, or infer that pixels depict the intended request.
Those remain separate prerequisites; no status promotion or export wiring is
included. Tests use synthetic byte files and hand-written sidecars, not playable
media or model-quality evidence. All records and unknown costs stay unchanged.


### Saved receipt identity (2026-10-21)

`validate_generated_receipt_binding(job, expected_model=..., project_root=...)`
checks a P1 job against its saved receipt: canonical JSON snapshot hash, request
fingerprint, expected video model, task ID, downloaded status and video path.
Receipt-relative video paths resolve beside the receipt; record-relative paths
resolve against the supplied project root. Missing or changed receipts return
errors without polling, changing records or treating unknown costs as zero.

Use this together with independently validated bundle/request identities and
source-file checks. Matching local evidence does not authenticate a provider,
prove video quality or certify reuse ownership, HTTP totals or charges. This
helper does not require video bytes to exist; that is the preceding file check's
responsibility. No automatic eligibility or blind-export wiring is added.
Tests use hand-written synthetic receipts and no provider calls.


### Combined per-condition media diagnostics

`validate_generated_media_evidence(record, compiled_condition, project_root=...)`
composes the existing source/file and saved-receipt checks for one condition.
It reports receipt failures even when a file check fails, labels diagnostics by
shot, and takes the expected receipt model from the compiled request while also
checking the record's video_model_id. It does not modify or discard records.

The supplied P4 condition must still be independently validated against the
source plans/settings. Block input checks, same-block reuse ownership, accounting,
media decoding and human acceptance remain separate requirements. An empty list
is not comparison eligibility. No CLI/export gate is changed. Combined tests use
synthetic bytes and receipts, preserve not_checked and unknown costs, and include
simultaneous missing-receipt/replaced-file failures.


### Integration with actual P1/P4 outputs (2026-10-21)

`test_p5_reads_actual_inspection_records` reuses P4's existing inspection fixture
and calls its actual inspection interface. Actual P1/P2/P3/P4 code prepares and
assembles the three conditions with FakeClient, synthetic moving/audio files and
hand-written receipts. P5 accepts all three final records, including the records
containing reused shots, without changing their accounting or not_checked status.
Blank human judgments remain blank. Modifying a saved receipt after inspection
produces both snapshot and task-ID mismatch diagnostics.

This verifies interface compatibility, not independent reuse/accounting approval,
provider authenticity or video quality. Only final records are read as the ledger;
preflight snapshots are not added. The fixture's numeric bills are not actual
spending. FFmpeg and ffprobe must be on PATH; this run used version 9.0.1.

Validation: `python -B -m pytest tests/test_evaluation_paired.py tests/test_evaluation.py -q`
passed 49 tests and 88 subtests. No business code, CLI/export gate or paid execution
was changed for this increment.


### Unknown-cost integration regression

`test_p5_actual_unknown_cost_records_remain_unknown` passes actual P1/P4 output
with a legacy receipt through P5 media checks and the existing summary function.
Missing download counters and unknown provider cost remain unknown; the original
known subtotal is retained, all three final runs remain in coverage, and records
are not mutated. Media identity passing does not approve unknown costs or promote
comparison eligibility. The test supplies no ratings and uses synthetic media
and bills only. Focused evaluation regression: 50 tests and 88 subtests passed.


### Failed-generation integration regression

The actual-interface failure fixture produces one failed baseline and two
completed conditions. P5 rejects the failed record; all three final records stay
in coverage and unknown spending remains unknown. No ratings are supplied and
validation does not mutate the ledger. The test uses a synthetic failed receipt.

Current summary limitation: generation failures before rendering appear under
`render_pending_or_skipped_runs`, not `render_failed_runs`. Their explicit
`generation_status=failed` and `failure_kind=generation` remain in the raw record.
This test documents that existing behavior; it does not claim the summary already
has a separate generation-failure count. Adding such a count is a later reporting
increment. No business code or export gate changes are included here.


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
private mapping to exported bytes. Generation-failure summary categories, real
three-condition execution, formal protocol choices and actual human evaluation
remain separate follow-up work. No new sample, experiment condition, model call,
model download, GPU evaluation or subjective score is introduced here.


Qualification validation for this increment: the full offline suite passed 801
tests and 116 subtests (408.97 seconds); the 14 new qualification cases passed.
The CLI/original-file preservation case was rerun after the final verified-snapshot
binding adjustment and passed. The existing saved software inspection artifacts
also passed all three conditions with 98 source file hashes unchanged, under a
network-denying audit hook. Only new qualification/acceptance reports were saved.
FFmpeg/ffprobe 9.0.2 were used. All 33 cached references, 41 local document links,
Python syntax and diff whitespace checks passed. No provider request, real charge,
new experiment sample or human rating was produced.

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
anonymity. Real task execution, failure-category reporting, approved formal
protocol and independent viewers remain follow-up work.

Validation: the local full suite passed 815 tests and 116 subtests (578.18s).
After final boundary hardening, all 19 export/import regressions passed (331.72s);
the selected-shot export/import and raw-ledger directory compatibility cases
also passed separately. The PR CI reruns the final complete suite. An AST check
confirmed the scorer body is unchanged. Existing saved synthetic artifacts
exported three anonymous clips and validated an empty score import, with 106
source file hashes and the original ledger unchanged under a network-denying
audit hook (zero network attempts). Templates stayed blank; no real human scores
or new model media were produced. All 33 cached references, 43 local Markdown
targets, syntax, added-text privacy and whitespace checks passed.
