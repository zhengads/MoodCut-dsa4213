# VBench imaging_quality 工具

[返回评价说明](evaluation.md) · [历史记录](history/README.md)

本页说明已固定版本的单指标工具，不代表完整 VBench 或情绪评价。安装/模型推理需按实际任务授权；本次文档整理不运行推理。

## Scope

Offline helpers validate video metadata and summarize per-video scores. The second
increment adds a pinned native imaging_quality adapter and an explicitly invoked
CPU smoke runner. Neither synthetic-video scores nor tool success establish that
the project generates high-quality videos. The paired human-rating interfaces in evaluation.md are implemented independently of these VBench helpers; neither replaces the other.

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
narrative quality, or audio quality. The paired human emotion evaluation in evaluation.md remains the primary assessment of the project hypothesis. Report dimensions separately, without inventing a total score.

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

This is the adapter's normalized internal format, not VBench's native JSON format. The imaging_quality adapter supports the pinned original VBench revision below.
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



## Historical validation (2026-10-14)

These are preserved measurements on synthetic software media, not new results from this documentation cleanup.

### Synthetic smoke

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



### Synthetic batch and resume


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
