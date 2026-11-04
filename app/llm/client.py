"""Fallback chain over provider adapters. Config via LLM_MODELS (provider:model,...) or legacy GEMINI_MODEL."""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable, Mapping
from typing import NamedTuple

from dotenv import load_dotenv

from app.llm.base import LlmResponse, Provider, is_retryable
from app.llm.providers import AnthropicProvider, GeminiProvider, OpenAIProvider

load_dotenv()
log = logging.getLogger(__name__)

RETRIES_PER_MODEL = int(os.environ.get("RETRIES_PER_MODEL", "2"))
RETRY_SLEEP_SEC = 1.0
DEFAULT_PROVIDER = "gemini"
DEFAULT_MODELS = "gemini-3.5-flash,gemini-flash-latest,gemini-3.8-flash,gemini-2.5-flash"

KEY_ENV = {"gemini": "GEMINI_API_KEY", "anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}

ProviderFactory = Callable[[str, Mapping[str, str]], Provider]
PROVIDER_FACTORIES: dict[str, ProviderFactory] = {
    "gemini": lambda key, env: GeminiProvider(key),
    "anthropic": lambda key, env: AnthropicProvider(key),
    "openai": lambda key, env: OpenAIProvider(key, env.get("OPENAI_BASE_URL")),
}


class LlmDeadline(RuntimeError):
    """Raised when the caller's time budget ran out before an attempt could start."""


class ChainEntry(NamedTuple):
    provider: str
    model: str

    def __str__(self) -> str:
        return f"{self.provider}:{self.model}"


def parse_chain(spec: str) -> list[ChainEntry]:
    """'gemini:a,anthropic:b,c' -> entries; a bare name means gemini."""
    entries: list[ChainEntry] = []
    for raw in spec.split(","):
        item = raw.strip()
        if not item:
            continue
        provider, sep, model = item.partition(":")
        if not sep:
            provider, model = DEFAULT_PROVIDER, item
        provider = provider.strip().lower()
        if provider not in KEY_ENV:
            raise ValueError(f"unknown provider '{provider}' in LLM_MODELS entry '{item}' (known: {sorted(KEY_ENV)})")
        entries.append(ChainEntry(provider, model.strip()))
    return entries


class Llm:
    """Public LLM client: same interface as before, now with a cross-vendor fallback chain."""

    def __init__(
        self,
        model: str | None = None,
        *,
        env: Mapping[str, str] | None = None,
        providers: Mapping[str, Provider] | None = None,
    ) -> None:
        env = os.environ if env is None else env
        spec = model or env.get("LLM_MODELS") or env.get("GEMINI_MODEL") or DEFAULT_MODELS
        self._entries: list[ChainEntry] = []
        self._providers: dict[str, Provider] = dict(providers or {})
        skipped: set[str] = set()
        for entry in parse_chain(spec):
            if self._ensure_provider(entry.provider, env):
                self._entries.append(entry)
            elif entry.provider not in skipped:
                skipped.add(entry.provider)
                log.warning("skipping %s models: %s is not set", entry.provider, KEY_ENV[entry.provider])
        if not self._entries:
            raise RuntimeError(
                f"no usable LLM in chain '{spec}': set the API key for at least one provider "
                f"({', '.join(KEY_ENV.values())}), see .env.example"
            )
        self.models = [str(e) for e in self._entries]
        self.model = self.models[0]

    def _ensure_provider(self, name: str, env: Mapping[str, str]) -> bool:
        if not env.get(KEY_ENV[name]):
            return False
        if name not in self._providers:
            self._providers[name] = PROVIDER_FACTORIES[name](env[KEY_ENV[name]], env)
        return True

    def complete(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.0,
        json_mode: bool = False,
        deadline: float | None = None,
    ) -> LlmResponse:
        """`deadline` is a time.monotonic() value: no new attempt is started after it."""
        last_error: Exception | None = None
        for entry in self._entries:
            provider = self._providers[entry.provider]
            for attempt in range(1, RETRIES_PER_MODEL + 1):
                if deadline is not None and time.monotonic() > deadline:
                    raise LlmDeadline(f"LLM budget exhausted before {entry} attempt {attempt}: {last_error}")
                try:
                    resp = provider.complete(
                        entry.model, system, user, temperature=temperature, json_mode=json_mode
                    )
                except Exception as exc:  # noqa: BLE001 - vendors raise many types
                    last_error = exc
                    log.warning("LLM %s attempt %d failed: %s", entry, attempt, str(exc)[:200])
                    if not is_retryable(exc):
                        break
                    time.sleep(RETRY_SLEEP_SEC * attempt)
                    continue
                if str(entry) != self.model:
                    log.warning("answered by fallback model %s", entry)
                return resp
        raise RuntimeError(f"LLM failed on all models ({', '.join(self.models)}): {last_error}")
