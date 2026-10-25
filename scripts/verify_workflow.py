"""One-command offline workflow verification; no provider calls or human scores.

Name: FANXUYANG
Date: 2026-10-24
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="New verification directory.")
    args = parser.parse_args()
    output = Path(args.output).resolve()
    if output.exists():
        parser.error("Output exists; choose a new directory.")
    missing = [name for name in ("ffmpeg", "ffprobe") if not shutil.which(name)]
    if missing:
        parser.error("Add to PATH: " + ", ".join(missing))
    output.mkdir(parents=True)
    steps = []

    def run(name, arguments):
        started = time.monotonic()
        with (output / (name + ".log")).open("w", encoding="utf-8") as log:
            result = subprocess.run([sys.executable, *arguments], cwd=ROOT,
                                    stdout=log, stderr=subprocess.STDOUT, text=True)
        steps.append(dict(name=name, exit_code=result.returncode,
                          seconds=round(time.monotonic() - started, 2),
                          log=name + ".log"))
        print(name + ": " + ("PASS" if result.returncode == 0 else "FAIL"), flush=True)
        return result.returncode == 0

    cli = ["-m", "moodcut"]
    block = output / "animatic" / "block.json"
    prepared = run("three-condition-run", [*cli, "run", "--mock",
                   "--scene", "tests/fixtures/scene.json", "--assets", "tests/fixtures/assets.json",
                   "--source-kind", "synthetic", "--output", str(block.parent)])
    if prepared:
        run("anonymous-export", [*cli, "evaluate", "--records", str(block),
            "--blind-output", str(output / "blind"), "--seed", "17"])
        run("coverage-without-ratings", [*cli, "evaluate", "--records", str(block),
            "--output", str(output / "coverage.json")])
    run("assignment-dry-run", [*cli, "evaluate", "--config", "configs/experiment.json",
        "--dry-run", "--output", str(output / "assignments.json")])

    # Reuse the existing actual P1/P2/P3/P4 integration fixtures and P5 assertions.
    # Their moving/audio clips, receipts and arithmetic votes are synthetic.
    tests = ["test_offline_qualification_and_cli_preserve_originals",
             "test_generated_blind_export_and_rating_cli_preserve_sources",
             "test_p5_actual_unknown_cost_records_remain_unknown",
             "test_p5_actual_failed_run_is_rejected_but_kept_in_summary",
             "test_offline_qualification_rejects_changed_evidence"]
    run("generated-integration", ["-m", "pytest", "-q", "--tb=short", "-p", "no:cacheprovider",
        "--basetemp", str(output / "generated-software-cases"),
        "--junitxml", str(output / "generated-tests.xml"),
        *["tests/test_evaluation_paired.py::" + test for test in tests]])
    passed = all(step["exit_code"] == 0 for step in steps)
    summary = dict(kind="offline_workflow_verification", status="passed" if passed else "failed",
                   data_source="synthetic_software_fixtures", new_paid_calls=0,
                   human_ratings=0, real_model_quality_verified=False, steps=steps)
    coverage_path = output / "coverage.json"
    if coverage_path.exists():
        coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
        summary["animatic_coverage"] = coverage["overall"]["coverage"]
        summary["animatic_means"] = coverage["overall"]["equal_clip_means"]
    junit = output / "generated-tests.xml"
    if junit.exists():
        summary["generated_test_suites"] = [suite.attrib for suite in ET.parse(junit).getroot()]
    (output / "verification.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "README.md").write_text(
        "# Offline workflow verification\n\nStatus: " + summary["status"] + "\n\n"
        "All videos, receipts and test votes here are synthetic software fixtures. "
        "No provider calls or real human scores. This does not certify historical real runs.\n\n"
        "- animatic/: three-condition CLI output\n"
        "- blind/public/: anonymous animatic videos and blank rating template\n"
        "- blind/PRIVATE/: private mapping; do not distribute to raters\n"
        "- coverage.json: statistics with no ratings\n"
        "- generated-software-cases/: existing generated-mode integration artifacts\n"
        "- generated-tests.xml and *.log: test and command evidence\n"
        "- verification.json: combined results\n", encoding="utf-8")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
