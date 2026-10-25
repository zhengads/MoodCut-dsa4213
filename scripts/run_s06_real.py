"""S06 real text experiment and video preparation helper.

No automatic retries. Never overwrites existing run directories.
Video generation remains delegated to the official MoodCut CLI.
"""
import argparse
import json
import os
from decimal import Decimal
from pathlib import Path

from moodcut import validation
from moodcut.client import RoleRoutedClient
from moodcut.pipeline import run_experiment
from moodcut.video_generation import get_video_template_sha256

ROOT = Path(__file__).resolve().parents[1]
CONDITIONS = ("baseline", "generic_review", "moodcut")
MODEL_CONFIG = ROOT / "configs/agent_pilot_models.json"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def check_inputs(folder):
    scene = read(folder / "scene.json")
    manifest = read(folder / "assets.json")
    settings = read(folder / "generation_settings.json")

    errors = validation.validate_scene(
        scene, manifest,
        project_root=ROOT,
        output_mode="generated",
    )
    if errors:
        raise ValueError("; ".join(errors))

    if settings.get("model") != "heygen/heygen-video-1":
        raise ValueError("Expected HeyGen Video 1")

    if settings.get("resolution") != "768p":
        raise ValueError("Expected 768p")

    if scene.get("max_shots") != 1:
        raise ValueError("Expected single-shot S06")

    if scene.get("min_duration_s") != 5 or scene.get("max_duration_s") != 5:
        raise ValueError("Expected five-second S06")

    return scene, manifest, settings


def run_text(folder, budget):
    output = folder / "real-text-01"

    if output.exists():
        raise FileExistsError(
            "Text output already exists. Refusing to resubmit."
        )

    if not os.environ.get("OPENROUTER_API_KEY"):
        raise RuntimeError("OPENROUTER_API_KEY missing")

    scene, manifest, settings = check_inputs(folder)

    client = RoleRoutedClient.from_env(
        str(MODEL_CONFIG),
        allow_paid=True,
        max_cost_usd=float(budget),
    )

    print("Starting real S06 text experiment", flush=True)

    block = run_experiment(
        scene,
        manifest,
        client,
        out_dir=output,
        project_root=ROOT,
        render=False,
        source_kind="development",
        output_mode="generated",
        generation_settings=settings,
        template_sha256=get_video_template_sha256(),
        review_protocol="actor_self_review_v3",
    )

    print("Block status:", block.get("status"))

    for row in block.get("runs", []):
        print(
            row.get("condition"),
            row.get("run_status"),
            row.get("review_status"),
        )

    if block.get("status") != "prepared":
        raise RuntimeError(
            "Text experiment not prepared. Inspect saved records; do not retry."
        )

    print("Text prepared:", output / "block.json")


def inspect(folder):
    execution = folder / "video-execution-live"
    path = execution / "execution.json"

    if not path.is_file():
        raise FileNotFoundError("Execution record not found")

    data = read(path)

    print("Execution status:", data.get("status"))
    print("Video POSTs:", data.get("generation_posts_this_invocation"))
    print("Errors:", data.get("errors"))

    costs = []
    hashes = []

    import hashlib

    for condition in CONDITIONS:
        job = execution / condition / "shot-000"
        receipt = read(job / "receipt.json")
        video = job / "generated.mp4"

        if not video.is_file():
            raise FileNotFoundError(video)

        if receipt.get("status") != "downloaded":
            raise RuntimeError(f"{condition}: not downloaded")

        cost = receipt.get("provider_cost_usd")
        if cost is None:
            raise RuntimeError(f"{condition}: unknown provider cost")

        costs.append(Decimal(str(cost)))
        hashes.append(hashlib.sha256(video.read_bytes()).hexdigest())

        print(condition, "cost:", cost, "sha256:", hashes[-1])

    print("Video cost:", sum(costs))
    print("Distinct MP4 files:", len(set(hashes)) == 3)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action", choices=("check", "text", "inspect")
    )
    parser.add_argument("--input", required=True)
    parser.add_argument("--text-budget", default="0.10")
    parser.add_argument("--allow-paid", action="store_true")
    args = parser.parse_args()

    folder = Path(args.input).resolve()
    if not folder.is_dir():
        raise FileNotFoundError(folder)

    budget = Decimal(args.text_budget)
    if not budget.is_finite() or not Decimal("0") < budget <= Decimal("0.10"):
        raise ValueError("Text budget must be positive and at most $0.10")

    if args.action == "check":
        scene, _, settings = check_inputs(folder)
        print("PASS:", scene["scene_id"])
        print("Video model:", settings["model"])
        print("No API requests sent")

    elif args.action == "text":
        if not args.allow_paid:
            raise PermissionError("Explicit --allow-paid required")
        run_text(folder, budget)

    else:
        inspect(folder)


if __name__ == "__main__":
    main()
