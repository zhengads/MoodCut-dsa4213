"""Diagnostic: save VEMOCLAP per-modality features, then ablate each modality (zero it) and re-classify.
Reuses the project worker's loading logic; read-only on the repo, outputs go to --out."""
import argparse, functools, gc, itertools, json, os, sys, time
from pathlib import Path
import sys as _sys
from pathlib import Path as _P
_sys.path.insert(0, str(_P(__file__).resolve().parent))
from _paths import REPO as _REPO, upstream_dir, work_dir
_sys.path.insert(0, str(_REPO / 'src'))

from moodcut import vemoclap_worker as w  # noqa: E402

LABELS = ("anger", "disgust", "fear", "joy", "sadness", "surprise")


def run(upstream, video, out):
    os.environ.update(CUDA_VISIBLE_DEVICES="", TORCH_DEVICE="cpu", HF_HUB_OFFLINE="1",
                      TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1", MPLBACKEND="Agg")
    import torch, clip
    cache = Path(os.environ["MOODCUT_VEMOCLAP_CACHE"])
    clip.load = functools.partial(clip.load, download_root=str(cache / "clip"))
    torch.cuda.is_available = lambda: False
    torch.set_num_threads(2)
    torch.manual_seed(0)
    os.chdir(upstream)
    sys.path.insert(0, str(upstream / "src"))
    import models_ as models
    import utils
    config = w._load_metadata(torch, upstream / "weights/classifier/model_config.pt")
    stats = w._load_metadata(torch, upstream / "stats.pt")
    clf = models.AttentionClassifier(feature_dims=config["feature_dims"], d_model=config["d_model"],
                                     d_output=config["n_labels"], dropout=config["dropout"])
    clf.load_state_dict(torch.load(upstream / "weights/classifier/model.pt", map_location="cpu", weights_only=True))
    clf.to("cpu").eval()
    ctor = {"clip": models.CLIPRunner, "beats": models.BEATSRunner, "asr_sentiment": models.ASRSentiment,
            "ocr_sentiment": models.OCRPipeline, "face_emotion": models.FaceExtractAndClassify}
    names = config["features"]
    duration = utils.get_video_duration(str(video))
    frames, audio, _, sr = utils.extract_frames_and_audio(
        str(video), output_fps=config["feature_lengths"]["clip"] / duration, size=360)
    feats, missing = {}, []
    with torch.no_grad():
        for n in names:
            ex = ctor[n](); ex.to_device("cpu")
            if hasattr(ex, "eval"): ex.eval()
            opt = {"num_workers": 0} if n == "beats" else {}
            got = ex.process_video(input_tensor=audio if n in ("beats", "asr_sentiment") else frames,
                                   n_frames=config["n_frames"], sr=sr, **opt)["features"]
            tl, wd = config["feature_lengths"][n], config["feature_dims"][n]
            if isinstance(got, list) and not got:
                missing.append(n); t = torch.zeros((tl, wd))
            else:
                t = torch.as_tensor(got).detach().cpu()
                if config["normalize_data"]:
                    t = utils.normalize(t, stats[n]["min"], stats[n]["max"])
                if t.shape[0] > tl: t = t[utils.equidistant_indices(t.shape[0], tl), :]
                elif t.shape[0] < tl: t = torch.nn.functional.pad(t, (0, 0, 0, tl - t.shape[0]))
            feats[n] = t.unsqueeze(0)
            del ex; gc.collect()
        torch.save(feats, out / "features.pt")

        def classify(f):
            return dict(zip(LABELS, torch.softmax(clf(f).squeeze().float(), -1).tolist()))

        res = {"names": names, "missing": missing, "full": classify(feats), "drop_one": {}, "keep_one": {}}
        for n in names:
            f = {k: (torch.zeros_like(v) if k == n else v) for k, v in feats.items()}
            res["drop_one"][n] = classify(f)
            f = {k: (v if k == n else torch.zeros_like(v)) for k, v in feats.items()}
            res["keep_one"][n] = classify(f)
        res["all_zero"] = classify({k: torch.zeros_like(v) for k, v in feats.items()})
    (out / "ablation.json").write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    t = time.monotonic()
    run(upstream_dir(), a.video.resolve(), a.out.resolve())
    print("DONE", a.video.name, round(time.monotonic() - t), "s", flush=True)
