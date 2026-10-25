"""Synthetic artifacts test reporting, never model quality or real video decoding."""

import importlib.util
from html import unescape
from pathlib import Path

import pytest

from moodcut.client import FakeClient
from moodcut.pipeline import json_hash, read_json, run_experiment


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("compare_demo", ROOT / "scripts/compare_demo.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


def replace_json(path, data):
    import json
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


@pytest.fixture
def block(tmp_path):
    scene, assets = [read_json(ROOT / "tests/fixtures" / name)
                     for name in ("scene.json", "assets.json")]
    folder = tmp_path / "block"
    result = run_experiment(scene, assets, out_dir=folder, project_root=ROOT, render=False)
    return folder, result


def test_report_uses_actual_differences_and_escapes_model_text(block):
    folder, data = block
    review_file = folder / "moodcut/review.json"
    review = read_json(review_file)
    review["report"]["issues"][0]["evidence"] = '<script>alert("untrusted")</script>'
    replace_json(review_file, review)
    for row in data["runs"]:
        video = folder / row["condition"] / "clip #&.mp4"
        video.write_bytes(b"unit-test-path-not-decoded-video")
        row.update(render_status="rendered", video_path=str(video))
    replace_json(folder / "block.json", data)
    output = tool.write_comparison(folder, folder / "comparison.html")
    text = output.read_text(encoding="utf-8")
    assert '<script>' not in text and '&lt;script&gt;' in text
    assert 'clip%20%23%26.mp4' in text
    assert text.count('<video controls') == 3
    _, items = tool.collect_comparison(folder)
    assert items[0]["changes"] == []
    assert [c["field"] for c in items[2]["changes"]] == ["narration"]
    assert items[2]["changes"][0]["before"] != items[2]["changes"][0]["after"]
    displayed_text = unescape(text)
    assert '"real_http_calls": 0' in displayed_text and '"mock": true' in displayed_text


def test_unchanged_final_is_reported_as_unchanged(block):
    folder, data = block
    initial = read_json(folder / "moodcut/initial.json")
    replace_json(folder / "moodcut/final.json", initial)
    data["runs"][2]["final_plan_sha256"] = json_hash(initial)
    data["runs"][2]["review_status"] = "unchanged"
    replace_json(folder / "block.json", data)
    output = tool.write_comparison(folder, folder / "comparison.html")
    assert "no fields changed" in output.read_text(encoding="utf-8")


def test_failed_planning_is_not_disguised_as_zero_changes(tmp_path):
    folder = tmp_path / "failed"
    scene, assets = [read_json(ROOT / "tests/fixtures" / name)
                     for name in ("scene.json", "assets.json")]
    data = run_experiment(scene, assets, FakeClient([{"invalid": "planning"}]),
                          out_dir=folder, project_root=ROOT, render=False)
    assert data["status"] == "failed"
    _, items = tool.collect_comparison(folder)
    assert all(item["changes"] is None for item in items)
    output = tool.write_comparison(folder, folder / "comparison.html")
    text = output.read_text(encoding="utf-8")
    assert "No final storyboard is available for comparison" in text and "no fields changed" not in text
    assert "planning_errors" in text


@pytest.mark.parametrize("kind", ["mismatched_block", "tampered_initial", "tampered_final"])
def test_mismatched_or_tampered_inputs_rejected_before_writing(block, kind):
    folder, data = block
    if kind == "mismatched_block":
        data["runs"][2]["initial_plan_sha256"] = "b" * 64
        replace_json(folder / "block.json", data)
    else:
        target = folder / "moodcut" / ("initial.json" if kind == "tampered_initial" else "final.json")
        plan = read_json(target)
        plan["shots"][0]["narration"] += " changed after run"
        replace_json(target, plan)
    output = folder / "comparison.html"
    with pytest.raises(ValueError, match="hash"):
        tool.write_comparison(folder, output)
    assert not output.exists()


def test_output_is_never_overwritten_and_external_video_rejected(block, tmp_path):
    folder, data = block
    output = folder / "comparison.html"
    output.write_text("existing", encoding="utf-8")
    assert tool.main(["--run", str(folder), "--output", str(output)]) == 1
    assert output.read_text(encoding="utf-8") == "existing"
    outside = tmp_path / "external.mp4"
    outside.write_bytes(b"not-a-real-video")
    data["runs"][2].update(render_status="rendered", video_path=str(outside))
    replace_json(folder / "block.json", data)
    with pytest.raises(ValueError, match="inside"):
        tool.write_comparison(folder, folder / "new.html")


def test_plan_diff_includes_shot_addition_removal_and_order():
    before = {"tone": "suspicious", "shots": [{"shot_id": "s1"}, {"shot_id": "s2"}]}
    after = {"tone": "hostile", "shots": [{"shot_id": "s2"}, {"shot_id": "s3"}]}
    changes = tool.plan_changes(before, after)
    assert {c["field"] for c in changes} == {"tone", "shot_order", "shot"}
    assert {c["shot_id"] for c in changes if c["field"] == "shot"} == {"s1", "s3"}
