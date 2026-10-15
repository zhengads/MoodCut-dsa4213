"""Offline smoke exercises real module boundaries without HTTP or video tools."""
import json
from pathlib import Path
import socket

from moodcut import pipeline


ROOT = Path(__file__).resolve().parents[1]


def test_default_mock_smoke_needs_no_key_network_or_renderer(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Offline smoke reached a network or rendering entry point")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr("moodcut.client.build_opener", forbidden)
    monkeypatch.setattr(pipeline, "render_plan", forbidden)
    scene, assets = [json.loads((ROOT / "tests/fixtures" / name).read_text(encoding="utf-8"))
                     for name in ("scene.json", "assets.json")]
    output = tmp_path / "smoke"
    block = pipeline.run_experiment(scene, assets, out_dir=output, project_root=ROOT, render=False)
    assert block["status"] == "completed"
    assert block["mock"] is True and block["source_kind"] == "synthetic"
    assert block["planning"]["real_http_calls"] == 0
    assert {row["condition"] for row in block["runs"]} == set(pipeline.CONDITIONS)
    assert all(row["render_status"] == "skipped" and row["video_path"] is None for row in block["runs"])
    assert all(row["real_http_calls"] == 0 and row["provider_cost_usd"] == 0 for row in block["runs"])
    assert not list(output.rglob("*.mp4"))
    assert pipeline.read_json(output / "block.json") == block
