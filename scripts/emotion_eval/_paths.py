"""Path helpers shared by the emotion-evaluation scripts.

Nothing is hard-coded: point these environment variables at your own directories.

VEMOCLAP_UPSTREAM  checkout of the upstream VEMOCLAP code with its weights (see docs/vemoclap.md)
MOODCUT_EVAL_WORK  working directory that holds the videos and the per-video result folders
"""
import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
STUDY = REPO / "docs" / "studies" / "emotion-evaluation-20261027"


def _env_dir(name: str) -> Path:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Set the {name} environment variable (see scripts/emotion_eval/README.md).")
    return Path(value).expanduser().resolve()


def upstream_dir() -> Path:
    return _env_dir("VEMOCLAP_UPSTREAM")


def work_dir() -> Path:
    return _env_dir("MOODCUT_EVAL_WORK")
