"""Shared LLM interface, offline FakeClient and explicit OpenRouter calls."""

from abc import ABC, abstractmethod
from collections import deque
from copy import deepcopy
from contextlib import contextmanager
from contextvars import ContextVar
import json
import hashlib
import math
import os
from decimal import Decimal
from pathlib import Path
from threading import Lock
from time import monotonic
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import uuid4


class LLMClient(ABC):
    """Common interface for all MoodCut LLM clients."""

    @abstractmethod
    def complete_json(
        self,
        *,
        stage: str,
        system: str,
        user: str,
        max_output_tokens: int,
    ) -> dict:
        """Return a JSON-compatible dictionary."""
        raise NotImplementedError


class FakeClient(LLMClient):
    """Return predefined responses without using the network."""

    def __init__(self, responses: list[dict]):
        if not isinstance(responses, list):
            raise TypeError("responses must be a list")

        self._responses = deque(deepcopy(responses))
        self.calls = []

    def complete_json(
        self,
        *,
        stage: str,
        system: str,
        user: str,
        max_output_tokens: int,
    ) -> dict:

        if not isinstance(stage, str) or not stage.strip():
            raise ValueError("stage must be a non-empty string")

        if not isinstance(system, str):
            raise TypeError("system must be a string")

        if not isinstance(user, str):
            raise TypeError("user must be a string")

        if type(max_output_tokens) is not int or max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be a positive integer")

        self.calls.append({
            "stage": stage,
            "system": system,
            "user": user,
            "max_output_tokens": max_output_tokens,
        })

        if not self._responses:
            raise RuntimeError(
                f"FakeClient response queue exhausted at stage: {stage}"
            )

        response = self._responses.popleft()

        if not isinstance(response, dict):
            raise TypeError("FakeClient response must be a dictionary")

        try:
            json.dumps(response, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "FakeClient response must be valid JSON"
            ) from exc

        return deepcopy(response)

    @property
    def remaining(self) -> int:
        """Number of responses remaining in the queue."""
        return len(self._responses)


class OpenRouterError(RuntimeError):
    """A sanitized provider/transport/protocol failure; never retried here."""


class BudgetError(RuntimeError):
    """Local estimated budget is insufficient or a prior charge is unknown."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Keep the credential on the configured origin; a redirect is an error.
        return None


class _StrictJSONError(ValueError):
    def __init__(self, kind, message):
        super().__init__(message)
        self.kind = kind


def _strict_json(text):
    def object_pairs(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise _StrictJSONError("duplicate_key", "duplicate JSON key")
            obj[key] = value
        return obj

    def reject_constant(value):
        raise _StrictJSONError("non_finite", "non-finite JSON value")

    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            reject_constant(value)
        return number

    return json.loads(text, object_pairs_hook=object_pairs, parse_constant=reject_constant,
                      parse_float=finite_float)


_RESPONSE_ROOT = ContextVar("moodcut_text_response_root", default=None)


@contextmanager
def capture_text_responses(directory):
    """Bind a private artifact root for this execution context, including routed roles."""
    token = _RESPONSE_ROOT.set(Path(directory).resolve())
    try:
        yield
    finally:
        _RESPONSE_ROOT.reset(token)


def _json_diagnostic(record, layer, exc):
    if isinstance(exc, json.JSONDecodeError):
        detail = {"kind": "syntax_error", "line": exc.lineno, "column": exc.colno, "position": exc.pos}
    elif isinstance(exc, _StrictJSONError):
        detail = {"kind": exc.kind}
    elif isinstance(exc, UnicodeDecodeError):
        detail = {"kind": "invalid_utf8", "byte_offset": exc.start}
    elif isinstance(exc, RecursionError):
        detail = {"kind": "excessive_nesting"}
    else:
        detail = {"kind": "parser_error"}
    record["parse_error"] = {"layer": layer, **detail}
    return OpenRouterError(f"OpenRouter {layer} JSON error: {detail['kind']}; no retry performed")


def _number(value, field, *, positive=False):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{field} must be a finite number")
    if value < 0 or (positive and value == 0):
        raise ValueError(f"{field} must be {'positive' if positive else 'nonnegative'}")
    return Decimal(str(value))


class OpenRouterClient(LLMClient):
    """Stateless JSON calls with separate usage records and a local budget.

    max_cost_usd is an estimated, per-instance budget, not an account-wide cap.
    Input reservation uses UTF-8 bytes + 64 framing tokens, not a model tokenizer.
    A response without a known charge disables further calls on this instance.
    Set a server-side OpenRouter key limit for the team's actual shared ceiling.
    Constructing/importing a client never accesses the network.
    """

    ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
    MAX_RESPONSE_BYTES = 8 * 1024 * 1024

    def __init__(self, *, api_key, model, input_price_per_million,
                 output_price_per_million, allow_paid=False, max_cost_usd=None,
                 timeout_s=60, temperature=0, reasoning_enabled=None, response_dir=None):
        if not isinstance(api_key, str) or not api_key.strip():
            raise ValueError("OPENROUTER_API_KEY is required")
        if any(c in api_key for c in "\r\n"):
            raise ValueError("OPENROUTER_API_KEY contains invalid characters")
        if not isinstance(model, str) or not model.strip() or model != model.strip():
            raise ValueError("model must be an explicit OpenRouter model ID")
        if type(allow_paid) is not bool:
            raise ValueError("allow_paid must be a boolean")
        self.model = model
        self._api_key = api_key.strip()
        self._input_price = _number(input_price_per_million, "input_price_per_million")
        self._output_price = _number(output_price_per_million, "output_price_per_million")
        self._max_cost = _number(max_cost_usd, "max_cost_usd", positive=True)
        self.timeout_s = float(_number(timeout_s, "timeout_s", positive=True))
        self.temperature = float(_number(temperature, "temperature"))
        if reasoning_enabled is not None and type(reasoning_enabled) is not bool:
            raise ValueError("reasoning_enabled must be a boolean or None")
        self.reasoning_enabled = reasoning_enabled
        if self.temperature > 2:
            raise ValueError("temperature must be in [0, 2]")
        self.allow_paid = allow_paid
        self.calls = []
        self._spent = Decimal(0)
        self._unknown_charge = False
        self._lock = Lock()
        self._response_root = Path(response_dir).resolve() if response_dir is not None else None

    def _redact_response(self, data):
        # Never retain request headers. Defensively remove an echoed credential too.
        for secret in (self._api_key.encode("utf-8"), json.dumps(self._api_key)[1:-1].encode("utf-8")):
            data = data.replace(secret, b"[REDACTED]")
        return data

    def _retain_body(self, raw, record):
        root = _RESPONSE_ROOT.get() or self._response_root
        if root is None:
            return
        relative = Path("PRIVATE") / "text-responses" / uuid4().hex
        saved = self._redact_response(raw)
        try:
            directory = root / relative
            directory.mkdir(parents=True, exist_ok=False, mode=0o700)
            with (directory / "response.bin").open("xb") as stream:
                stream.write(saved)
            record["response_artifact"] = {
                "body_path": (relative / "response.bin").as_posix(),
                "body_sha256": hashlib.sha256(saved).hexdigest(), "body_bytes": len(saved),
                "complete": len(raw) <= self.MAX_RESPONSE_BYTES, "credential_redacted": saved != raw}
        except OSError:
            record["retention_error"] = "body_write_failed"

    def _retain_content(self, content, record):
        artifact = record["response_artifact"]
        if artifact is None:
            return
        root = _RESPONSE_ROOT.get() or self._response_root
        raw = content.encode("utf-8", errors="surrogatepass")
        saved = self._redact_response(raw)
        path = Path(artifact["body_path"]).with_name("content.txt")
        try:
            with (root / path).open("xb") as stream:
                stream.write(saved)
            artifact.update(content_path=path.as_posix(), content_sha256=hashlib.sha256(saved).hexdigest(),
                            content_bytes=len(saved), content_encoding="utf-8/surrogatepass",
                            content_credential_redacted=saved != raw)
        except OSError:
            record["retention_error"] = "content_write_failed"

    def _retain_diagnostic(self, record):
        artifact = record["response_artifact"]
        if artifact is None:
            return
        root = _RESPONSE_ROOT.get() or self._response_root
        path = root / Path(artifact["body_path"]).with_name("diagnostic.json")
        try:
            with path.open("x", encoding="utf-8") as stream:
                json.dump(record, stream, ensure_ascii=True, allow_nan=False, indent=2)
        except OSError:
            record["retention_error"] = "diagnostic_write_failed"
            if record["status"] == "success":
                record["status"] = "retention_failed"
                record["error"] = "Text response diagnostic could not be saved; no retry performed"
                raise OpenRouterError(record["error"]) from None

    @classmethod
    def from_env(cls, config_path="configs/model.json", *, allow_paid=False,
                 max_cost_usd=None, environ=None):
        """Load public configuration and the process key; do not read .env files."""
        config = _strict_json(Path(config_path).read_text(encoding="utf-8"))
        if not isinstance(config, dict):
            raise ValueError("model configuration must be a JSON object")
        environment = os.environ if environ is None else environ
        return cls(api_key=environment.get("OPENROUTER_API_KEY"),
                   model=config.get("model"),
                   input_price_per_million=config.get("input_price_per_million"),
                   output_price_per_million=config.get("output_price_per_million"),
                   timeout_s=config.get("timeout_s", 60),
                   temperature=config.get("temperature", 0),
                   reasoning_enabled=config.get("reasoning_enabled"),
                   allow_paid=allow_paid, max_cost_usd=max_cost_usd)

    @property
    def spent_usd(self):
        """Actual summed provider cost, or None if any attempt's cost is unknown."""
        return None if self._unknown_charge else float(self._spent)

    def complete_json(self, *, stage, system, user, max_output_tokens):
        if not self.allow_paid:
            raise PermissionError("Live OpenRouter calls require explicit allow_paid=True")
        if not isinstance(stage, str) or not stage.strip():
            raise ValueError("stage must be a non-empty string")
        if not isinstance(system, str) or not isinstance(user, str):
            raise TypeError("system and user must be strings")
        if type(max_output_tokens) is not int or max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be a positive integer")
        # Serializes reservations and responses when a single client is shared.
        with self._lock:
            return self._complete(stage, system, user, max_output_tokens)

    def _reservation(self, system, user, max_output_tokens):
        estimated_input = len(system.encode("utf-8")) + len(user.encode("utf-8")) + 64
        return estimated_input, (estimated_input * self._input_price +
                max_output_tokens * self._output_price) / Decimal(1_000_000)

    def _complete(self, stage, system, user, max_output_tokens):
        if self._unknown_charge:
            raise BudgetError("Previous request cost is unknown; reconcile it before further calls")
        estimated_input, reservation = self._reservation(system, user, max_output_tokens)
        if self._spent + reservation > self._max_cost:
            raise BudgetError("Estimated request cost exceeds the remaining client budget")
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "stream": False, "max_tokens": max_output_tokens,
            "temperature": self.temperature,
            "response_format": {"type": "json_object"},
            "provider": {"allow_fallbacks": False, "require_parameters": True,
                         "max_price": {"prompt": float(self._input_price),
                                       "completion": float(self._output_price), "request": 0}},
        }
        if self.reasoning_enabled is not None:
            payload["reasoning"] = {"enabled": self.reasoning_enabled}
        request = Request(self.ENDPOINT, data=json.dumps(payload, allow_nan=False).encode("utf-8"),
                          headers={"Authorization": f"Bearer {self._api_key}",
                                   "Content-Type": "application/json",
                                   "X-OpenRouter-Title": "MoodCut"}, method="POST")
        record = {"stage": stage, "model_id": self.model, "response_model": None,
                  "generation_id": None, "max_output_tokens": max_output_tokens,
                  "estimated_input_tokens": estimated_input,
                  "reserved_cost_usd": float(reservation), "input_tokens": None,
                  "output_tokens": None, "estimated_cost_usd": None,
                  "provider_cost_usd": None, "status": "request_failed",
                  "http_status": None, "elapsed_s": None, "parse_error": None,
                  "response_artifact": None, "retention_error": None}
        self.calls.append(record)
        start = monotonic()
        envelope = None
        try:
            try:
                with build_opener(_NoRedirect()).open(request, timeout=self.timeout_s) as response:
                    raw = response.read(self.MAX_RESPONSE_BYTES + 1)
            except HTTPError as exc:
                record["http_status"] = exc.code
                try:
                    raw = exc.read(self.MAX_RESPONSE_BYTES + 1)
                    self._retain_body(raw, record)
                    if len(raw) <= self.MAX_RESPONSE_BYTES:
                        try:
                            envelope = _strict_json(raw.decode("utf-8"))
                        except (ValueError, UnicodeError, RecursionError) as error:
                            _json_diagnostic(record, "envelope", error)
                except OSError:
                    record["retention_error"] = "http_error_body_unavailable"
                finally:
                    exc.close()
                raise OpenRouterError(f"OpenRouter HTTP {exc.code}; no retry performed") from None
            self._retain_body(raw, record)  # Persist bytes before either JSON parser runs.
            if len(raw) > self.MAX_RESPONSE_BYTES:
                raise OpenRouterError("OpenRouter response exceeds the client size limit")
            record["status"] = "invalid_response"
            try:
                envelope = _strict_json(raw.decode("utf-8"))
            except (ValueError, UnicodeError, RecursionError) as exc:
                raise _json_diagnostic(record, "envelope", exc) from None
            if not isinstance(envelope, dict):
                raise _json_diagnostic(record, "envelope", _StrictJSONError("non_object", "response root is not an object"))
            if envelope.get("error") is not None:
                raise OpenRouterError("OpenRouter returned an error or invalid response envelope")
            choices = envelope.get("choices")
            if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
                raise OpenRouterError("OpenRouter returned no unique completion")
            choice = choices[0]
            message = choice.get("message")
            if isinstance(message, dict) and isinstance(message.get("content"), str):
                self._retain_content(message["content"], record)
            if choice.get("finish_reason") != "stop" or choice.get("error") is not None:
                raise OpenRouterError("OpenRouter completion was incomplete or refused")
            if (not isinstance(message, dict) or message.get("refusal")
                    or message.get("tool_calls") or not isinstance(message.get("content"), str)):
                raise OpenRouterError("OpenRouter completion has no JSON text content")
            try:
                result = _strict_json(message["content"])
                try:
                    json.dumps(result, allow_nan=False)
                except ValueError:
                    raise _StrictJSONError("non_finite", "model JSON contains a non-finite number") from None
                if not isinstance(result, dict):
                    raise _StrictJSONError("non_object", "model JSON root is not an object")
            except (ValueError, TypeError, OverflowError, RecursionError) as exc:
                raise _json_diagnostic(record, "content", exc) from None
            if record["retention_error"] is not None:
                raise OpenRouterError("Text response could not be retained; no retry performed")
            record["status"] = "success"
            return result
        except OpenRouterError as exc:
            record["error"] = str(exc)
            raise
        except Exception:
            record["error"] = "OpenRouter transport failed; no retry performed"
            raise OpenRouterError(record["error"]) from None
        finally:
            self._record_usage(envelope, record)
            record["elapsed_s"] = monotonic() - start
            self._retain_diagnostic(record)

    def _record_usage(self, envelope, record):
        if isinstance(envelope, dict):
            for source, target in (("id", "generation_id"), ("model", "response_model")):
                if isinstance(envelope.get(source), str):
                    record[target] = envelope[source]
            usage = envelope.get("usage")
            if isinstance(usage, dict):
                for source, target in (("prompt_tokens", "input_tokens"),
                                       ("completion_tokens", "output_tokens")):
                    if type(usage.get(source)) is int and usage[source] >= 0:
                        record[target] = usage[source]
                cost = usage.get("cost")
                if type(cost) in (int, float) and math.isfinite(cost) and cost >= 0:
                    record["provider_cost_usd"] = cost
                    self._spent += Decimal(str(cost))
        if record["input_tokens"] is not None and record["output_tokens"] is not None:
            record["estimated_cost_usd"] = float(
                (record["input_tokens"] * self._input_price +
                 record["output_tokens"] * self._output_price) / Decimal(1_000_000))
        if record["provider_cost_usd"] is None:
            self._unknown_charge = True


class RoleRoutedClient(LLMClient):
    """Route existing text stages with one fail-closed shared budget, no retries."""

    def __init__(self, planning_client, review_client, *, max_cost_usd):
        if (not all(isinstance(c, OpenRouterClient) for c in (planning_client, review_client))
                or planning_client is review_client or planning_client.calls or review_client.calls):
            raise ValueError("Role routing requires two fresh OpenRouter clients")
        self.planning_client, self.review_client = planning_client, review_client
        self._max_cost = _number(max_cost_usd, "max_cost_usd", positive=True)
        self.calls = []
        self._stop_reason = None
        self._lock = Lock()

    @classmethod
    def from_env(cls, config_path, *, allow_paid=False, max_cost_usd=None, environ=None):
        config = _strict_json(Path(config_path).read_text(encoding="utf-8"))
        if not isinstance(config, dict) or set(config) != {"planning", "review"}:
            raise ValueError("Role configuration requires exactly planning and review")
        environment = os.environ if environ is None else environ
        clients = [OpenRouterClient(api_key=environment.get("OPENROUTER_API_KEY"),
                    allow_paid=allow_paid, max_cost_usd=max_cost_usd, **config[role])
                   for role in ("planning", "review")]
        return cls(*clients, max_cost_usd=max_cost_usd)

    @staticmethod
    def policy_id(roles):
        text = json.dumps(roles, sort_keys=True, separators=(",", ":"), allow_nan=False)
        return "role-policy/" + hashlib.sha256(text.encode("utf-8")).hexdigest()

    @property
    def model_settings(self):
        roles = {role: {"model_id": c.model, "temperature": c.temperature,
                        "reasoning_enabled": c.reasoning_enabled}
                 for role, c in (("planning", self.planning_client), ("review", self.review_client))}
        return {"model_id": self.policy_id(roles), "roles": roles}

    @property
    def model(self):
        return self.model_settings["model_id"]

    @property
    def spent_usd(self):
        costs = [self.planning_client.spent_usd, self.review_client.spent_usd]
        return None if any(c is None for c in costs) else float(sum(Decimal(str(c)) for c in costs))

    @property
    def stopped(self):
        return self._stop_reason is not None

    def stop(self, reason):
        self._stop_reason = str(reason)

    @staticmethod
    def role_for_stage(stage):
        if stage in ("director", "scene", "shot", "actor_revise"):
            return "planning"
        if stage in ("critique", "revise", "verify", "actor_critique", "actor_confirm"):
            return "review"
        raise ValueError("Unknown text stage; no model selected")

    def complete_json(self, *, stage, system, user, max_output_tokens):
        with self._lock:
            if self.stopped:
                raise BudgetError("Text pipeline stopped: " + self._stop_reason)
            role = self.role_for_stage(stage)
            client = self.planning_client if role == "planning" else self.review_client
            if (not isinstance(system, str) or not isinstance(user, str)
                    or type(max_output_tokens) is not int or max_output_tokens <= 0):
                raise ValueError("Invalid text request")
            cost = self.spent_usd
            _, reservation = client._reservation(system, user, max_output_tokens)
            if cost is None or Decimal(str(cost)) + reservation > self._max_cost:
                self.stop("Shared text cost is unknown or its budget is exhausted")
                raise BudgetError(self._stop_reason)
            before = len(client.calls)
            try:
                result = client.complete_json(stage=stage, system=system, user=user,
                                              max_output_tokens=max_output_tokens)
                cost = self.spent_usd
                if cost is None or Decimal(str(cost)) > self._max_cost:
                    raise BudgetError("Returned text cost is unknown or exceeds the shared budget")
                return result
            except Exception:
                self.stop("Earlier text request failed or has unresolved charges")
                raise
            finally:
                self.calls.extend(deepcopy(client.calls[before:]))
