import os, sys, glob
from pathlib import Path
from moodcut import vemoclap_worker as w
import sys as _sys
from pathlib import Path as _P
_sys.path.insert(0, str(_P(__file__).resolve().parent))
from _paths import REPO as _REPO, upstream_dir, work_dir
_sys.path.insert(0, str(_REPO / 'src'))
os.environ.update(CUDA_VISIBLE_DEVICES="", TORCH_DEVICE="cpu")
import torch
sys.stdout.reconfigure(encoding="utf-8")
UP = upstream_dir()
os.chdir(UP); sys.path.insert(0, str(UP / "src"))
import models_ as models
cfg = w._load_metadata(torch, UP / "weights/classifier/model_config.pt")
clf = models.AttentionClassifier(feature_dims=cfg["feature_dims"], d_model=cfg["d_model"], d_output=cfg["n_labels"], dropout=cfg["dropout"])
clf.load_state_dict(torch.load(UP / "weights/classifier/model.pt", map_location="cpu", weights_only=True)); clf.eval()
L = ("anger", "disgust", "fear", "joy", "sadness", "surprise")
E = work_dir()
ld = lambda p: torch.load(p, weights_only=True)
def cls(f):
    with torch.no_grad():
        p = torch.softmax(clf(f).squeeze().float(), -1).tolist()
    return p
fmt = lambda p: " ".join(f"{k[:3]}={v*100:5.1f}" for k, v in zip(L, p))
fear_vids = {}
for g, res in (("S09", "results9"), ("S15", "results10")):
    for d in sorted(glob.glob(str(E / res / ("vem_09*" if g == "S09" else "vem_15*")))):
        if os.path.isdir(d): fear_vids[g + "/" + os.path.basename(d)[7:].split("_8s")[0]] = ld(Path(d) / "features.pt")
ref = {"NOTLD-T2(fear 99.6)": ld(E / "results2/T2_tense_notld/features.pt"),
       "NOTLD-T1(fear 78.5)": ld(E / "results2/T1_tense_notld/features.pt"),
       "S07-moodcut(anger 95.7)": ld(E / "results9/vem_07__03_MoodCut_8s_Chinese/features.pt")}
# neutral reference = mean of all project videos' features per stream
allf = [ld(p) for p in glob.glob(str(E / "results*/**/features.pt"), recursive=True) if "results2/" not in p.replace("\\", "/")]
mean = {s: torch.stack([f[s] for f in allf]).mean(0) for s in cfg["features"]}
ref["MEAN of all %d project videos" % len(allf)] = mean
print("streams:", list(cfg["features"]))
print("\n## A. 把一个视频的某一路特征换成参照视频的同一路特征（行=被改的恐惧视频，列=换入的流）")
for name, F in fear_vids.items():
    print("\n#", name, "| own:", fmt(cls(F)))
    for rn, R in ref.items():
        print("  from", rn)
        for s in cfg["features"]:
            f = dict(F); f[s] = R[s]
            p = cls(f); print(f"    swap {s:14}", fmt(p))
print("\n## B. 反过来：把恐惧视频的某一路特征放进 NOTLD-T2（fear 99.6）里，看哪一路会把 fear 拉下去")
T2 = ref["NOTLD-T2(fear 99.6)"]
print("T2 own:", fmt(cls(T2)))
for name, F in fear_vids.items():
    print("#", name)
    for s in cfg["features"]:
        f = dict(T2); f[s] = F[s]; print(f"    T2 with {s:14}", fmt(cls(f)))
print("\n## C. 各路特征的统计（均值/标准差；NOTLD-T2 与 S09/S15 对照）")
for s in cfg["features"]:
    row = [f"{n[:12]}: {F[s].mean():.3f}/{F[s].std():.3f}" for n, F in [("T2", T2)] + list(fear_vids.items())[::3]]
    print(f"  {s:14}", " | ".join(row))
