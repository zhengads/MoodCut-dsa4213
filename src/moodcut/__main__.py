
"""Command-line interface for the MoodCut project."""

import argparse


def build_parser() -> argparse.ArgumentParser:
    """Create the main MoodCut argument parser."""

    parser = argparse.ArgumentParser(
        prog="moodcut",
        description=(
            "MoodCut: Emotion-aware storyboard review "
            "and constrained revision."
        ),
    )

    parser.add_argument(
        "--version",
        action="version",
        version="MoodCut 0.0.0",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        title="commands",
        description="Available MoodCut operations",
    )

    subparsers.add_parser(
        "plan",
        help="Generate an initial storyboard plan.",
    )

    subparsers.add_parser(
        "review",
        help="Review and revise a storyboard plan.",
    )

    subparsers.add_parser(
        "render",
        help="Render a storyboard into an animatic.",
    )

    subparsers.add_parser(
        "smoke",
        help="Run offline integration checks.",
    )

    subparsers.add_parser(
        "evaluate",
        help="Prepare and evaluate experimental results.",
    )

    return parser


def main() -> int:
    """Run the MoodCut command-line interface."""

    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    parser.error(
        f"The '{args.command}' command is not implemented yet."
    )

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
