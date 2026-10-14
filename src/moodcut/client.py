"""Shared LLM interface and offline FakeClient."""

from abc import ABC, abstractmethod
from collections import deque
from copy import deepcopy
import json


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