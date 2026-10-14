

"""Unit tests for the MoodCut command-line interface."""

import subprocess
import sys

import pytest


def run_cli(*arguments):
    """Run MoodCut CLI using the current Python interpreter."""
    return subprocess.run(
        [sys.executable, "-m", "moodcut", *arguments],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )


def test_help_command():
    """The main help command must exit successfully."""
    result = run_cli("--help")

    assert result.returncode == 0
    assert "MoodCut" in result.stdout
    assert "plan" in result.stdout
    assert "review" in result.stdout
    assert "render" in result.stdout
    assert "smoke" in result.stdout
    assert "evaluate" in result.stdout


def test_version_command():
    """The version command must display the project version."""
    result = run_cli("--version")

    assert result.returncode == 0
    assert "MoodCut 0.0.0" in result.stdout


def test_no_arguments_shows_help():
    """Running without arguments must display help."""
    result = run_cli()

    assert result.returncode == 0
    assert "usage:" in result.stdout


@pytest.mark.parametrize(
    "command",
    ["plan", "review", "render", "smoke", "evaluate"],
)
def test_unimplemented_commands_fail(command):
    """Unimplemented commands must not report success."""
    result = run_cli(command)

    assert result.returncode != 0
    assert "not implemented yet" in result.stderr


def test_unknown_command_fails():
    """An unknown command must be rejected."""
    result = run_cli("unknown")

    assert result.returncode != 0
    assert "invalid choice" in result.stderr


def test_subcommand_help():
    """Subcommands must provide their own help messages."""
    result = run_cli("plan", "--help")

    assert result.returncode == 0
    assert "usage:" in result.stdout
    assert "plan" in result.stdout
