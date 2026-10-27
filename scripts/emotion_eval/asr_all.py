"""Transcribe (Whisper large-v3 via the upstream wrapper, translate-to-English) the audio of every manifest video."""
import argparse, json, os, sys
from pathlib import Path
import sys as _sys
from pathlib import Path as _P
_sys.path.insert(0, str(_P(__file__).resolve().parent))
from _paths import REPO as _REPO, upstream_dir, work_dir
_sys.path.insert(0, str(_REPO / 'src'))

UP = upstream_dir()
ap = argparse.ArgumentParser()
ap.add_argument("--manifest", type=Path, required=True)
ap.add_argument("--out", type=Path, required=True)
a = ap.parse_args()
os.environ.update(CUDA_VISIBLE_DEVICES="", TORCH_DEVICE="cpu", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", MPLBACKEND="Agg")
import torch
torch.cuda.is_available = lambda: False
torch.set_num_threads(2)
sys.path.insert(0, str(UP / "src"))
os.chdir(UP)
import models_ as models, utils
import numpy as np

asr = models.ASRSentiment()
asr.to_device("cpu")
items = json.loads(a.manifest.read_text(encoding="utf-8"))
out = []
for it in items:
    dur = utils.get_video_duration(it["path"])
    _, audio, _, sr = utils.extract_frames_and_audio(it["path"], output_fps=16 / dur, size=360)
    mono = np.asarray(audio).mean(0) if np.asarray(audio).ndim > 1 else np.asarray(audio)
    with torch.no_grad():
        o = asr.process_video(input_tensor=torch.tensor(mono.astype("float32")).unsqueeze(0), sr=sr)
    rec = {k: it[k] for k in ("id", "set", "condition", "intended")}
    rec["asr_text"] = o["asr"]
    rec["language"] = o["language"]
    out.append(rec)
    print("done", it["id"], "|", o["asr"][:80], flush=True)
    a.out.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
