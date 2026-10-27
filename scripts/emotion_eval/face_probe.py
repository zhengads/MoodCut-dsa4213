"""Probe: what does the upstream face detector/classifier see in a clip? Saves crops and prints per-frame results."""
import argparse, os, sys
from pathlib import Path
import sys as _sys
from pathlib import Path as _P
_sys.path.insert(0, str(_P(__file__).resolve().parent))
from _paths import REPO as _REPO, upstream_dir, work_dir
_sys.path.insert(0, str(_REPO / 'src'))

UP = upstream_dir()
ap = argparse.ArgumentParser()
ap.add_argument("--video", type=Path, required=True)
ap.add_argument("--out", type=Path, required=True)
a = ap.parse_args()
a.out.mkdir(parents=True, exist_ok=True)
os.environ.update(CUDA_VISIBLE_DEVICES="", TORCH_DEVICE="cpu", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", MPLBACKEND="Agg")
import torch
import numpy as np
torch.cuda.is_available = lambda: False
torch.set_num_threads(2)
os.chdir(UP)
sys.path.insert(0, str(UP / "src"))
import models_ as models, utils
from PIL import Image

dur = utils.get_video_duration(str(a.video))
frames, audio, _, sr = utils.extract_frames_and_audio(str(a.video), output_fps=16 / dur, size=360)
print("frames", tuple(frames.shape), flush=True)
fe = models.FaceExtractAndClassify()
fe.to_device("cpu")
fe.eval()
with torch.no_grad():
    for i, fr in enumerate(frames):
        fr = fr.squeeze()
        Image.fromarray(fr.numpy() if hasattr(fr, "numpy") else fr).save(a.out / f"frame_{i:02d}.jpg") if False else None
        faces, coords = fe.face_detector_model(fr)
        line = f"frame {i:02d} faces={len(faces)} coords={coords}"
        for j, f in enumerate(faces):
            Image.fromarray(np.asarray(f).astype("uint8")).save(a.out / f"frame_{i:02d}_face{j}.png")
            out = fe.face_emotion_model(f)
            p = out["predictions"]
            line += f" | shape={np.asarray(f).shape} pred={p}"
        print(line, flush=True)
