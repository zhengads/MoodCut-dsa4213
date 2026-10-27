"""Headless CPU integration of the pinned VEMOCLAP feature/classifier APIs.

Inference sequence adapted from video_emotion_classifier.py at
https://github.com/serkansulun/video-emotion/tree/312f80204f001d611564a2c8405999080829cae3
Copyright (c) 2024 INESC TEC; original author Serkan Sulun.
Modifications (c) 2026 FANXUYANG: offline CPU worker, precise JSON probabilities,
no caption/visualization, explicit empty-feature handling and Windows workers=0.
SPDX-License-Identifier: GPL-3.0-or-later

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later version.
This program is distributed WITHOUT ANY WARRANTY; without even the implied
warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See
https://www.gnu.org/licenses/gpl-3.0.html and docs/licenses/vemoclap-LICENSE.md.
"""
import argparse
import functools
import gc
import importlib.metadata
import json
import os
from pathlib import Path
import pickle
import sys
import types


class _PortableUnpickler(pickle.Unpickler):
    """Read upstream Linux path metadata with the current platform's Path."""

    def find_class(self, module, name):
        if module == "pathlib" and name in ("PosixPath", "WindowsPath"):
            return Path
        return super().find_class(module, name)


def _load_metadata(torch, path):
    portable_pickle = types.SimpleNamespace(
        __name__="pickle", Unpickler=_PortableUnpickler,
        load=pickle.load, loads=pickle.loads)
    return torch.load(path, map_location="cpu", weights_only=False, pickle_module=portable_pickle)


def _deny_network(event, args):
    if event in ("socket.connect", "socket.getaddrinfo", "socket.sendto"):
        raise RuntimeError("VEMOCLAP worker is offline; prepare missing model caches separately")


def predict(upstream, video):
    # Set policy before any optional dependency is imported. No GPU option.
    os.environ.update(CUDA_VISIBLE_DEVICES="", TORCH_DEVICE="cpu", HF_HUB_OFFLINE="1",
                      TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1",
                      MPLBACKEND="Agg")
    sys.addaudithook(_deny_network)
    import torch
    import clip
    cache = Path(os.environ["MOODCUT_VEMOCLAP_CACHE"])
    # OpenAI CLIP otherwise ignores TORCH_HOME and downloads to the user's home.
    clip.load = functools.partial(clip.load, download_root=str(cache / "clip"))
    # Third-party constructors use this method and their own module-level DEVICE.
    torch.cuda.is_available = lambda: False
    torch.set_num_threads(2)
    torch.manual_seed(0)
    os.chdir(upstream)
    sys.path.insert(0, str(upstream / "src"))
    import models_ as models
    import utils

    config = _load_metadata(torch, upstream / "weights/classifier/model_config.pt")
    stats = _load_metadata(torch, upstream / "stats.pt")
    classifier = models.AttentionClassifier(feature_dims=config["feature_dims"],
                                           d_model=config["d_model"],
                                           d_output=config["n_labels"], dropout=config["dropout"])
    classifier.load_state_dict(torch.load(upstream / "weights/classifier/model.pt",
                                         map_location="cpu", weights_only=True))
    classifier.to("cpu").eval()
    constructors = {"clip": models.CLIPRunner, "beats": models.BEATSRunner,
                    "asr_sentiment": models.ASRSentiment, "ocr_sentiment": models.OCRPipeline,
                    "face_emotion": models.FaceExtractAndClassify}
    names = config["features"]
    if not names or len(set(names)) != len(names) or set(names) - set(constructors):
        raise ValueError("Unsupported feature configuration")
    duration = utils.get_video_duration(str(video))
    frames, audio, _, sr = utils.extract_frames_and_audio(
        str(video), output_fps=config["feature_lengths"]["clip"] / duration, size=360)
    if len(frames) == 0 or audio is None or sr is None or audio.shape[-1] / sr <= 3:
        raise ValueError("Decoded video needs frames and more than 3 seconds of audio")
    features, missing = {}, []
    with torch.no_grad():
        for name in names:
            print("Extracting " + name, flush=True)
            extractor = constructors[name]()
            extractor.to_device("cpu")
            if hasattr(extractor, "eval"):
                extractor.eval()
            options = {"num_workers": 0} if name == "beats" else {}
            extracted = extractor.process_video(
                input_tensor=audio if name in ("beats", "asr_sentiment") else frames,
                n_frames=config["n_frames"], sr=sr, **options)["features"]
            target = config["feature_lengths"][name]
            width = config["feature_dims"][name]
            # Preserve native missing-modality zeros, but disclose their use.
            if isinstance(extracted, list) and not extracted:
                missing.append(name)
                tensor = torch.zeros((target, width))
            else:
                tensor = torch.as_tensor(extracted).detach().cpu()
                if tensor.ndim != 2 or tensor.shape[1] != width or tensor.shape[0] == 0:
                    raise ValueError("Unexpected feature shape: " + name)
                if config["normalize_data"]:
                    tensor = utils.normalize(tensor, stats[name]["min"], stats[name]["max"])
                if tensor.shape[0] > target:
                    tensor = tensor[utils.equidistant_indices(tensor.shape[0], target), :]
                elif tensor.shape[0] < target:
                    tensor = torch.nn.functional.pad(tensor, (0, 0, 0, target - tensor.shape[0]))
            if not torch.isfinite(tensor).all():
                raise ValueError("Nonfinite feature values: " + name)
            features[name] = tensor.unsqueeze(0)
            del extractor
            gc.collect()
        logits = classifier(features).squeeze()
        if logits.shape != (6,) or not torch.isfinite(logits).all():
            raise ValueError("Expected six finite classifier logits")
        values = torch.softmax(logits.float(), dim=-1).cpu().tolist()
    labels = ("anger", "disgust", "fear", "joy", "sadness", "surprise")
    packages = {}
    for package in ("torch", "torchvision", "torchaudio", "transformers", "surya-ocr", "numpy"):
        packages[package] = importlib.metadata.version(package)
    return {"probabilities": dict(zip(labels, values)), "missing_features": missing,
            "packages": packages}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    upstream, video, output = args.upstream.resolve(), args.video.resolve(), args.output.resolve()
    # Reserve output before work; parent never treats a partial/empty result as success.
    with output.open("x", encoding="utf-8") as handle:
        result = predict(upstream, video)
        json.dump(result, handle, ensure_ascii=False, indent=2, allow_nan=False)


if __name__ == "__main__":
    main()
