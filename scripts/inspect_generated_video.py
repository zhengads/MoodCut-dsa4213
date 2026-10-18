"""Offline inspection packages for existing local video receipts; never submit jobs."""
import argparse
from pathlib import Path
import subprocess
import sys

from moodcut.video_generation import inspect_generated_video


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', default='.')
    parser.add_argument('--preparation', required=True)
    parser.add_argument('--evidence', required=True)
    parser.add_argument('--pricing-config', default='configs/video.json')
    parser.add_argument('--output', required=True)
    parser.add_argument('--media-origin', required=True, choices=('synthetic', 'provided_local'))
    args = parser.parse_args(argv)
    root = Path(args.project_root).resolve()
    resolve = lambda value: Path(value) if Path(value).is_absolute() else root / value
    try:
        result = inspect_generated_video(resolve(args.preparation), evidence=resolve(args.evidence),
            out_dir=resolve(args.output), pricing_config=resolve(args.pricing_config),
            media_origin=args.media_origin, project_root=root)
    except (ValueError, TypeError, KeyError, OSError, subprocess.SubprocessError) as exc:
        print(f'Inspection failed: {type(exc).__name__}: {exc}', file=sys.stderr)
        return 1
    print(f"{result['status']}: {resolve(args.output) / 'index.html'} (offline; no new API calls)")
    return 0 if result['status'] == 'ready_requires_manual_inspection' else 1


if __name__ == '__main__':
    raise SystemExit(main())
