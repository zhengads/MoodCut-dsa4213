import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_s06_real.py"

spec = importlib.util.spec_from_file_location("s06_runner", SCRIPT)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def test_runner_has_three_conditions():
    assert runner.CONDITIONS == (
        "baseline", "generic_review", "moodcut"
    )


def test_missing_input_rejected(tmp_path):
    with pytest.raises(FileNotFoundError):
        runner.check_inputs(tmp_path)


def test_existing_text_output_blocks_paid_retry(tmp_path):
    output = tmp_path / "real-text-01"
    output.mkdir()

    with pytest.raises(FileExistsError):
        runner.run_text(tmp_path, runner.Decimal("0.10"))


def test_inspection_missing_execution_rejected(tmp_path):
    with pytest.raises(FileNotFoundError):
        runner.inspect(tmp_path)


def test_text_requires_explicit_paid_authorization(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        [
            str(SCRIPT), "text",
            "--input", str(tmp_path),
        ],
    )

    with pytest.raises(PermissionError):
        runner.main()


def test_invalid_budget_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        [
            str(SCRIPT), "check",
            "--input", str(tmp_path),
            "--text-budget", "0.20",
        ],
    )

    with pytest.raises(ValueError):
        runner.main()


def test_no_network_for_local_checks(tmp_path):
    with patch(
        "socket.socket.connect",
        side_effect=AssertionError("Network forbidden"),
    ):
        with pytest.raises(FileNotFoundError):
            runner.inspect(tmp_path)
