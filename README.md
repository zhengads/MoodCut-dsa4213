# MoodCut

**English** | [简体中文](README.zh-CN.md)

[![MoodCut v4 framework](docs/images/moodcut-v4-en.png)](docs/images/moodcut-v4-en.svg)

**Let characters review dialogue against a target emotion, then let a shared screenwriter revise it.**

MoodCut is a DSA4213 course research project. Given a story, two character references and a target tone, it plans a shared scene and compares general script review with emotion-oriented Actor review. The research question is whether focused emotional feedback can help the resulting video convey the intended tone while keeping the story clear and the dialogue natural.

[Watch videos and compare dialogue](https://zhengads.github.io/MoodCut-dsa4213/) · [Quick start](#quick-start) · [Documentation](docs/README.md) · [Usage](docs/usage.md) · [Method](docs/ACTOR_REVIEW_METHOD.md) · [Development](#development)

## Method and comparison

The diagram and table describe the **v4 development protocol** used in the latest S01 case:

| Condition | Behavior |
| --- | --- |
| `baseline` | Keep the draft produced by the shared planning Agent, without review or revision. |
| `generic_review` | One global reviewer checks both characters' dialogue; a screenwriter Agent integrates the feedback. |
| `moodcut` | Two independent Actors inspect their own character's intent, subtext and emotional-expression gaps; the same screenwriter integrates their feedback. |

Both review conditions allow up to two revisions. Every candidate is revisited by the original reviewers. With no initial issues, the draft is retained; final disagreements remain recorded. Revision opportunities are matched, while call counts and costs may differ. API/contract errors, unknown charges and budget failures stop the flow.

In generated mode, **only dialogue may change**. Scene directions, actions, camera, character references, voices and generation settings remain common inputs. A fixed seed does not guarantee identical visuals after dialogue changes.

**Version boundary: the runtime on main remains v3**, which uses two Actors in each reviewed condition. V4 has been exercised in a separate development snapshot, and its runtime implementation has not been merged. This update publishes the bilingual overview and diagrams only. See the [method history](docs/ACTOR_REVIEW_METHOD.md) and [actual S01 v4 record](docs/pilots/s01-v4-text-video.md).

## Current progress

As of 2026-10-25, the latest **S01 v4 video comparison** is available: [watch it](https://zhengads.github.io/MoodCut-dsa4213/#s01-v4) · [reviews, revisions, revisits and costs](docs/pilots/s01-v4-text-video.md). Generic review retained the draft; MoodCut changed one Kristoff line and revisited both Actors. Three condition entries correspond to two independently generated videos, with generic review reusing baseline. Successful text and video generation cost **$0.504356**. The gallery temporarily hides entries without completed videos; failure records and costs remain preserved.

The earlier S06 v3 development run produced three real videos for **$0.75421676**. [Watch them](https://zhengads.github.io/MoodCut-dsa4213/#s06-index) · [run record and original results](docs/pilots/s06-actor-v3-index.md)

These cases demonstrate technical execution. Spoken Chinese, character consistency, naturalness and emotional effects still require human inspection and independent evaluation. Successful and failed attempts remain in the [pilot records](docs/pilots/).

The candidate study inputs are [six clear-emotion stories v2](docs/studies/six-story-clear-emotions-20261024/README.md): two each for affectionate, hostile and tense tones. They are research inputs awaiting execution; confirming their scope does not authorize paid runs or formal evaluation.

## Quick start

Requires **Python 3.11+**. Run from the repository root; the examples use PowerShell on Windows:

```powershell
git clone https://github.com/zhengads/MoodCut-dsa4213.git
cd MoodCut-dsa4213
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/python -m moodcut smoke --mock --output runs/smoke-01
```

On Linux/macOS, replace `.venv/Scripts/python` with `.venv/bin/python`.

`smoke` checks the three-condition JSON flow without network access, API keys or video rendering. Use a new output directory for each run.

### Render an offline preview

Install **FFmpeg and ffprobe** on PATH and a Chinese font, such as Microsoft YaHei on Windows or Noto Sans CJK on Linux. Then run:

```powershell
.venv/Scripts/python -m moodcut run --mock --scene tests/fixtures/scene.json --assets tests/fixtures/assets.json --output runs/demo-01
.venv/Scripts/python scripts/compare_demo.py --run runs/demo-01
Start-Process (Resolve-Path runs/demo-01/comparison.html).Path
```

The output contains a shared draft, three condition records and three static animatics. These software fixtures validate the pipeline, not the method's effectiveness. Select a font with `--font` or `MOODCUT_FONT` if needed.

### Choose an entry point

| Task | Entry point and scope |
| --- | --- |
| Check the text flow | `smoke --mock`: offline JSON, without video. |
| Preview still images and subtitles | `run --mock`: the default animatic flow. |
| Prepare video requests from saved generated scripts | `run --output-mode generated --source-block ...`: compile requests only. |
| Execute prepared video requests | `execute-generated`: offline by default; real calls need an explicit model, scope and budget. |
| Inspect saved videos, export anonymized media or import ratings | [Usage guide](docs/usage.md#检查与评价生成视频). |

**Default `plan/review/smoke/run` commands still use the original animatic flow and do not enable Actor v3 automatically.** V3 must be selected explicitly during generated-script orchestration. Script preparation, request compilation and video generation are separate stages. See the [generated-video workflow](docs/usage.md#生成式视频流程) for parameters and prerequisites.

## Documentation

| Topic | Reference |
| --- | --- |
| Commands, outputs, API configuration and assets | [Usage](docs/usage.md) |
| Actor review, writer revisions and protocol versions | [Method](docs/ACTOR_REVIEW_METHOD.md) |
| Data structures, interfaces, shared identity and accounting | [Contracts](docs/CONTRACTS.md) |
| Static rendering, request compilation and video inspection | [Rendering](docs/rendering.md) |
| Anonymized export, human ratings, coverage and cost summaries | [Evaluation](docs/evaluation.md) |
| Character references, sources and license status | [Animation asset library](assets/library/README.md) |
| Settings, results and failures from previous trials | [Pilot records](docs/pilots/) |
| Module ownership, task cards and branch rules | [Team workflow](docs/TEAM.md) · [Branch rules](docs/BRANCHES.md) |

## Development

Read [AGENTS.md](AGENTS.md) and the [team workflow](.agents/skills/moodcut-team/SKILL.md), check Issues and existing PRs, and claim only unfinished increments. The shared startup instructions are in [developing a task with AI](docs/usage.md#用-ai-开发一个任务).

```powershell
git config commit.template .gitmessage
.venv/Scripts/python -m pytest -q
.venv/Scripts/python scripts/prepare_references.py --check
```

Video tests require FFmpeg/ffprobe and a usable font; set `MOODCUT_TEST_FONT` when needed. If the reference cache is missing, follow the [reference preparation guide](docs/REFERENCES.md). Ordinary tests and CI do not call paid models.

```text
src/moodcut/         Core modules; prompts/ holds model prompts
configs/            Model, rendering and experiment configuration
tests/              Offline tests and fixtures/
scripts/            Asset preparation, video inspection and comparison
docs/               Methods, contracts, tasks and pilot records
assets/             Asset metadata; original images stay in ignored folders
references/         Source locks, reading index and local caches
runs/               Local run outputs, excluded from Git
```

## References and reuse

MoodCut draws on **MovieAgent** for staged planning and asset organization, and **FilmAgent** for review–revision–recheck collaboration. These are independent adaptations to this project's contracts, not complete reproductions of either paper.

Pinned versions, reading paths and citations are listed in [References](docs/REFERENCES.md) and [references.bib](references/references.bib); the adopted scope is recorded in [Reuse notes](docs/upstream-reuse.md). Attribution and provider acceptance do not establish permission to use or redistribute character images. Original images are not committed to Git.
