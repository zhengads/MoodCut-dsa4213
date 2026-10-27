"""Probe the audio track of each video: loudness stats, BEATs AudioSet tags (whole + 5s windows), Whisper transcript + sentiment."""
import argparse, json, os, sys
from pathlib import Path
import sys as _sys
from pathlib import Path as _P
_sys.path.insert(0, str(_P(__file__).resolve().parent))
from _paths import REPO as _REPO, upstream_dir, work_dir
_sys.path.insert(0, str(_REPO / 'src'))

UP = upstream_dir()
ap = argparse.ArgumentParser()
ap.add_argument("--videos", nargs="+", type=Path, required=True)
ap.add_argument("--out", type=Path, required=True)
a = ap.parse_args()
os.environ.update(CUDA_VISIBLE_DEVICES="", TORCH_DEVICE="cpu", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", MPLBACKEND="Agg")
import numpy as np
import torch
torch.cuda.is_available = lambda: False
torch.set_num_threads(2)
sys.path.insert(0, str(UP / "src"))
os.chdir(UP)
import models_ as models, utils

beats = models.BEATSRunner(predict=True); beats.to_device("cpu"); beats.eval()
res = {}
for v in a.videos:
    dur = utils.get_video_duration(str(v))
    frames, audio, _, sr = utils.extract_frames_and_audio(str(v), output_fps=16 / dur, size=360)
    mono = np.asarray(audio).mean(0) if np.asarray(audio).ndim > 1 else np.asarray(audio)
    mono = mono.astype("float32")
    r = {"duration_s": dur, "sr": sr}
    # loudness per second (dBFS RMS)
    n = int(sr)
    rms = [float(20 * np.log10(np.sqrt(np.mean(mono[i:i + n] ** 2)) + 1e-9)) for i in range(0, len(mono) - n + 1, n)]
    r["rms_db_per_s"] = [round(x, 1) for x in rms]
    r["peak_db"] = round(float(20 * np.log10(np.abs(mono).max() + 1e-9)), 1)
    r["frac_seconds_below_-50dB"] = round(float(np.mean(np.array(rms) < -50)), 2)
    with torch.no_grad():
        out = beats.process_video(input_tensor=torch.tensor(mono).unsqueeze(0), sr=sr, n_frames=16, num_workers=0)
        r["beats_tags_whole"] = [(t, round(p, 3)) for t, p in out["predictions"]]
        wins = []
        step = int(5 * sr)
        for s in range(0, len(mono) - step + 1, step):
            seg = torch.tensor(mono[s:s + step]).unsqueeze(0)
            o = beats.process_video(input_tensor=seg, sr=sr, n_frames=8, num_workers=0)
            wins.append({"t": f"{s // step * 5}-{s // step * 5 + 5}s", "tags": [(t, round(p, 3)) for t, p in o["predictions"]]})
        r["beats_tags_5s_windows"] = wins
    res[v.parent.name + '/' + v.stem] = r
    print("done", v.stem, flush=True)
a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
