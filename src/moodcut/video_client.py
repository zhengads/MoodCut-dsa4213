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
HEYGEN_MODEL = "heygen/heygen-video-1"
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


class _VideoAPIError(OpenRouterError):
    """Carry bounded response evidence to the existing receipt, never to str(exc)."""

    def __init__(self, message, **diagnostic):
        super().__init__(message)
        self.diagnostic = diagnostic


def _http_error(exc):
    diagnostic = {"kind": "http", "http_status": exc.code}
    try:
        request_id = exc.headers.get("x-request-id") if exc.headers else None
        if isinstance(request_id, str):
            diagnostic["request_id"] = request_id[:200]
        raw = exc.read(8193)
        if len(raw) <= 8192:
            data = _strict_json(raw.decode("utf-8"))
            if isinstance(data, dict):
                diagnostic["provider_error"] = data.get("error", data)
    except (OSError, ValueError, UnicodeError, RecursionError):
        pass  # A malformed/HTML error body must not hide the HTTP status.
    finally:
        exc.close()
    return _VideoAPIError(f"Video API HTTP {exc.code}; no automatic resubmission", **diagnostic)


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
        raise _http_error(exc) from None
    except (URLError, OSError) as exc:
        raise _VideoAPIError("Video API transport error; no automatic resubmission",
                             kind="transport", error_type=type(exc).__name__) from None
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise _VideoAPIError("Video API JSON error; no automatic resubmission",
                             kind="invalid_response", error_type=type(exc).__name__) from None


def fetch_video_models(*, discount_model=None) -> list[dict]:
    """Public read-only discovery; does not require a key or create a job."""
    data = _json_request(build_opener(_NoRedirect()).open, Request(BASE + "/models"))
    if not isinstance(data.get("data"), list):
        raise OpenRouterError("Invalid video model catalogue")
    models = data["data"]
    if discount_model == HEYGEN_MODEL:
        endpoints = _json_request(build_opener(_NoRedirect()).open, Request(
            "https://openrouter.ai/api/v1/models/" + HEYGEN_MODEL + "/endpoints"))
        entries = endpoints.get("data", {}).get("endpoints", [])
        if len(entries) != 1 or entries[0].get("tag") != "heygen":
            raise BudgetError("HeyGen provider pricing changed; verify before submission")
        discount = _money(entries[0].get("pricing", {}).get("discount"))
        if discount >= 1:
            raise BudgetError("Invalid HeyGen provider discount")
        models = deepcopy(models)
        for model in models:
            if model.get("id") == HEYGEN_MODEL:
                model["verified_provider_discount"] = str(discount)
    elif discount_model is not None:
        raise ValueError("Unverified provider discount model")
    return models


def video_request_controls(model):
    """Fixed native audio has no toggle on HeyGen; disable prompt rewriting."""
    if model == HEYGEN_MODEL:
        return {"provider": {"options": {"heygen": {"parameters": {"prompt_enhancement": "disabled"}}}}}
    return {"generate_audio": True}


def estimate_video_cost(config: dict, request: dict) -> Decimal:
    """Quote only verified reference-image/audio configurations in USD."""
    if any(request.get(k) != config.get(k) for k in ("model", "resolution", "aspect_ratio")):
        raise ValueError("Video request does not match its pricing config")
    controls = video_request_controls(config.get("model"))
    if (any(request.get(k) != v for k, v in controls.items())
            or config.get("model") == HEYGEN_MODEL and "generate_audio" in request
            or request.get("aspect_ratio") != "16:9"):
        raise ValueError("This price contract requires native audio and 16:9")
    references = request.get("input_references", [])
    if not isinstance(references, list) or any(not isinstance(ref, dict) or ref.get("type") != "image_url" for ref in references):
        raise ValueError("Only image references are covered by this price contract")
    duration = request.get("duration")
    if config.get("model") == HEYGEN_MODEL:
        if (request.get("resolution") != "768p" or type(duration) is not int or duration not in range(5, 16)
                or not 1 <= len(references) <= 9 or config.get("free_reference_images") != 2):
            raise ValueError("Unsupported HeyGen reference request")
        discount = _money(config.get("provider_discount"))
        if discount >= 1:
            raise ValueError("Invalid HeyGen provider discount")
        return (duration * _money(config.get("reference_price_per_second_usd"), positive=True)
                + max(0, len(references) - 2) * _money(config.get("reference_image_price_usd"), positive=True)) * (1 - discount)
    if config.get("model") == "alibaba/wan-2.7":
        if request.get("resolution") != "720p" or type(duration) is not int or duration not in range(2,11):
            raise ValueError("Unsupported Wan 2.7 request")
        return _money(config.get("price_per_second_usd"), positive=True) * duration
    if config.get("model") == "bytedance/seedance-2.0-mini":
        sizes = {"480p": (854,480), "720p": (1280,720)}
        if request.get("resolution") not in sizes or type(duration) is not int or duration not in range(4,16):
            raise ValueError("Unsupported Seedance 2.0 Mini request")
        width, height = sizes[request["resolution"]]
        # Official output-token formula; not comparable to a per-second SKU.
        tokens = Decimal(width * height * duration * 24) / Decimal(1024)
        return tokens * _money(config.get("price_per_million_video_tokens_usd"), positive=True) / Decimal(1_000_000)
    raise ValueError("Unverified video price contract")


def check_video_model(config: dict, models: list[dict]) -> None:
    matches = [m for m in models if m.get("id") == config["model"]]
    if len(matches) != 1:
        raise ValueError("Selected video model is unavailable")
    model = matches[0]
    for field, supported in (("resolution", "supported_resolutions"), ("aspect_ratio", "supported_aspect_ratios")):
        if config[field] not in (model.get(supported) or []):
            raise ValueError(f"Video model does not support {field}")
    if (config["model"] != HEYGEN_MODEL and model.get("generate_audio") is not True
            or model.get("seed") is not True):
        raise ValueError("Video model must advertise audio and seed support")
    for shot in config.get("shots", []):
        if shot["duration_s"] not in (model.get("supported_durations") or []):
            raise ValueError("Video model does not support requested duration")
    skus = model.get("pricing_skus") or {}
    if config["model"] == HEYGEN_MODEL:
        expected = {"duration_seconds_2k", "duration_seconds_480p", "duration_seconds_768p",
                    "reference_input_images", "reference_duration_seconds_2k",
                    "reference_duration_seconds_480p", "reference_duration_seconds_768p"}
        if (set(skus) != expected or config.get("resolution") != "768p"
                or config.get("free_reference_images") != 2
                or "prompt_enhancement" not in (model.get("allowed_passthrough_parameters") or [])):
            raise BudgetError("HeyGen reference pricing/control contract changed")
        discount = _money(model.get("verified_provider_discount"))
        if discount != _money(config.get("provider_discount")) or discount >= 1:
            raise BudgetError("HeyGen provider discount changed")
        if _money(skus["reference_input_images"], positive=True) > _money(config.get("reference_image_price_usd"), positive=True):
            raise BudgetError("HeyGen reference image price increased")
        live_rate = _money(skus["reference_duration_seconds_768p"], positive=True)
        configured_rate = _money(config.get("reference_price_per_second_usd"), positive=True)
    elif config["model"] == "alibaba/wan-2.7":
        if set(skus) != {"duration_seconds"}:
            raise BudgetError("Video pricing SKU contract changed; verify before submission")
        live_rate = _money(skus["duration_seconds"], positive=True)
        configured_rate = _money(config["price_per_second_usd"], positive=True)
    elif config["model"] == "bytedance/seedance-2.0-mini":
        if "video_tokens" not in skus or set(skus) - {"video_tokens", "video_tokens_without_audio", "video_tokens_with_video_input"}:
            raise BudgetError("Seedance pricing SKU contract changed; verify before submission")
        live_rate = _money(skus["video_tokens"], positive=True) * Decimal(1_000_000)
        configured_rate = _money(config["price_per_million_video_tokens_usd"], positive=True)
    else:
        raise ValueError("Unverified video price contract")
    if live_rate > configured_rate:
        raise BudgetError("Advertised video price exceeds the configured estimate")


class _ContentRedirect(HTTPRedirectHandler):
    """CDN redirects may download bytes but must not receive the API key."""
    def __init__(self, on_redirect=None):
        super().__init__()
        self.on_redirect = on_redirect

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parts = urlsplit(newurl)
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
            raise OpenRouterError("Unsafe video content redirect")
        result = super().redirect_request(req, fp, code, msg, headers, newurl)
        if result is not None and (parts.hostname != "openrouter.ai" or parts.port not in (None, 443)):
            result.remove_header("Authorization")
        if result is not None and self.on_redirect is not None:
            self.on_redirect()
        return result


class OpenRouterVideoClient:
    def __init__(self, config, *, api_key=None, allow_paid=False, max_cost_usd=None,
                 opener=None, poll_interval_s=8, job_timeout_s=900):
        self.config = deepcopy(config)
        self._key = api_key if api_key is not None else os.environ.get("OPENROUTER_API_KEY", "")
        self._allow_paid = allow_paid is True
        self._limit = _money(max_cost_usd, positive=True)
        self._spent = Decimal(0)
        self._unknown = False
        self._resume_only = False
        self.post_attempts = 0
        self._api = opener or build_opener(_NoRedirect()).open
        self._content = opener
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

    def _safe_provider_error(self, value, _depth=0):
        """Keep actionable error fields, excluding credentials and signed URLs."""
        if _depth >= 6:
            return "[truncated]"
        if value is None or type(value) in (bool, int):
            return value
        if isinstance(value, dict):
            result = {}
            for key in ("code", "message", "type", "error", "details", "metadata", "provider_name", "raw"):
                if key not in value:
                    continue
                item = value[key]
                if key == "raw" and isinstance(item, str):
                    try:
                        parsed = _strict_json(item)
                        if isinstance(parsed, (dict, list)):
                            item = parsed
                    except (ValueError, RecursionError):
                        pass
                result[key] = self._safe_provider_error(item, _depth + 1)
            return result
        if isinstance(value, list):
            return [self._safe_provider_error(item, _depth + 1) for item in value[:5]]
        text = str(value)
        if self._key:
            text = text.replace(self._key, "[redacted-key]")
        text = re.sub(r"https?://[^\s\"<>]+", "[redacted-url]", text, flags=re.IGNORECASE)
        text = re.sub(r"data:[^\s\"<>]+", "[redacted-data]", text, flags=re.IGNORECASE)
        text = re.sub(r"sk-[A-Za-z0-9_-]+", "[redacted-key]", text)
        text = re.sub(r"(?i)bearer\s+[A-Za-z0-9._~+/-]+=*", "Bearer [redacted-key]", text)
        return text[:2000]

    def _record_error(self, directory, receipt, phase, diagnostic):
        details = {key: diagnostic[key] for key in ("kind", "http_status", "error_type", "reason")
                   if key in diagnostic}
        details["phase"] = phase
        if "request_id" in diagnostic:
            details["request_id"] = self._safe_provider_error(diagnostic["request_id"])
        receipt["last_error"] = details
        if "provider_error" in diagnostic:
            receipt["provider_error"] = self._safe_provider_error(diagnostic["provider_error"])
        self._save(directory, receipt)

    def _api_json(self, directory, receipt, request, phase):
        try:
            return _json_request(self._api, request)
        except _VideoAPIError as exc:
            self._record_error(directory, receipt, phase, exc.diagnostic)
            raise

    def generate(self, request: dict, *, out_dir: str) -> dict:
        if not self._allow_paid:
            raise BudgetError("Paid video generation is disabled")
        if self._unknown or self._resume_only:
            raise BudgetError("Reconcile earlier charges before any further generation")
        if not self._key or not self._key.strip():
            raise ValueError("Set OPENROUTER_API_KEY in the process environment")
        controls = video_request_controls(self.config.get("model"))
        allowed = {"model", "prompt", "duration", "resolution", "aspect_ratio", "seed", "input_references"} | set(controls)
        if set(request) != allowed or not isinstance(request["prompt"], str) or not request["prompt"].strip():
            raise ValueError("Unexpected video request shape")
        if any(request.get(k) != v for k, v in controls.items()) or type(request["seed"]) is not int or not request["input_references"]:
            raise ValueError("Native audio, seed and references are required")
        estimate = estimate_video_cost(self.config, request)
        if self._spent + estimate > self._limit:
            raise BudgetError("Video estimate exceeds remaining local budget")
        directory = Path(out_dir).resolve()
        directory.mkdir(parents=True, exist_ok=False)
        receipt = {"schema_version": "1.1", "model": request["model"], "status": "submitting",
                   "job_id": None, "estimated_cost_usd": str(estimate), "provider_cost_usd": None,
                   "post_attempts": 1, "poll_attempts": 0, "download_attempts": 0,
                   "download_redirect_attempts": 0, "video_get_calls": 0, "real_http_calls": 1,
                   "http_counts_complete": True, "video_path": None,
                   "request_sha256": json_hash(request)}
        self._save(directory, receipt)
        # After any POST attempt, only a validated terminal usage record can
        # reconcile the charge. A lost submit response must not trigger retry.
        self._unknown = True
        try:
            self.post_attempts += 1
            data = self._api_json(directory, receipt, self._request(payload=request), "submit")
            job_id = data.get("id")
            if not isinstance(job_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,160}", job_id):
                self._record_error(directory, receipt, "submit", {
                    "kind": "invalid_response", "reason": "missing_or_invalid_job_id",
                    **({"provider_error": data["error"]} if "error" in data else {})})
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
        def count(field):
            # Missing legacy counters remain unknown across GET-only recovery.
            value = receipt.get(field)
            receipt[field] = value + 1 if type(value) is int and value >= 0 else None
            observed = "observed_" + field
            receipt[observed] = receipt.get(observed, 0) + 1
            get_fields = ("poll_attempts", "download_attempts", "download_redirect_attempts")
            get_complete = all(type(receipt.get(k)) is int and receipt[k] >= 0 for k in get_fields)
            complete = get_complete and type(receipt.get("post_attempts")) is int and receipt["post_attempts"] >= 0
            receipt["http_counts_complete"] = complete
            receipt["video_get_calls"] = sum(receipt[k] for k in get_fields) if get_complete else None
            receipt["real_http_calls"] = receipt["post_attempts"] + receipt["video_get_calls"] if complete else None
            self._save(directory, receipt)

        deadline = monotonic() + self._job_timeout
        data = first
        while True:
            if data is None or data.get("status") not in TERMINAL:
                if monotonic() >= deadline:
                    receipt["status"] = "polling_timeout"
                    self._save(directory, receipt)
                    raise OpenRouterError("Video polling timed out; the job may still charge. Resume this job, do not resubmit")
                count("poll_attempts")
                try:
                    data = self._api_json(directory, receipt, self._request("/" + receipt["job_id"]), "poll")
                except OpenRouterError:
                    receipt["status"] = "polling_interrupted"
                    self._save(directory, receipt)
                    raise
            if data.get("status") not in STATUSES or data.get("id", receipt["job_id"]) != receipt["job_id"]:
                receipt["status"] = "invalid_poll_response"
                self._record_error(directory, receipt, "poll", {
                    "kind": "invalid_response", "reason": "invalid_status_or_job_id",
                    **({"provider_error": data["error"]} if "error" in data else {})})
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
            content = self._content or build_opener(_ContentRedirect(lambda: count("download_redirect_attempts"))).open
            count("download_attempts")
            with content(self._request("/" + receipt["job_id"] + "/content?index=0"), timeout=60) as response:
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
        except (HTTPError, URLError, OSError, OpenRouterError) as exc:
            receipt["status"] = "download_interrupted"
            diagnostic = (_http_error(exc).diagnostic if isinstance(exc, HTTPError) else
                          {"kind": "transport" if isinstance(exc, OSError) else "invalid_response",
                           "error_type": type(exc).__name__})
            self._record_error(directory, receipt, "download", diagnostic)
            raise OpenRouterError("Video download interrupted; resume the saved job without POST") from None
        receipt["status"] = "downloaded"
        receipt["video_path"] = str(target)
        self._save(directory, receipt)
        return receipt
