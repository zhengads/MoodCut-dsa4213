import os, sys
from pathlib import Path
from moodcut import vemoclap_worker as w
import sys as _sys
from pathlib import Path as _P
_sys.path.insert(0, str(_P(__file__).resolve().parent))
from _paths import REPO as _REPO, upstream_dir, work_dir
_sys.path.insert(0, str(_REPO / 'src'))
os.environ.update(CUDA_VISIBLE_DEVICES="", TORCH_DEVICE="cpu")
import torch
UP = upstream_dir(); os.chdir(UP); sys.path.insert(0, str(UP / "src"))
import models_ as models
cfg = w._load_metadata(torch, UP / "weights/classifier/model_config.pt")
clf = models.AttentionClassifier(feature_dims=cfg["feature_dims"], d_model=cfg["d_model"], d_output=cfg["n_labels"], dropout=cfg["dropout"])
clf.load_state_dict(torch.load(UP / "weights/classifier/model.pt", map_location="cpu", weights_only=True)); clf.eval()
L = ("anger","disgust","fear","joy","sadness","surprise")
R = work_dir() / "results3"
F = {k: torch.load(R / v / "features.pt") for k, v in {"B":"01_Baseline_15s","G":"02_Generic_Review_15s","M":"03_MoodCut_15s"}.items()}
def cls(f):
    with torch.no_grad(): p = torch.softmax(clf(f).squeeze().float(), -1).tolist()
    return " ".join(f"{k[:3]}={v*100:5.1f}" for k, v in zip(L, p)) + "  -> " + L[max(range(6), key=lambda i: p[i])]
for k in "BGM": print(k, "nonzero beats rows:", [int(i) for i in (F[k]["beats"][0].abs().sum(-1) > 0).nonzero().flatten()])
print("beats rows idx -> chunk start = idx*1.5s (3s chunks, 1.5s step)")
g = F["G"]["beats"].clone()
for cut in (8, 7, 6, 5):
    f = dict(F["G"]); b = g.clone(); b[:, cut:] = 0; f["beats"] = b
    print(f"G: zero beats rows >= {cut} (start >= {cut*1.5:.1f}s):", cls(f))
for base in "BM":
    for cut in (7, 6):
        f = dict(F[base]); b = F[base]["beats"].clone(); b[:, cut:] = g[:, cut:]; f["beats"] = b
        print(f"{base}: put G's beats rows >= {cut} into {base}:", cls(f))
