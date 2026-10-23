"""Hand-written transport fixtures, never real generation requests."""
import io
import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock
from urllib.error import HTTPError, URLError
from urllib.request import Request

import pytest

from moodcut.client import BudgetError, OpenRouterError
from moodcut.video_client import OpenRouterVideoClient, check_video_model, estimate_video_cost, _ContentRedirect
from test_video_generation import inspection_inputs


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


@pytest.fixture
def execution_case(inspection_inputs, monkeypatch):
    """Real executor/client/compiler/accounting with local transport and A/V only."""
    from moodcut import video_client
    from moodcut.pipeline import read_json
    import socket
    case = inspection_inputs
    case.update(http=[], mode="success", cost="0.07", jobs={})
    monkeypatch.setattr(socket, "create_connection", lambda *a, **k: pytest.fail("No real network"))
    monkeypatch.setattr(socket.socket, "connect", lambda *a, **k: pytest.fail("No real network"))
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: pytest.fail("No real network"))

    def opener(req, **kwargs):
        method = req.get_method()
        case["http"].append((method, req.full_url))
        if method == "POST":
            if case["mode"] == "lost_submit":
                raise URLError("Synthetic lost response")
            payload = json.loads(req.data)
            job_id = f"synthetic-{len(case['jobs'])}"
            case["jobs"][job_id] = payload
            if case["mode"] in ("poll_interrupt", "keyboard_interrupt"):
                return response({"id": job_id, "status": "pending"})
        else:
            job_id = req.full_url.split("/videos/")[1].split("/")[0]
            if "/content?" in req.full_url:
                if case["mode"] == "download_interrupt":
                    raise URLError("Synthetic content interruption")
                return io.BytesIO(b"not media" if case["mode"] == "bad_media" else case["media"][0].read_bytes())
            if case["mode"] == "poll_interrupt":
                raise URLError("Synthetic polling interruption")
            if case["mode"] == "keyboard_interrupt":
                raise KeyboardInterrupt()
        result = {"id": job_id, "status": "failed" if case["mode"] == "failed" else "completed"}
        if case["cost"] is not None:
            result["usage"] = {"cost": case["cost"]}
        return response(result)

    monkeypatch.setattr(video_client, "OpenRouterVideoClient", lambda *a, **k:
        OpenRouterVideoClient(*a, **k, api_key="synthetic-secret-do-not-log", opener=opener, poll_interval_s=0))
    catalogue = [{"id": "alibaba/wan-2.7", "supported_resolutions": ["720p"],
                  "supported_aspect_ratios": ["16:9"], "generate_audio": True, "seed": True,
                  "supported_durations": [2], "pricing_skus": {"duration_seconds": "0.10"}}]
    case["catalogue"] = catalogue
    monkeypatch.setattr(video_client, "fetch_video_models", lambda: catalogue)
    case["pricing"] = Path(__file__).resolve().parents[1] / "configs/video.json"
    case["root"] = case["pricing"].parents[1]
    return case


def execute_case(case, output, **overrides):
    from moodcut.pipeline import execute_generated_run
    return execute_generated_run(case["prep"], out_dir=output, pricing_config=case["pricing"],
        project_root=case["root"], media_origin="synthetic", **{"allow_paid": True, "max_cost_usd": "2", **overrides})


def test_three_condition_execution_to_qualification_and_blind_export(execution_case, tmp_path):
    from moodcut.pipeline import read_json
    from moodcut.evaluation import qualify_generated_records, export_generated_blind_items, summarize_generated_records
    case = execution_case
    original = {str(p): p.read_bytes() for p in case["prep"].rglob("*.json")}
    output = tmp_path / "execution"
    state = execute_case(case, output)
    assert state["status"] == "assembled_requires_manual_inspection"
    assert state["generation_posts_this_invocation"] == 4
    records = output / state["records_path"]
    block = read_json(records)
    assert [r["condition"] for r in block["runs"]] == ["baseline", "generic_review", "moodcut"]
    assert block["accounting"]["generation_posts"] == 4
    assert block["accounting"]["video_get_calls"] == 4
    assert block["accounting"]["provider_cost_usd"] == pytest.approx(.28)
    assert sum(j["reused_from"] is not None for r in block["runs"] for j in r["generation_jobs"]) == 2
    assert qualify_generated_records(records, pricing_config=case["pricing"], project_root=case["root"])["accounting_verified"]
    exported = tmp_path / "blind"
    export_generated_blind_items([records], out_dir=exported, seed=0, pricing_config=case["pricing"], project_root=case["root"])
    summary = summarize_generated_records([records], [], private_key=exported / "PRIVATE/private_key.csv",
        pricing_config=case["pricing"], project_root=case["root"])
    assert summary["overall"]["generation"]["generated_runs"] == 3
    assert all(p.read_bytes() == value for path, value in original.items() for p in [Path(path)])
    checks = read_json(output / "inspection/manual_checks.json")
    assert checks["status"] == "not_reviewed"
    assert all(i["audio_lipsync"] is None for i in checks["items"])


@pytest.mark.parametrize("mode,cost,remote", [
    ("failed", "0.03", "failed"), ("lost_submit", None, "submission_unknown"),
    ("poll_interrupt", None, "polling_interrupted"),
    ("download_interrupt", "0.07", "download_interrupted"),
    ("keyboard_interrupt", None, "submitted"), ("success", None, "downloaded"),
    ("bad_media", "0.07", "downloaded")])
def test_execution_stops_and_retains_all_three_conditions(execution_case, tmp_path, mode, cost, remote):
    from moodcut.pipeline import read_json
    case = execution_case
    case.update(mode=mode, cost=cost)
    output = tmp_path / "stopped"
    state = execute_case(case, output)
    assert state["status"] == "stopped"
    assert state["generation_posts_this_invocation"] == 1
    assert sum(method == "POST" for method, url in case["http"]) == 1
    block = read_json(output / state["records_path"])
    assert len(block["runs"]) == 3
    jobs = [j for r in block["runs"] for j in r["generation_jobs"]]
    assert jobs[0]["remote_status"] == remote
    assert sum(j["status"] == "prepared_offline" for j in jobs) == 5
    assert block["accounting"]["generation_posts"] == 1
    assert block["accounting"]["provider_cost_usd"] == (float(cost) if cost else None)
    assert "synthetic-secret-do-not-log" not in (output / "execution.json").read_text()
    with pytest.raises(FileExistsError):
        execute_case(case, output)
    assert sum(method == "POST" for method, url in case["http"]) == 1


@pytest.mark.parametrize("mode", ["poll_interrupt", "download_interrupt"])
def test_execution_resume_is_get_only_and_preserves_previous_snapshot(execution_case, tmp_path, mode):
    from moodcut.pipeline import read_json
    case = execution_case
    case["mode"] = mode
    original = tmp_path / "interrupted"
    execute_case(case, original)
    before = {p: p.read_bytes() for p in original.rglob("*") if p.is_file()}
    case["mode"] = "success"
    case["http"].clear()
    recovered = tmp_path / "recovered"
    state = execute_case(case, recovered, resume_execution=original, resume_condition="baseline",
                         resume_shot_id=case["bundle"]["conditions"][0]["jobs"][0]["shot_id"])
    assert state["mode"] == "resume_get_only"
    assert state["generation_posts_this_invocation"] == 0
    assert case["http"] and all(method == "GET" for method, url in case["http"])
    block = read_json(recovered / state["records_path"])
    assert block["accounting"]["generation_posts"] == 1
    assert block["accounting"]["provider_cost_usd"] == pytest.approx(.07)
    assert block["runs"][0]["generation_jobs"][0]["status"] == "downloaded"
    assert sum(j["status"] == "prepared_offline" for r in block["runs"] for j in r["generation_jobs"]) == 5
    assert all(p.read_bytes() == value for p, value in before.items())
    case["http"].clear()
    with pytest.raises(FileExistsError):
        execute_case(case, tmp_path / "second-recovery", resume_execution=original, resume_condition="baseline",
                     resume_shot_id=case["bundle"]["conditions"][0]["jobs"][0]["shot_id"])
    assert not case["http"]


@pytest.mark.parametrize("kind", ["unsubmitted", "no_id", "terminal", "changed_evidence"])
def test_execution_cannot_resume_unsubmitted_lost_or_terminal_tasks(execution_case, tmp_path, kind):
    from moodcut.pipeline import read_json
    case = execution_case
    case["mode"] = {"no_id": "lost_submit", "terminal": "failed"}.get(kind, "poll_interrupt")
    original = tmp_path / "original"
    execute_case(case, original)
    shot_id = case["bundle"]["conditions"][0]["jobs"][0 if kind != "unsubmitted" else 1]["shot_id"]
    if kind == "changed_evidence":
        path = original / "evidence.json"
        data = read_json(path)
        data["provenance"] = "tampered"
        path.write_text(json.dumps(data))
    case["http"].clear()
    with pytest.raises(ValueError):
        execute_case(case, tmp_path / "rejected", resume_execution=original, resume_condition="baseline", resume_shot_id=shot_id)
    assert not case["http"]
    assert not (tmp_path / "rejected").exists()


@pytest.mark.parametrize("kind", ["budget", "missing_budget", "catalogue", "request", "key", "tools", "discovery_change"])
def test_execution_preflight_blocks_http_and_output(execution_case, tmp_path, monkeypatch, kind):
    from moodcut import pipeline, video_client
    case = execution_case
    options = {}
    if kind == "budget":
        options["max_cost_usd"] = "0.01"
    elif kind == "missing_budget":
        options["max_cost_usd"] = None
    elif kind == "catalogue":
        case["catalogue"][0]["supported_durations"] = [6]
    elif kind == "request":
        path = case["prep"] / "bundle.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["conditions"][0]["jobs"][0]["request"]["prompt"] += " altered"
        data["conditions"][0]["jobs"][0]["request_sha256"] = pipeline.json_hash(data["conditions"][0]["jobs"][0]["request"])
        path.write_text(json.dumps(data))
    elif kind == "key":
        monkeypatch.setattr(video_client, "OpenRouterVideoClient", lambda *a, **k: OpenRouterVideoClient(*a, **k, api_key=""))
    elif kind == "discovery_change":
        def discovery():
            path = case["prep"] / "preparation.json"
            data = pipeline.read_json(path)
            data["quote_scope"] = "changed during discovery"
            path.write_text(json.dumps(data), encoding="utf-8")
            return case["catalogue"]
        monkeypatch.setattr(video_client, "fetch_video_models", discovery)
    else:
        monkeypatch.setattr(pipeline.shutil, "which", lambda *a: None)
    with pytest.raises((ValueError, BudgetError)):
        execute_case(case, tmp_path / "rejected", **options)
    assert not case["http"]
    assert not (tmp_path / "rejected").exists()


def test_execution_cli_default_is_offline_and_budget_alone_is_rejected(execution_case, tmp_path):
    from moodcut.__main__ import main
    from moodcut.pipeline import read_json
    case = execution_case
    args = ["execute-generated", "--project-root", str(case["root"]), "--preparation", str(case["prep"]),
            "--pricing-config", str(case["pricing"]), "--media-origin", "synthetic", "--output", str(tmp_path / "offline")]
    assert main(args + ["--max-cost-usd", "2"]) == 1
    assert not (tmp_path / "offline").exists()
    assert main(args) == 0
    state = read_json(tmp_path / "offline/execution.json")
    assert state["generation_posts_this_invocation"] == 0
    assert state["status"] == "prepared_offline"
    assert not case["http"]


def test_execution_recovers_then_explicitly_continues_without_duplicate_post(execution_case, tmp_path):
    from moodcut.__main__ import main
    from moodcut.pipeline import read_json
    case = execution_case
    first = tmp_path / "interrupted"
    case["mode"] = "poll_interrupt"
    execute_case(case, first)
    case["mode"] = "success"
    recovered = tmp_path / "recovered"
    execute_case(case, recovered, resume_execution=first, resume_condition="baseline",
        resume_shot_id=case["bundle"]["conditions"][0]["jobs"][0]["shot_id"])
    output = tmp_path / "continued"
    assert main(["execute-generated", "--project-root", str(case["root"]), "--preparation", str(case["prep"]),
        "--pricing-config", str(case["pricing"]), "--media-origin", "synthetic", "--output", str(output),
        "--continue-execution", str(recovered), "--allow-paid", "--max-cost-usd", "2"]) == 0
    state = read_json(output / "execution.json")
    assert state["status"] == "assembled_requires_manual_inspection"
    assert state["generation_posts_this_invocation"] == 3
    assert sum(method == "POST" for method, url in case["http"]) == 4
    block = read_json(output / state["records_path"])
    assert block["accounting"]["generation_posts"] == 4
    assert block["accounting"]["provider_cost_usd"] == pytest.approx(.28)
    case["http"].clear()
    with pytest.raises(FileExistsError):
        execute_case(case, tmp_path / "duplicate-child", continue_execution=recovered)
    assert not case["http"]
    assert not (tmp_path / "duplicate-child").exists()


@pytest.mark.parametrize("kind", ["unknown_cost", "interrupted", "prior_budget"])
def test_execution_continuation_requires_reconciliation_and_counts_prior_charges(execution_case, tmp_path, kind):
    case = execution_case
    case["mode"] = "poll_interrupt" if kind != "unknown_cost" else "success"
    case["cost"] = None if kind == "unknown_cost" else "0.07"
    original = tmp_path / "original"
    execute_case(case, original)
    parent = original
    if kind == "prior_budget":
        case["mode"] = "success"
        parent = tmp_path / "recovered"
        execute_case(case, parent, resume_execution=original, resume_condition="baseline",
            resume_shot_id=case["bundle"]["conditions"][0]["jobs"][0]["shot_id"])
    case["http"].clear()
    with pytest.raises(BudgetError):
        execute_case(case, tmp_path / "rejected", continue_execution=parent,
                     **({"max_cost_usd": "1.00"} if kind == "prior_budget" else {}))
    assert not case["http"]
    assert not (tmp_path / "rejected").exists()


def test_execution_cli_single_shot_preserves_original_seed_and_unchanged_reuse(execution_case, tmp_path):
    from moodcut.__main__ import main
    from moodcut.pipeline import prepare_generated_run, read_json
    case = execution_case
    preparation = tmp_path / "single"
    shot = case["bundle"]["conditions"][0]["jobs"][1]
    prepare_generated_run(case["source"], out_dir=preparation, project_root=case["root"],
                          pricing_config=case["pricing"], shot_id=shot["shot_id"])
    output = tmp_path / "executed-single"
    assert main(["execute-generated", "--project-root", str(case["root"]), "--preparation", str(preparation),
        "--pricing-config", str(case["pricing"]), "--media-origin", "synthetic", "--output", str(output),
        "--allow-paid", "--max-cost-usd", "2"]) == 0
    assert sum(method == "POST" for method, url in case["http"]) == 1
    assert next(iter(case["jobs"].values()))["seed"] == shot["request"]["seed"]
    state = read_json(output / "execution.json")
    block = read_json(output / state["records_path"])
    assert block["selected_shot_ids"] == [shot["shot_id"]]
    assert block["accounting"]["generation_posts"] == 1
    assert block["accounting"]["provider_cost_usd"] == pytest.approx(.07)


def test_execution_rechecks_parent_receipts_after_discovery(execution_case, tmp_path, monkeypatch):
    from moodcut import video_client
    from moodcut.pipeline import read_json
    case = execution_case
    original = tmp_path / "first"
    case["mode"] = "poll_interrupt"
    execute_case(case, original)
    case["mode"] = "success"
    recovered = tmp_path / "recovered"
    execute_case(case, recovered, resume_execution=original, resume_condition="baseline",
        resume_shot_id=case["bundle"]["conditions"][0]["jobs"][0]["shot_id"])
    def discovery():
        path = recovered / "resumed-job/receipt.json"
        data = read_json(path)
        data["provider_cost_usd"] = None
        path.write_text(json.dumps(data), encoding="utf-8")
        return case["catalogue"]
    monkeypatch.setattr(video_client, "fetch_video_models", discovery)
    case["http"].clear()
    with pytest.raises(ValueError, match="changed during preflight"):
        execute_case(case, tmp_path / "rejected", continue_execution=recovered)
    assert not case["http"]
    assert not (tmp_path / "rejected").exists()


def test_execution_checks_copied_recovery_receipt_before_get(execution_case, tmp_path, monkeypatch):
    from moodcut import pipeline
    from moodcut.pipeline import read_json
    case = execution_case
    original = tmp_path / "interrupted"
    case["mode"] = "poll_interrupt"
    execute_case(case, original)
    case["mode"] = "success"
    copy = pipeline.shutil.copyfile
    def corrupt_copy(source, target, *args, **kwargs):
        result = copy(source, target, *args, **kwargs)
        if Path(target).name == "receipt.json":
            data = read_json(target)
            data["job_id"] = "another-task"
            Path(target).write_text(json.dumps(data), encoding="utf-8")
        return result
    monkeypatch.setattr(pipeline.shutil, "copyfile", corrupt_copy)
    case["http"].clear()
    state = execute_case(case, tmp_path / "rejected", resume_execution=original, resume_condition="baseline",
        resume_shot_id=case["bundle"]["conditions"][0]["jobs"][0]["shot_id"])
    assert state["status"] == "stopped"
    assert not case["http"]


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
    assert receipt["download_attempts"] == 1 and receipt["download_redirect_attempts"] == 0
    assert receipt["video_get_calls"] == 2 and receipt["real_http_calls"] == 3
    assert receipt["http_counts_complete"] is True
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
    assert json.loads(stored)["last_error"] == {
        "phase": "submit", "kind": "transport", "error_type": "URLError"}


@pytest.mark.parametrize("code", [400, 429, 502])
def test_submit_http_error_retains_diagnostic_without_retry(tmp_path, code):
    body = response({"error": {"code": "SYNTHETIC_REJECTION", "message":
        "Cannot fetch HTTPS://example.com/a?token=private; key=never-log-this-key DATA:image/png;base64,private-image",
        "metadata": {"provider_name": "synthetic", "raw": json.dumps({
            "error": {"message": "Synthetic reference error"}, "headers": {"secret": "do-not-store"}})},
        "request": {"prompt": "do-not-store"}}})
    error = HTTPError("https://openrouter.ai/api/v1/videos", code, "unsafe reason", {
        "x-request-id": "req-synthetic-123", "Authorization": "never-log-this-key"}, body)
    opener = Mock(side_effect=error)
    c = client(opener)
    with pytest.raises(OpenRouterError, match=f"HTTP {code}"):
        c.generate(request(), out_dir=str(tmp_path / "job"))
    saved = json.loads((tmp_path / "job/receipt.json").read_text())
    assert saved["last_error"] == {"phase": "submit", "kind": "http", "http_status": code,
                                   "request_id": "req-synthetic-123"}
    assert saved["provider_error"]["code"] == "SYNTHETIC_REJECTION"
    assert saved["provider_error"]["metadata"]["raw"] == {"error": {"message": "Synthetic reference error"}}
    assert saved["status"] == "submission_unknown" and saved["job_id"] is None
    assert saved["provider_cost_usd"] is None and c.spent_usd is None
    assert body.closed
    for secret in ("never-log-this-key", "token=private", "private-image", "do-not-store", "unsafe reason"):
        assert secret not in json.dumps(saved)
    with pytest.raises(BudgetError):
        c.generate(request(), out_dir=str(tmp_path / "second"))
    assert opener.call_count == c.post_attempts == 1


@pytest.mark.parametrize("raw", [b'<html>secret</html>', b'{invalid', b'x' * 8193,
                                b'[' * 2000 + b'0' + b']' * 2000],
                         ids=["html", "malformed_json", "oversize", "too_deep"])
def test_http_error_invalid_or_large_body_keeps_status_only(tmp_path, raw):
    body = io.BytesIO(raw)
    opener = Mock(side_effect=HTTPError("https://example.com", 502, "unsafe", {}, body))
    with pytest.raises(OpenRouterError, match="HTTP 502"):
        client(opener).generate(request(), out_dir=str(tmp_path / "job"))
    saved = json.loads((tmp_path / "job/receipt.json").read_text())
    assert saved["last_error"] == {"phase": "submit", "kind": "http", "http_status": 502}
    assert "provider_error" not in saved and "secret" not in str(saved)
    assert body.closed and opener.call_count == 1


def test_invalid_json_response_has_distinct_saved_diagnostic(tmp_path):
    opener = Mock(return_value=io.BytesIO(b'{not-json never-log-this-key'))
    with pytest.raises(OpenRouterError, match="JSON error"):
        client(opener).generate(request(), out_dir=str(tmp_path / "job"))
    saved = json.loads((tmp_path / "job/receipt.json").read_text())
    assert saved["last_error"]["phase"] == "submit"
    assert saved["last_error"]["kind"] == "invalid_response"
    assert "never-log-this-key" not in str(saved) and opener.call_count == 1


@pytest.mark.parametrize("phase", ["poll", "download"])
def test_http_error_after_submit_retains_phase_id_and_known_cost(tmp_path, phase):
    initial = {"id": "job-http", "status": "pending" if phase == "poll" else "completed"}
    if phase == "download":
        initial["usage"] = {"cost": .6}
    opener = Mock(side_effect=[response(initial), HTTPError("https://example.com", 503, "unsafe", {},
        response({"error": {"code": "SYNTHETIC_UNAVAILABLE", "message": "Bearer never-log-this-key"}}))])
    with pytest.raises(OpenRouterError):
        client(opener).generate(request(), out_dir=str(tmp_path / "job"))
    saved = json.loads((tmp_path / "job/receipt.json").read_text())
    assert saved["last_error"] == {"phase": phase, "kind": "http", "http_status": 503}
    assert saved["job_id"] == "job-http"
    assert saved["status"] == ("polling_interrupted" if phase == "poll" else "download_interrupted")
    assert saved["provider_cost_usd"] == (None if phase == "poll" else "0.6")
    assert saved["provider_error"]["code"] == "SYNTHETIC_UNAVAILABLE"
    assert "never-log-this-key" not in str(saved)
    assert opener.call_count == 2
    assert [c.args[0].get_method() for c in opener.call_args_list] == ["POST", "GET"]


def test_http_submit_diagnostic_survives_executor_final_records(execution_case, tmp_path, monkeypatch):
    from moodcut import video_client
    from moodcut.pipeline import read_json
    case = execution_case
    original = {p: p.read_bytes() for p in case["prep"].rglob("*.json")}
    transport = Mock(side_effect=HTTPError("https://example.com", 400, "unsafe", {}, response({
        "error": {"code": "SYNTHETIC_BAD_INPUT", "message": "Synthetic invalid parameter"}})))
    monkeypatch.setattr(video_client, "OpenRouterVideoClient", lambda *a, **k:
        OpenRouterVideoClient(*a, **k, api_key="synthetic-secret-do-not-log", opener=transport))
    output = tmp_path / "http-stopped"
    state = execute_case(case, output)
    assert state["status"] == "stopped" and state["generation_posts_this_invocation"] == 1
    block = read_json(output / state["records_path"])
    job = block["runs"][0]["generation_jobs"][0]
    assert job["last_error"] == {"phase": "submit", "kind": "http", "http_status": 400}
    assert job["provider_error"]["code"] == "SYNTHETIC_BAD_INPUT"
    assert job["remote_status"] == "submission_unknown" and job["provider_cost_usd"] is None
    assert all(j["status"] == "prepared_offline" for r in block["runs"][1:] for j in r["generation_jobs"])
    assert transport.call_count == 1
    assert all(p.read_bytes() == b for p, b in original.items())


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
    assert saved["last_error"]["reason"] == "missing_or_invalid_job_id"
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


def test_download_failure_counts_actual_attempt_and_resumes_get_only(tmp_path):
    opener = Mock(side_effect=[response({"id": "job-a", "status": "completed", "usage": {"cost": .6}}),
                              URLError("offline simulated failure")])
    with pytest.raises(OpenRouterError, match="download interrupted"):
        client(opener).generate(request(), out_dir=str(tmp_path / "job"))
    saved = json.loads((tmp_path / "job/receipt.json").read_text())
    assert saved["download_attempts"] == saved["video_get_calls"] == 1
    assert saved["real_http_calls"] == 2
    resumed = Mock(side_effect=[response({"id": "job-a", "status": "completed", "usage": {"cost": .6}}), io.BytesIO(b"video")])
    saved = client(resumed).resume(str(tmp_path / "job"))
    assert saved["post_attempts"] == 1 and saved["poll_attempts"] == 1
    assert saved["download_attempts"] == 2 and saved["video_get_calls"] == 3 and saved["real_http_calls"] == 4
    assert all(c.args[0].get_method() == "GET" for c in resumed.call_args_list)


def test_resume_legacy_counters_stay_unknown(tmp_path):
    directory = tmp_path / "legacy"
    directory.mkdir()
    (directory / "receipt.json").write_text(json.dumps({"schema_version": "1.0", "model": config()["model"],
        "status": "polling_interrupted", "job_id": "job-old", "post_attempts": 1, "poll_attempts": 2}), encoding="utf-8")
    opener = Mock(side_effect=[response({"id": "job-old", "status": "completed", "usage": {"cost": .6}}), io.BytesIO(b"video")])
    saved = client(opener).resume(str(directory))
    assert saved["status"] == "downloaded" and saved["poll_attempts"] == 3
    assert saved["download_attempts"] is None and saved["observed_download_attempts"] == 1
    assert saved["video_get_calls"] is saved["real_http_calls"] is None
    assert saved["http_counts_complete"] is False
    assert all(c.args[0].get_method() == "GET" for c in opener.call_args_list)


def test_resume_missing_post_preserves_independently_known_gets(tmp_path):
    from moodcut.pipeline import _generated_receipt_counts
    directory = tmp_path / "partial-counts"
    directory.mkdir()
    (directory / "receipt.json").write_text(json.dumps({"schema_version": "1.0", "model": config()["model"],
        "status": "download_interrupted", "job_id": "job-old", "poll_attempts": 2,
        "download_attempts": 1, "download_redirect_attempts": 0}), encoding="utf-8")
    opener = Mock(side_effect=[response({"id": "job-old", "status": "completed", "usage": {"cost": .6}}), io.BytesIO(b"video")])
    saved = client(opener).resume(str(directory))
    assert saved["video_get_calls"] == 5 and saved["real_http_calls"] is None
    counts = _generated_receipt_counts(saved)
    assert counts["generation_posts"] is None and counts["video_get_calls"] == 5
    assert counts["missing_counters"] == ["post_attempts"]


def test_redirect_attempt_callback_only_for_followed_redirects():
    callback = Mock()
    handler = _ContentRedirect(callback)
    req = Request("https://openrouter.ai/content", headers={"Authorization": "Bearer hidden"})
    assert handler.redirect_request(req, None, 302, "Found", {}, "https://cdn.example.com/video") is not None
    callback.assert_called_once_with()
    with pytest.raises(OpenRouterError):
        handler.redirect_request(req, None, 302, "Found", {}, "http://unsafe.example.com/video")
    callback.assert_called_once_with()


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
