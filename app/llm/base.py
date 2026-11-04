"""Shared types for the LLM layer: response DTO, provider protocol, error classification."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

# Per-request timeout so one hung vendor cannot eat the whole answer budget.
REQUEST_TIMEOUT_SEC = 40.0

# 4xx statuses that still make sense to retry / move on from (quota, timeout).
RETRYABLE_4XX = {408, 409, 425, 429}


@dataclass(frozen=True)
class LlmResponse:
    text: str
    input_tokens: int
    output_tokens: int


class ProviderSkip(Exception):
    """Raised by an adapter when the entry cannot be used at all (missing SDK, bad config)."""


class Provider(Protocol):
    """One vendor adapter. Must raise on failure; the chain decides what to do next."""

    def complete(
        self,
        model: str,
        system: str,
        user: str,
        *,
        temperature: float = 0.0,
        json_mode: bool = False,
    ) -> LlmResponse: ...


def _status_of(exc: BaseException) -> int | None:
    """Best-effort HTTP status from vendor exceptions (anthropic/openai: status_code, genai: code)."""
    for attr in ("status_code", "code", "status"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    return None


def is_retryable(exc: BaseException) -> bool:
    """True when the next attempt / next model may succeed (429, 5xx, timeouts, unknown).

    False for auth / invalid-request errors (other 4xx) and ProviderSkip: retrying
    the same entry is pointless, move straight to the next one.
    """
    if isinstance(exc, ProviderSkip):
        return False
    status = _status_of(exc)
    if status is None:
        return True
    if status >= 500 or status in RETRYABLE_4XX:
        return True
    return status < 400
