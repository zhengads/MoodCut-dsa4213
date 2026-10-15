"""OpenRouter asynchronous video transport with explicit paid-call boundaries.

POST is never retried. GET polling/download can resume a saved job. This is a
distinct API from the existing shared text planning/review client.
"""
from copy import deepcopy
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
import re
from time import monotonic, sleep
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .client import BudgetError, OpenRouterError, _NoRedirect, _strict_json
from .pipeline import json_hash

BASE = "https://openrouter.ai/api/v1/videos"
TERMINAL = {"completed", "failed", "cancelled", "expired"}
STATUSES = TERMINAL | {"pending", "in_progress"}


def _money(value, *, positive=False):
    if isinstance(value, bool) or value is None:
        raise ValueError("Invalid cost")
    try:
        amount = Decimal(str(value))
    except InvalidOperation:
        raise ValueError("Invalid cost") from None
    if not amount.is_finite() or amount < 0 or (positive and amount == 0):
        raise ValueError("Invalid cost")
    return amount


def _json_request(opener, request):
    try:
        with opener(request, timeout=60) as response:
            raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError("Oversize response")
        data = _strict_json(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Expected an object")
        return data
    except HTTPError as exc:
        raise OpenRouterError(f"Video API HTTP {exc.code}; no automatic resubmission") from None
    except (URLError, OSError, ValueError, UnicodeError):
        raise OpenRouterError("Video API transport or JSON error; no automatic resubmission") from None


def fetch_video_models() -> list[dict]:
    """Public read-only discovery; does not require a key or create a job."""
    data = _json_request(build_opener(_NoRedirect()).open, Request(BASE + "/models"))
    if not isinstance(data.get("data"), list):
        raise OpenRouterError("Invalid video model catalogue")
    return data["data"]


def check_video_model(config: dict, models: list[dict]) -> None:
    matches = [m for m in models if m.get("id") == config["model"]]
    if len(matches) != 1:
        raise ValueError("Selected video model is unavailable")
    model = matches[0]
    for field, supported in (("resolution", "supported_resolutions"), ("aspect_ratio", "supported_aspect_ratios")):
        if config[field] not in (model.get(supported) or []):
            raise ValueError(f"Video model does not support {field}")
    if model.get("generate_audio") is not True or model.get("seed") is not True:
        raise ValueError("Video model must advertise audio and seed support")
    for shot in config.get("shots", []):
        if shot["duration_s"] not in (model.get("supported_durations") or []):
            raise ValueError("Video model does not support requested duration")
    # This explicit rate parser is for the pinned Wan 2.7 contract, not a
    # comparison across unrelated token/image/second SKU units.
    if config["model"] != "alibaba/wan-2.7":
        raise ValueError("Unverified video price contract")
    skus = model.get("pricing_skus") or {}
    if set(skus) != {"duration_seconds"}:
        raise BudgetError("Video pricing SKU contract changed; verify before submission")
    live_rate = _money(skus["duration_seconds"], positive=True)
    if live_rate > _money(config["price_per_second_usd"], positive=True):
        raise BudgetError("Advertised video price exceeds the configured estimate")


class _ContentRedirect(HTTPRedirectHandler):
    """CDN redirects may download bytes but must not receive the API key."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parts = urlsplit(newurl)
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
            raise OpenRouterError("Unsafe video content redirect")
        result = super().redirect_request(req, fp, code, msg, headers, newurl)
        if result is not None and (parts.hostname != "openrouter.ai" or parts.port not in (None, 443)):
            result.remove_header("Authorization")
        return result


class OpenRouterVideoClient:
    def __init__(self, config, *, api_key=None, allow_paid=False, max_cost_usd=None,
                 opener=None, poll_interval_s=8, job_timeout_s=900):
        self.config = deepcopy(config)
        self._key = api_key if api_key is not None else os.environ.get("OPENROUTER_API_KEY", "")
        self._allow_paid = allow_paid is True
        self._limit = _money(max_cost_usd, positive=True)
        self._rate = _money(config["price_per_second_usd"], positive=True)
        self._spent = Decimal(0)
        self._unknown = False
        self._resume_only = False
        self.post_attempts = 0
        self._api = opener or build_opener(_NoRedirect()).open
        self._content = opener or build_opener(_ContentRedirect()).open
        if not 0 <= poll_interval_s <= 30 or not 0 < job_timeout_s <= 3600:
            raise ValueError("Invalid bounded polling settings")
        self._poll_interval = poll_interval_s
        self._job_timeout = job_timeout_s

    @property
    def spent_usd(self):
        return None if self._unknown else str(self._spent)

    @property
    def credentials_available(self):
        return bool(self._key and self._key.strip())

    def _request(self, path="", payload=None):
        headers = {"Authorization": "Bearer " + self._key, "X-OpenRouter-Title": "MoodCut"}
        if payload is not None:
            headers["Content-Type"] = "application/json"
        return Request(BASE + path, headers=headers,
                       data=None if payload is None else json.dumps(payload, allow_nan=False).encode("utf-8"))

    def _save(self, directory, receipt):
        # Directory belongs exclusively to this job, created before POST.
        temporary = directory / "receipt.json.tmp"
        temporary.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        temporary.replace(directory / "receipt.json")

    def _safe_provider_error(self, value):
        """Keep actionable error fields, excluding credentials and signed URLs."""
        if value is None or type(value) in (bool, int):
            return value
        if isinstance(value, dict):
            return {key: self._safe_provider_error(value[key])
                    for key in ("code", "message", "type", "error", "details") if key in value}
        if isinstance(value, list):
            return [self._safe_provider_error(item) for item in value[:5]]
        text = str(value).replace(self._key, "[redacted-key]")
        text = re.sub(r"https?://[^\s\"<>]+", "[redacted-url]", text)
        text = re.sub(r"sk-[A-Za-z0-9_-]+", "[redacted-key]", text)
        text = re.sub(r"(?i)bearer\s+[A-Za-z0-9._~+/-]+=*", "Bearer [redacted-key]", text)
        return text[:2000]

    def generate(self, request: dict, *, out_dir: str) -> dict:
        if not self._allow_paid:
            raise BudgetError("Paid video generation is disabled")
        if self._unknown or self._resume_only:
            raise BudgetError("Reconcile earlier charges before any further generation")
        if not self._key or not self._key.strip():
            raise ValueError("Set OPENROUTER_API_KEY in the process environment")
        allowed = {"model", "prompt", "duration", "resolution", "aspect_ratio", "generate_audio", "seed", "input_references"}
        if set(request) != allowed or not isinstance(request["prompt"], str) or not request["prompt"].strip():
            raise ValueError("Unexpected video request shape")
        if self.config["model"] != "alibaba/wan-2.7" or any(request[k] != self.config[k] for k in ("model", "resolution", "aspect_ratio")):
            raise ValueError("Video request does not match the verified config")
        if request["generate_audio"] is not True or type(request["seed"]) is not int or not request["input_references"]:
            raise ValueError("Native audio, seed and references are required")
        duration = request["duration"]
        if type(duration) is not int or duration not in range(2, 11):
            raise ValueError("Unsupported video duration")
        estimate = self._rate * duration
        if self._spent + estimate > self._limit:
            raise BudgetError("Video estimate exceeds remaining local budget")
        directory = Path(out_dir).resolve()
        directory.mkdir(parents=True, exist_ok=False)
        receipt = {"schema_version": "1.0", "model": request["model"], "status": "submitting",
                   "job_id": None, "estimated_cost_usd": str(estimate), "provider_cost_usd": None,
                   "post_attempts": 1, "poll_attempts": 0, "video_path": None,
                   "request_sha256": json_hash(request)}
        self._save(directory, receipt)
        # After any POST attempt, only a validated terminal usage record can
        # reconcile the charge. A lost submit response must not trigger retry.
        self._unknown = True
        try:
            self.post_attempts += 1
            data = _json_request(self._api, self._request(payload=request))
            job_id = data.get("id")
            if not isinstance(job_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,160}", job_id):
                raise OpenRouterError("Video submission returned no usable job ID; reconcile remotely")
            receipt["job_id"] = job_id
            receipt["status"] = "submitted"
            self._save(directory, receipt)
            return self._finish(directory, receipt, first=data)
        except OpenRouterError:
            if receipt["status"] == "submitting":
                receipt["status"] = "submission_unknown"
                self._save(directory, receipt)
            raise

    def resume(self, out_dir: str) -> dict:
        """GET-only recovery of one saved job; this instance cannot submit later."""
        if not self._key or not self._key.strip():
            raise ValueError("Set OPENROUTER_API_KEY in the process environment")
        directory = Path(out_dir).resolve(strict=True)
        receipt = _strict_json((directory / "receipt.json").read_text(encoding="utf-8"))
        job_id = receipt.get("job_id")
        if receipt.get("model") != self.config["model"] or not isinstance(job_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,160}", job_id):
            raise ValueError("Receipt has no matching resumable job")
        self._resume_only = True
        self._unknown = True
        if receipt["status"] == "downloaded" and (directory / "generated.mp4").is_file():
            return receipt
        return self._finish(directory, receipt)

    def _finish(self, directory, receipt, first=None):
        deadline = monotonic() + self._job_timeout
        data = first
        while True:
            if data is None or data.get("status") not in TERMINAL:
                if monotonic() >= deadline:
                    receipt["status"] = "polling_timeout"
                    self._save(directory, receipt)
                    raise OpenRouterError("Video polling timed out; the job may still charge. Resume this job, do not resubmit")
                receipt["poll_attempts"] += 1
                self._save(directory, receipt)
                try:
                    data = _json_request(self._api, self._request("/" + receipt["job_id"]))
                except OpenRouterError:
                    receipt["status"] = "polling_interrupted"
                    self._save(directory, receipt)
                    raise
            if data.get("status") not in STATUSES or data.get("id", receipt["job_id"]) != receipt["job_id"]:
                receipt["status"] = "invalid_poll_response"
                self._save(directory, receipt)
                raise OpenRouterError("Invalid video job status; retain job ID for reconciliation")
            receipt["status"] = data["status"]
            self._save(directory, receipt)
            if data["status"] in TERMINAL:
                break
            sleep(self._poll_interval)
            data = None
        generation_id = data.get("generation_id")
        if isinstance(generation_id, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,200}", generation_id):
            receipt["generation_id"] = generation_id
        if data.get("error") is not None:
            receipt["provider_error"] = self._safe_provider_error(data["error"])
        self._save(directory, receipt)
        usage = data.get("usage")
        value = usage.get("cost") if isinstance(usage, dict) else None
        if value is not None:
            try:
                cost = _money(value)
            except ValueError:
                receipt["status"] = "invalid_usage"
                self._save(directory, receipt)
                raise OpenRouterError("Invalid video usage; reconcile charges before continuing") from None
            receipt["provider_cost_usd"] = str(cost)
            self._spent += cost
            self._unknown = False
        self._save(directory, receipt)
        if data["status"] != "completed":
            raise OpenRouterError("Video job ended as " + data["status"] + "; no automatic replacement")
        target = directory / "generated.mp4"
        partial = directory / "generated.mp4.part"
        if target.exists():
            raise FileExistsError("Generated output already exists; preserve it")
        try:
            # Ignore returned signed URLs; construct the authenticated endpoint.
            with self._content(self._request("/" + receipt["job_id"] + "/content?index=0"), timeout=60) as response:
                total = 0
                with partial.open("wb") as output:
                    while chunk := response.read(1024 * 1024):
                        total += len(chunk)
                        if total > 200_000_000:
                            raise OpenRouterError("Video download exceeds 200 MB limit")
                        output.write(chunk)
            if total == 0:
                raise OpenRouterError("Empty video download")
            partial.replace(target)
        except (HTTPError, URLError, OSError):
            receipt["status"] = "download_interrupted"
            self._save(directory, receipt)
            raise OpenRouterError("Video download interrupted; resume the saved job without POST") from None
        receipt["status"] = "downloaded"
        receipt["video_path"] = str(target)
        self._save(directory, receipt)
        return receipt
