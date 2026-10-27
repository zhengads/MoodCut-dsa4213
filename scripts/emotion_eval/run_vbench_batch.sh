#!/usr/bin/env bash
# VBench imaging_quality batch over a manifest from make_vbench_manifest.py.
# Prerequisites: the pinned environment, VBench checkout and MUSIQ weights from docs/vbench.md.
# Usage: VBENCH_PY=<python of that environment> VBENCH_SRC=<VBench checkout at the pinned commit> \
#        VBENCH_CACHE=<folder with pyiqa_model/musiq_spaq_ckpt-358bb6af.pth> \
#        scripts/emotion_eval/run_vbench_batch.sh <manifest.json> <video-root> <output-dir>
set -euo pipefail
: "${VBENCH_PY:?}" "${VBENCH_SRC:?}" "${VBENCH_CACHE:?}"
manifest="$1"; video_root="$2"; output="$3"
cd "$(dirname "$0")/../.."
export PYTHONPATH=src HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1
"$VBENCH_PY" -B -m moodcut.evaluation batch --manifest "$manifest" --video-root "$video_root" \
  --upstream "$VBENCH_SRC" --cache "$VBENCH_CACHE" --output "$output" --timeout 600
