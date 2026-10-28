# MoodCut

**Let characters review dialogue against a target emotion, then let a shared screenwriter revise it.**

MoodCut is a DSA4213 research project exploring whether character-specific emotional feedback helps generated videos convey an intended emotion while keeping dialogue natural and the story clear.

[Watch the 12 videos](https://zhengads.github.io/MoodCut-dsa4213/) · [Download videos](https://github.com/zhengads/MoodCut-dsa4213/releases/tag/Videos_01-12) · [Script catalog](docs/studies/six-story-clear-emotions-20261024/README.md) · [Documentation](docs/README.md)

## Comparison

| Condition | Dialogue workflow |
| --- | --- |
| Baseline | Keep the shared initial draft. |
| Generic Review | A global reviewer checks the dialogue; a screenwriter revises it. |
| MoodCut | Each character reviews its own dialogue for emotional expression; the same screenwriter combines the feedback. |

Both review conditions allow at most two revisions and revisit each candidate. Only dialogue may change; scene directions, actions, camera, character references, voices and generation settings remain shared. A fixed seed does not guarantee identical visuals.

The gallery contains **12 stories numbered 01–12**, with three condition entries per story. The 36 entries contain 28 distinct video files, each approximately eight seconds long. These examples do not establish effectiveness; independent human evaluation remains outstanding.

## Quick start

Requires Python 3.11+. From the repository root:

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/python -m moodcut smoke --mock --output runs/smoke-01
```

On Linux/macOS, use `.venv/bin/python`. The smoke command checks the offline JSON flow without API keys or paid calls; choose a new output directory for each run.

For generated video preparation, protocol selection, rendering and scoring, follow the [usage guide](docs/usage.md). The default offline demo is a static animatic; generated video execution is a separate workflow.

## Development

Read [AGENTS.md](AGENTS.md) and the [team workflow](.agents/skills/moodcut-team/SKILL.md) before making changes.

```powershell
git config commit.template .gitmessage
.venv/Scripts/python -m pytest -q
.venv/Scripts/python scripts/prepare_references.py --check
```

Video tests require FFmpeg/ffprobe and a usable font. Ordinary tests and CI do not call paid models.

## References

MoodCut adapts planning and asset organization ideas from MovieAgent and review–revision collaboration from FilmAgent. See [references](docs/REFERENCES.md), [citations](references/references.bib) and [reuse notes](docs/upstream-reuse.md). Character references and source attribution are documented in the [asset library](assets/library/README.md).
