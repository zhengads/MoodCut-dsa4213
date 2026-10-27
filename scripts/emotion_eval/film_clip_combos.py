"""Classifier-only combos on saved features (no feature extraction)."""
import itertools, os, sys
from pathlib import Path
import sys as _sys
from pathlib import Path as _P
_sys.path.insert(0, str(_P(__file__).resolve().parent))
from _paths import REPO as _REPO, upstream_dir, work_dir
_sys.path.insert(0, str(_REPO / 'src'))

from moodcut import vemoclap_worker as w
os.environ.update(CUDA_VISIBLE_DEVICES="", TORCH_DEVICE="cpu")
import torch
UP = upstream_dir()
os.chdir(UP); sys.path.insert(0, str(UP / "src"))
import models_ as models
cfg = w._load_metadata(torch, UP / "weights/classifier/model_config.pt")
clf = models.AttentionClassifier(feature_dims=cfg["feature_dims"], d_model=cfg["d_model"], d_output=cfg["n_labels"], dropout=cfg["dropout"])
clf.load_state_dict(torch.load(UP / "weights/classifier/model.pt", map_location="cpu", weights_only=True)); clf.eval()
L = ("anger", "disgust", "fear", "joy", "sadness", "surprise")
R = work_dir() / "results2"
F = {d: torch.load(R / d / "features.pt") for d in os.listdir(R) if (R / d / "features.pt").exists()}
names = list(F["A3_affect_charade_phone"])

def cls(f):
    with torch.no_grad():
        p = torch.softmax(clf(f).squeeze().float(), -1).tolist()
    return " ".join(f"{k[:3]}={v*100:5.1f}" for k, v in zip(L, p))

a3 = F["A3_affect_charade_phone"]
print("A3 full           ", cls(a3))
z = lambda k: torch.zeros_like(a3[k])
for keep in (("beats", "clip"), ("beats", "clip", "asr_sentiment"), ("clip", "face_emotion"), ("beats", "face_emotion"), ("beats", "clip", "face_emotion")):
    print("A3 keep", "+".join(k[:5] for k in keep).ljust(24), cls({k: (a3[k] if k in keep else z(k)) for k in names}))
for other in ("A2_affect_charade_boat", "H1_hostile_hgf", "T2_tense_notld"):
    for k in ("face_emotion", "clip", "beats"):
        f = dict(a3); f[k] = F[other][k]
        print(f"A3 with {k[:5]} from {other[:2]}".ljust(26), cls(f))
