"""Hand-written transport fixtures, never real generation requests."""
import io
import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock
from urllib.error import URLError
from urllib.request import Request

import pytest

from moodcut.client import BudgetError, OpenRouterError
from moodcut.video_client import OpenRouterVideoClient, check_video_model, estimate_video_cost, _ContentRedirect


def response(value):
    return io.BytesIO(json.dumps(value).encode())


def config():
    return {"model": "alibaba/wan-2.7", "resolution": "720p", "aspect_ratio": "16:9",
            "price_per_second_usd": "0.10", "generate_audio": True}


def request():
    return {"model": "alibaba/wan-2.7", "prompt": "An actual moving scene.", "duration": 6,
            "resolution": "720p", "aspect_ratio": "16:9", "generate_audio": True, "seed": 42,
            "input_references": [{"type": "image_url", "image_url": {"url": "https://example.com/a.png"}}]}


def client(opener, **kwargs):
    return OpenRouterVideoClient(config(), api_key="never-log-this-key", allow_paid=True,
                                 max_cost_usd="2", opener=opener, **kwargs)


def test_no_authorization_no_http(tmp_path):
    opener = Mock()
    c = OpenRouterVideoClient(config(), api_key="key", allow_paid=False, max_cost_usd="2", opener=opener)
    with pytest.raises(BudgetError):
        c.generate(request(), out_dir=str(tmp_path / "job"))
    opener.assert_not_called()


def test_budget_insufficient_no_http(tmp_path):
    opener = Mock()
    c = OpenRouterVideoClient(config(), api_key="key", allow_paid=True, max_cost_usd="0.1", opener=opener)
    with pytest.raises(BudgetError):
        c.generate(request(), out_dir=str(tmp_path / "job"))
    opener.assert_not_called()


def test_success_persists_id_and_cost_then_downloads(tmp_path):
    opener = Mock(side_effect=[response({"id": "job-123", "status": "pending"}),
                              response({"id": "job-123", "status": "completed", "usage": {"cost": .6},
                                        "urls": ["https://secret.invalid/signed"]}), io.BytesIO(b"video-bytes")])
    c = client(opener)
    receipt = c.generate(request(), out_dir=str(tmp_path / "job"))
    assert receipt["status"] == "downloaded"
    assert receipt["estimated_cost_usd"] == "0.60"
    assert receipt["provider_cost_usd"] == "0.6"
    assert c.spent_usd == "0.6"
    assert c.post_attempts == 1
    assert [call.args[0].get_method() for call in opener.call_args_list] == ["POST", "GET", "GET"]
    stored = (tmp_path / "job/receipt.json").read_text()
    assert "never-log" not in stored and "signed" not in stored
    assert Path(receipt["video_path"]).read_bytes() == b"video-bytes"


def test_unknown_submit_not_retried_and_blocks_later_jobs(tmp_path):
    opener = Mock(side_effect=URLError("never-log-this-key"))
    c = client(opener)
    with pytest.raises(OpenRouterError):
        c.generate(request(), out_dir=str(tmp_path / "first"))
    with pytest.raises(BudgetError):
        c.generate(request(), out_dir=str(tmp_path / "second"))
    assert opener.call_count == 1
    stored = (tmp_path / "first/receipt.json").read_text()
    assert "never-log" not in stored
    assert json.loads(stored)["provider_cost_usd"] is None


def test_poll_timeout_preserves_job_id_without_resubmission(tmp_path, monkeypatch):
    opener = Mock(side_effect=[response({"id": "job-123", "status": "pending"})])
    monkeypatch.setattr("moodcut.video_client.monotonic", Mock(side_effect=[0, 2]))
    c = client(opener, job_timeout_s=1)
    with pytest.raises(OpenRouterError, match="timed out"):
        c.generate(request(), out_dir=str(tmp_path / "job"))
    saved = json.loads((tmp_path / "job/receipt.json").read_text())
    assert saved["status"] == "polling_timeout"
    assert saved["job_id"] == "job-123"
    assert c.spent_usd is None and c.post_attempts == 1
    assert opener.call_count == 1


def test_malformed_submit_job_id_stays_unknown(tmp_path):
    opener = Mock(return_value=response({"id": "../wrong", "status": "pending"}))
    c = client(opener)
    with pytest.raises(OpenRouterError, match="job ID"):
        c.generate(request(), out_dir=str(tmp_path / "job"))
    saved = json.loads((tmp_path / "job/receipt.json").read_text())
    assert saved["status"] == "submission_unknown"
    assert saved["job_id"] is None
    assert opener.call_count == 1


def test_unknown_cost_downloads_but_blocks_following_job(tmp_path):
    opener = Mock(side_effect=[response({"id": "job-123", "status": "completed"}), io.BytesIO(b"video")])
    c = client(opener)
    receipt = c.generate(request(), out_dir=str(tmp_path / "first"))
    assert receipt["status"] == "downloaded"
    assert receipt["provider_cost_usd"] is None
    with pytest.raises(BudgetError):
        c.generate(request(), out_dir=str(tmp_path / "second"))


def test_terminal_failure_preserves_known_charge(tmp_path):
    opener = Mock(side_effect=[response({"id": "job-123", "status": "failed", "usage": {"cost": .2},
                                        "error": "never-log-this-key"})])
    c = client(opener)
    with pytest.raises(OpenRouterError):
        c.generate(request(), out_dir=str(tmp_path / "job"))
    saved = json.loads((tmp_path / "job/receipt.json").read_text())
    assert saved["status"] == "failed"
    assert saved["provider_cost_usd"] == "0.2"
    assert "never-log" not in str(saved)


def test_failed_job_retains_sanitized_provider_reason(tmp_path):
    opener = Mock(side_effect=[response({"id": "job-123", "status": "failed", "generation_id": "gen-test-123",
                                        "error": {"code": "REFERENCE_FETCH_FAILED", "message":
                                                  "Cannot fetch https://example.com/private?token=secret; key=never-log-this-key"}})])
    c = client(opener)
    with pytest.raises(OpenRouterError):
        c.generate(request(), out_dir=str(tmp_path / "job"))
    saved = json.loads((tmp_path / "job/receipt.json").read_text())
    assert saved["provider_error"]["code"] == "REFERENCE_FETCH_FAILED"
    assert "Cannot fetch" in saved["provider_error"]["message"]
    assert "never-log-this-key" not in str(saved)
    assert "token=secret" not in str(saved)
    assert saved["generation_id"] == "gen-test-123"
    assert saved["provider_cost_usd"] is None
    assert c.post_attempts == 1


def test_poll_error_can_resume_without_post(tmp_path):
    opener = Mock(side_effect=[response({"id": "job-123", "status": "pending"}), URLError("oops")])
    with pytest.raises(OpenRouterError):
        client(opener).generate(request(), out_dir=str(tmp_path / "job"))
    resume_opener = Mock(side_effect=[response({"id": "job-123", "status": "completed", "usage": {"cost": .6}}),
                                     io.BytesIO(b"video")])
    saved = client(resume_opener).resume(str(tmp_path / "job"))
    assert saved["status"] == "downloaded"
    assert all(call.args[0].get_method() == "GET" for call in resume_opener.call_args_list)


@pytest.mark.parametrize("cost", [-1, "NaN", True])
def test_invalid_cost_never_becomes_zero(tmp_path, cost):
    opener = Mock(side_effect=[response({"id": "job-123", "status": "completed", "usage": {"cost": cost}})])
    c = client(opener)
    with pytest.raises(OpenRouterError):
        c.generate(request(), out_dir=str(tmp_path / "job"))
    assert c.spent_usd is None


def test_redirect_strips_authorization_on_foreign_origin():
    original = Request("https://openrouter.ai/api/v1/videos/job-123/content",
                       headers={"Authorization": "Bearer never-log-this-key"})
    redirected = _ContentRedirect().redirect_request(original, None, 302, "Found", {}, "https://cdn.example.com/video.mp4")
    assert redirected.get_header("Authorization") is None


def test_catalogue_preflight_rejects_higher_price_or_missing_audio():
    model = {"id": "alibaba/wan-2.7", "supported_resolutions": ["720p"],
             "supported_aspect_ratios": ["16:9"], "supported_durations": list(range(2, 11)),
             "generate_audio": True, "seed": True, "pricing_skus": {"duration_seconds": "0.1"}}
    check_video_model(config(), [model])
    model["pricing_skus"]["duration_seconds"] = "0.2"
    with pytest.raises(BudgetError):
        check_video_model(config(), [model])
    model["pricing_skus"]["duration_seconds"] = "0.1"
    model["generate_audio"] = False
    with pytest.raises(ValueError):
        check_video_model(config(), [model])


def test_seedance_quote_uses_video_tokens_not_seconds():
    cfg = {**config(), "model": "bytedance/seedance-2.0-mini", "price_per_million_video_tokens_usd": "3.50"}
    cfg.pop("price_per_second_usd")
    req = {**request(), "model": cfg["model"]}
    assert estimate_video_cost(cfg, req) == Decimal('0.4536')
    cfg["resolution"] = req["resolution"] = "480p"
    assert estimate_video_cost(cfg, req) == Decimal('0.2017575')


def test_seedance_catalogue_and_native_audio_request(tmp_path):
    cfg = {**config(), "model": "bytedance/seedance-2.0-mini", "price_per_million_video_tokens_usd": "3.50"}
    cfg.pop("price_per_second_usd")
    model = {"id": cfg["model"], "supported_resolutions": ["480p", "720p"],
             "supported_aspect_ratios": ["16:9"], "supported_durations": list(range(4,16)),
             "generate_audio": True, "seed": True, "pricing_skus": {"video_tokens": "0.0000035",
             "video_tokens_without_audio": "0.0000035", "video_tokens_with_video_input": "0.0000021"}}
    check_video_model(cfg, [model])
    opener = Mock(side_effect=[response({"id": "job-seed", "status": "completed", "usage": {"cost": .4536}}),
                              io.BytesIO(b"synthetic-video-bytes")])
    c = OpenRouterVideoClient(cfg, api_key="never-log-this-key", allow_paid=True, max_cost_usd="0.60", opener=opener)
    receipt = c.generate({**request(), "model": cfg["model"]}, out_dir=str(tmp_path / "seed"))
    assert receipt["estimated_cost_usd"] == '0.4536'
    assert c.post_attempts == 1
    payload = json.loads(opener.call_args_list[0].args[0].data)
    assert payload['generate_audio'] is True and payload['input_references'] == request()['input_references']
    model["pricing_skus"]["video_tokens"] = "0.0000040"
    with pytest.raises(BudgetError):
        check_video_model(cfg, [model])
    invalid = {**request(), "model": cfg["model"], "input_references": [{"type":"video_url","video_url":{"url":"https://example.com/video.mp4"}}]}
    with pytest.raises(ValueError):
        estimate_video_cost(cfg, invalid)
