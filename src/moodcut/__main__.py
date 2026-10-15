
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

    check = subparsers.add_parser(
        "check-client",
        help="Validate local OpenRouter configuration without sending a request.",
    )
    check.add_argument("--config", default="configs/model.json")
    check.add_argument("--max-cost-usd", type=float, required=True)

    return parser


def main() -> int:
    """Run the MoodCut command-line interface."""

    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "check-client":
        from .client import OpenRouterClient

        try:
            client = OpenRouterClient.from_env(args.config, max_cost_usd=args.max_cost_usd)
        except (ValueError, OSError) as exc:
            # Do not echo configuration values or environment secrets.
            parser.error(f"Invalid OpenRouter configuration ({type(exc).__name__}); check key, model, prices and budget")
        print(f"OpenRouter configuration valid for {client.model}; no network request sent.")
        return 0

    parser.error(
        f"The '{args.command}' command is not implemented yet."
    )

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
