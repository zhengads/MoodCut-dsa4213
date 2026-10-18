# MoodCut Rendering

## Generated request compilation (1.1)

`video_generation.build_generated_video_bundle` implements CONTRACTS 6.5/6.12.
It validates the complete initial plan and all three final plans with the public
generated validator, checks dialogue-only changes and recomputes the shared
identity for every condition. It rejects changed actions, timing, references and
unknown non-dialogue extensions; it never projects or repairs a candidate.

```python
from moodcut.video_generation import build_generated_video_bundle, get_video_template_sha256

# Freeze this hash when calling pipeline.run_experiment, before splitting conditions.
template_sha256 = get_video_template_sha256()
bundle = build_generated_video_bundle(
    scene, initial, plans, manifest, settings,
    project_root=project_root, template_sha256=template_sha256,
    pricing_config=pricing_config,
)
```

Inputs are explicit 1.1/generated Scene, Plan and GenerationSettings; `plans`
contains exactly baseline/generic_review/moodcut. Settings supply shared model,
style, sound, voice and seed values, with no per-condition overrides. Actions,
camera and integer durations come from `initial.scene_direction` and
`initial.shots[].direction/duration_s`, not the old configuration's `shots`.
The public helper validates the exact settings fields and character bindings.

The shipped `src/moodcut/prompts/video_generated.txt` is the common template.
Its effective UTF-8 text (universal newlines) determines the template identity,
using the same text for hashing and rendering. A source block frozen with a
different template is rejected; do not edit its hash in place to pass the gate.
The shared JSON section includes style, sound, tone, scene/shot direction,
duration, visual mappings, reference indices and character/voice bindings.
Only the final `DIALOGUE_JSON` section varies between conditions. Narration is
retained in source identity but is not turned into spoken text. Unknown plan
extensions remain identity-protected, not new untyped model controls.

All `scene.asset_ids` images become `input_references` in that order, with explicit
reference-index/character mappings and primary-reference markers from settings.
Local image bytes, dimensions and hashes must validate; every reference needs a
public HTTPS `source_url`. Preparation does not fetch those URLs or establish
that their remote bytes match the local file or that a provider accepts them.
No card first frames, subtitles or narration audio are synthesized. The model
request keeps native audio and `seed = settings.seed + original shot index`.

Each job contains a full request, `request_sha256` and decimal-string
`quoted_cost_usd`, calculated by the existing `video_client.estimate_video_cost`.
The separate pricing input needs model/resolution/aspect_ratio and the applicable
rate. The old `configs/video.json` can supply that local price snapshot, but its
letter-specific directions, style and character settings are ignored by this
compiler. That 1.0 example is a team-authored development adaptation using
MovieAgent character references, not an upstream story or a formal sample.
This change does not switch the default model or refresh prices.

A conservative shared feasibility gate rejects more than eight dialogue
characters per requested second; it is not a calibrated speech-speed or quality
predictor. Unsupported model/duration/price combinations fail through the existing
quote helper. No lengthening, shortening, extra model call or static fallback occurs.

Consume saved scripts through the existing offline entry, without a new runner:

```bash
python -m moodcut run --output-mode generated --source-block runs/generated-scripts/block.json --pricing-config configs/video.json --output runs/generated-requests
```

Add `--shot-id <actual-id>` to select one common shot after full compilation.
Output is `bundle.json`, `preparation.json`, full `source_inputs.json` and the
original `source_block.json` ledger. Preparation has zero new calls/spending,
no video, and comparison `not_checked`; the quote is neither spending nor live
pricing. No key, client construction, catalogue query, submission or polling
occurs. The original scripts and historical expenses are preserved.

Tests use actual planner/reviewer/pipeline/compiler functions with hand-written
FakeClient JSON for letter and bus-stop umbrella software stories. Local moving
test patterns and sine audio exercise the existing receipt assembler and
same-request reuse accounting; they are not generated acting or speech.
Existing `assemble_generated_clips` and the asynchronous video client remain
the media/transport implementations. Local bound inspection packages are
implemented below. Three-condition paid execution, P5 qualification and actual
quality acceptance remain unfinished.
Fixed seeds do not guarantee unchanged visuals or voices after a dialogue edit.

## Local video inspection and source binding (1.1)

Use already-prepared requests and the local receipt/evidence format from
CONTRACTS 6.9. This command cannot submit, resume or download a video job:

```bash
python scripts/inspect_generated_video.py --preparation runs/generated-requests --evidence runs/local-evidence.json --media-origin provided_local --output runs/video-inspection
```

Use `--media-origin synthetic` for software test media. `provided_local` only
declares supplied local files; it does not certify provider output. This flag is
required. `--project-root` resolves CLI paths; pricing defaults to the existing
`configs/video.json` snapshot and must match preparation. No key or paid flags
are accepted. Source preparation, scripts, assets and receipts must remain
available. Existing output directories are rejected.

The program API is `inspect_generated_video(preparation, *, evidence, out_dir,
pricing_config, media_origin, project_root=".")`. It uses the existing P1
`assemble_generated_records` for preflight, including actual local A/V and reuse
checks. It copies verified clips to fixed numeric file names, reuses a validated
existing assembly or calls `assemble_generated_clips`, then rechecks bytes and
durations. It binds every film to the ordered
`source_clips=[{shot_id, request_sha256, sha256}]` plus the film's SHA-256 and
relative `video_path`. Block/shared/initial/selected identities and source-file
details are retained. No shot IDs become output paths.

The output contains:

- `index.html`: local development viewing page, showing conditions, target,
  common directions and expected dialogue. This is not blind evaluation or ASR.
- Per ready condition: `film.mp4`, copied `clips/`, `frames/`,
  `contact_sheet.png`, `ffprobe.json` (actual streams/format and summary), and
  `media_check.json` with source/request/file bindings. Each contact-sheet row
  samples a shot at 10%, 50%, 90%; sample hashes/times are recorded.
- `manual_checks.csv` and `manual_checks.json`: identity-linked rows for
  character/action, dialogue/speaker, audio/lip sync, continuity and notes.
  Judgment cells are blank/null, status `not_reviewed`. Save a separate filled
  copy after watching. CSV identifiers with formula prefixes are escaped;
  JSON retains exact identifiers.
- `inspection.json`: readiness, declared origin, identities and zero new API
  activity; `evidence.json`: derived local pointers to the checks, with original
  evidence preserved in `preflight_records/evidence.json`.
- `records/block.json`: P1's final revalidation of original receipts, source
  clips and new bound films. `preflight_records/` is an earlier snapshot of the
  **same** history; do not add its fees to `records/`. Neither pass sends requests.

Failed, missing or unfinished clips keep their P1 states and known/unknown bills;
they do not acquire a static-image substitute. Other valid conditions can still
produce diagnostic materials. Binding, byte, A/V or assembly errors stay failed,
with no player advertised for that condition. New outputs retained after a
processing failure are diagnostics, not a completed inspection. Structural
preflight rejection creates no successful package. Records remain
`comparison_status=not_checked` or `ineligible`, never `eligible`.

CLI exit 0 means all selected conditions have materials ready for manual
inspection, not that quality passed. Missing work returns `incomplete`/exit 1;
errors return `failed`/exit 1. Single-shot preparation inspects only that shot
while retaining full-plan identity; it is not a complete multi-shot film.
Unknown legacy cost/GET history stays null even if the files pass checks.

The page and packaged media use relative links and need no server or network.
P1 record revalidation still requires original source inputs/receipts. Actual
motion, speech, speaker, lip sync, continuity and emotion require a viewer;
sampled frames and audio-stream presence are not automatic quality judgments.
Tests use labeled synthetic moving patterns/sine audio, not real model footage.

## Static animatic (1.0)

MC-04 renders ShotPlan dictionaries into a deterministic static animatic. The
renderer writes one PNG per shot, a contact sheet, a timeline JSON and a silent
H.264 MP4 assembled from the still frames.

## Requirements

- Python 3.11+
- Pillow available in the environment
- FFmpeg and ffprobe available on `PATH`
- A caller-provided UTF-8 capable TrueType/OpenType font path

The renderer does not download fonts or media. Asset paths come from the
manifest and are resolved under `project_root`. Existing non-empty output
directories are rejected so previous renders are not silently overwritten.

## Output

`render_plan(plan, manifest, project_root=..., out_dir=..., font_path=...)`
creates:

- `frames/shot_XX_<shot_id>.png`: 1280x720 static frame at 24fps target
- `contact_sheet.png`: thumbnail overview of rendered shots
- `timeline.json`: shot start/end times, durations, frame paths and subtitles
- `animatic.mp4`: H.264/yuv420p, 24fps, no audio track

The returned RenderResult follows `docs/CONTRACTS.md`. Failures return
`status: "render_failed"` with an error message. `timeline.json` includes the
ffprobe width, height, frame rate and duration used to verify the MP4.

## Layout Rules

Frames use a fixed 16:9 canvas with a uniform background. A single visual is
centered; two visuals are placed in fixed left and right cards. Images are
contained without stretching. `full` uses the whole image, while `center_close`
crops the center 60 percent of width and height before fitting.

Dialogue captions are prefixed with `character_id` because the renderer receives
only the plan and manifest, not the full scene character names. Narration is
prefixed with `叙述` so the animatic does not imply new generated action.

## Examples

macOS:

```bash
python -m moodcut render \
  --plan tests/fixtures/plan.json \
  --assets tests/fixtures/assets.json \
  --font /System/Library/Fonts/PingFang.ttc \
  --output runs/dev/render
```

Linux:

```bash
python -m moodcut render \
  --plan tests/fixtures/plan.json \
  --assets tests/fixtures/assets.json \
  --font /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf \
  --output runs/dev/render
```

The existing `render` CLI is owned by MC-01; `render_plan` is also callable
directly from Python or tests.

Direct Python example:

```bash
PYTHONPATH=src python - <<'PY'
import json
from pathlib import Path
from moodcut.renderer import render_plan

root = Path(".").resolve()
plan = json.loads((root / "tests/fixtures/plan.json").read_text())
manifest = json.loads((root / "tests/fixtures/assets.json").read_text())
print(render_plan(
    plan,
    manifest,
    project_root=str(root),
    out_dir="runs/dev/render",
    font_path="/System/Library/Fonts/PingFang.ttc",
))
PY
```
