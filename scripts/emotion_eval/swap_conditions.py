import os, sys, itertools
from pathlib import Path
from moodcut import vemoclap_worker as w
import sys as _sys
from pathlib import Path as _P
_sys.path.insert(0, str(_P(__file__).resolve().parent))
from _paths import REPO as _REPO, upstream_dir, work_dir
_sys.path.insert(0, str(_REPO / 'src'))
os.environ.update(CUDA_VISIBLE_DEVICES="", TORCH_DEVICE="cpu")
import torch
UP = upstream_dir()
os.chdir(UP); sys.path.insert(0, str(UP / "src"))
import models_ as models
cfg = w._load_metadata(torch, UP / "weights/classifier/model_config.pt")
clf = models.AttentionClassifier(feature_dims=cfg["feature_dims"], d_model=cfg["d_model"], d_output=cfg["n_labels"], dropout=cfg["dropout"])
clf.load_state_dict(torch.load(UP / "weights/classifier/model.pt", map_location="cpu", weights_only=True)); clf.eval()
L = ("anger", "disgust", "fear", "joy", "sadness", "surprise")
R = work_dir() / "results3"
names = {"B": "01_Baseline_15s", "G": "02_Generic_Review_15s", "M": "03_MoodCut_15s"}
F = {k: torch.load(R / v / "features.pt") for k, v in names.items()}
def cls(f):
    with torch.no_grad():
        p = torch.softmax(clf(f).squeeze().float(), -1).tolist()
    top = max(range(6), key=lambda i: p[i])
    return " ".join(f"{k[:3]}={v*100:5.1f}" for k, v in zip(L, p)) + f"  -> {L[top]}"
for stream in ("beats", "clip", "face_emotion", "asr_sentiment"):
    print(f"## swap only [{stream}] : rows = base video, cols = {stream} taken from")
    for base in "BGM":
        for src in "BGM":
            f = dict(F[base]); f[stream] = F[src][stream]
            print(f"  base={base} {stream}<-{src}: {cls(f)}")
print("## swap [clip+face] together (visual stream) and keep own audio/asr")
for base in "BGM":
    for src in "BGM":
        f = dict(F[base]); f["clip"] = F[src]["clip"]; f["face_emotion"] = F[src]["face_emotion"]
        print(f"  base={base} visual<-{src}: {cls(f)}")
