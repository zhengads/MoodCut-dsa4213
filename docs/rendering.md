# MoodCut Rendering

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

The CLI command is owned by MC-01; until that lands, call `render_plan` directly
from Python or tests.

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
