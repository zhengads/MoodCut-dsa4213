"""Score transcript text with GoEmotions (28 labels, multi-label sigmoid). Groups were fixed before running."""
import argparse, json, os
from pathlib import Path
import sys as _sys
from pathlib import Path as _P
_sys.path.insert(0, str(_P(__file__).resolve().parent))
from _paths import REPO as _REPO, upstream_dir, work_dir
_sys.path.insert(0, str(_REPO / 'src'))

ap = argparse.ArgumentParser()
ap.add_argument("--model", type=Path, required=True)
ap.add_argument("--transcripts", type=Path, required=True)
ap.add_argument("--out", type=Path, required=True)
a = ap.parse_args()
os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", CUDA_VISIBLE_DEVICES="")
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

GROUPS = {  # pre-specified; group score = max probability among its labels
    "hostile": ("anger", "annoyance", "disapproval", "disgust"),
    "tense": ("fear", "nervousness"),
    "affectionate": ("love", "caring", "admiration", "gratitude", "joy"),
}
tok = AutoTokenizer.from_pretrained(str(a.model))
model = AutoModelForSequenceClassification.from_pretrained(str(a.model)).eval()
id2label = model.config.id2label
items = json.loads(a.transcripts.read_text(encoding="utf-8"))
res = []
for it in items:
    text = it["asr_text"].strip()
    x = tok(text, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        p = torch.sigmoid(model(**x).logits).squeeze(0).tolist()
    probs = {id2label[i]: round(float(v), 4) for i, v in enumerate(p)}
    top = sorted(probs.items(), key=lambda kv: -kv[1])[:4]
    groups = {g: round(max(probs[l] for l in ls), 4) for g, ls in GROUPS.items()}
    res.append({**it, "top4": top, "groups": groups, "probs": probs})
    print(it["id"], groups, top[:2], flush=True)
a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
