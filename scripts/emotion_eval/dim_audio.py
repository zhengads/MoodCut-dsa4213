"""Run the audEERING dimensional speech-emotion model (arousal, dominance, valence ~0..1) on the audio of videos.
Whole clip plus consecutive 5 s windows. Local files only (offline)."""
import argparse, json, os, subprocess, sys, tempfile
from pathlib import Path
import sys as _sys
from pathlib import Path as _P
_sys.path.insert(0, str(_P(__file__).resolve().parent))
from _paths import REPO as _REPO, upstream_dir, work_dir
_sys.path.insert(0, str(_REPO / 'src'))

ap = argparse.ArgumentParser()
ap.add_argument("--model", type=Path, required=True)
ap.add_argument("--manifest", type=Path, required=True, help="json: list of {id, set, condition, path}")
ap.add_argument("--out", type=Path, required=True)
ap.add_argument("--ffmpeg", default="ffmpeg")
a = ap.parse_args()
os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", CUDA_VISIBLE_DEVICES="")
import numpy as np
import torch
import torch.nn as nn
from transformers import Wav2Vec2FeatureExtractor
from transformers.models.wav2vec2.modeling_wav2vec2 import Wav2Vec2Model, Wav2Vec2PreTrainedModel

torch.set_num_threads(2)


class RegressionHead(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.dense = nn.Linear(config.hidden_size, config.hidden_size)
        self.dropout = nn.Dropout(config.final_dropout)
        self.out_proj = nn.Linear(config.hidden_size, config.num_labels)

    def forward(self, features):
        x = self.dropout(features)
        x = torch.tanh(self.dense(x))
        return self.out_proj(self.dropout(x))


class EmotionModel(Wav2Vec2PreTrainedModel):
    def __init__(self, config):
        super().__init__(config)
        self.wav2vec2 = Wav2Vec2Model(config)
        self.classifier = RegressionHead(config)
        self.post_init()

    def forward(self, input_values):
        hidden = self.wav2vec2(input_values)[0].mean(dim=1)
        return self.classifier(hidden)


extractor = Wav2Vec2FeatureExtractor.from_pretrained(str(a.model))
model = EmotionModel.from_pretrained(str(a.model)).eval()
NAMES = ("arousal", "dominance", "valence")


def load_audio(path, sr=16000):
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "a.wav"
        subprocess.run([a.ffmpeg, "-v", "error", "-y", "-i", str(path), "-vn", "-ac", "1", "-ar", str(sr),
                        "-c:a", "pcm_s16le", str(wav)], check=True)
        import wave
        with wave.open(str(wav), "rb") as w:
            data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype("float32") / 32768.0
    return data


def predict(y, sr=16000):
    x = extractor(y, sampling_rate=sr, return_tensors="pt")["input_values"]
    with torch.no_grad():
        out = model(x).squeeze(0).tolist()
    return {k: round(float(v), 4) for k, v in zip(NAMES, out)}


items = json.loads(a.manifest.read_text(encoding="utf-8"))
res = []
for it in items:
    y = load_audio(it["path"])
    sr = 16000
    rec = dict(it)
    rec["duration_s"] = round(len(y) / sr, 2)
    rec["rms_dbfs"] = round(float(20 * np.log10(np.sqrt(np.mean(y ** 2)) + 1e-9)), 1)
    rec["whole"] = predict(y)
    rec["windows_5s"] = []
    step = 5 * sr
    for s in range(0, len(y) - step + 1, step):
        rec["windows_5s"].append({"t": f"{s // sr}-{s // sr + 5}s", **predict(y[s:s + step])})
    res.append(rec)
    print("done", it["id"], rec["whole"], flush=True)
a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
