"""Offline tests for the vendor-agnostic LLM layer (fake providers, no network)."""

from __future__ import annotations

import pytest

import app.llm.client as client_mod
from app.llm import ChainEntry, Llm, LlmResponse, parse_chain
from app.llm.base import ProviderSkip, is_retryable
from app.llm.providers import strip_fences


class FakeProvider:
    """Records calls; raises the given exception for named models."""

    def __init__(self, failures: dict[str, Exception] | None = None) -> None:
        self.failures = failures or {}
        self.calls: list[tuple[str, str, str, float, bool]] = []

    def complete(self, model, system, user, *, temperature=0.0, json_mode=False) -> LlmResponse:
        self.calls.append((model, system, user, temperature, json_mode))
        if model in self.failures:
            raise self.failures[model]
        return LlmResponse(text=f"answer from {model}", input_tokens=1, output_tokens=2)


class StatusError(Exception):
    def __init__(self, status_code: int) -> None:
        super().__init__(f"http {status_code}")
        self.status_code = status_code


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(client_mod, "RETRY_SLEEP_SEC", 0.0)


def _env(**kw: str) -> dict[str, str]:
    return dict(kw)


# ---------- chain parsing ----------

def test_parse_chain_with_providers() -> None:
    assert parse_chain("gemini:gemini-3.5-flash, anthropic:claude-sonnet-5-5 ,openai:gpt-5-mini") == [
        ChainEntry("gemini", "gemini-3.5-flash"),
        ChainEntry("anthropic", "claude-sonnet-5-5"),
        ChainEntry("openai", "gpt-5-mini"),
    ]


def test_parse_chain_bare_names_default_to_gemini() -> None:
    assert parse_chain("gemini-3.5-flash,gemini-2.5-flash") == [
        ChainEntry("gemini", "gemini-3.5-flash"),
        ChainEntry("gemini", "gemini-2.5-flash"),
    ]


def test_parse_chain_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError, match="unknown provider"):
        parse_chain("foo:bar")


def test_llm_models_falls_back_to_gemini_model_env() -> None:
    fake = FakeProvider()
    llm = Llm(env=_env(GEMINI_MODEL="m1,m2", GEMINI_API_KEY="k"), providers={"gemini": fake})
    assert llm.models == ["gemini:m1", "gemini:m2"]
    assert llm.model == "gemini:m1"


def test_llm_models_prefers_llm_models_env() -> None:
    fake = FakeProvider()
    llm = Llm(
        env=_env(LLM_MODELS="openai:gpt-5-mini", GEMINI_MODEL="m1", GEMINI_API_KEY="k", OPENAI_API_KEY="k"),
        providers={"gemini": fake, "openai": fake},
    )
    assert llm.models == ["openai:gpt-5-mini"]


# ---------- key handling ----------

def test_entries_without_key_are_skipped() -> None:
    fake = FakeProvider()
    llm = Llm(
        env=_env(LLM_MODELS="anthropic:claude-x,gemini:g", GEMINI_API_KEY="k"),
        providers={"gemini": fake, "anthropic": fake},
    )
    assert llm.models == ["gemini:g"]
    assert llm.complete("s", "u").text == "answer from g"


def test_empty_chain_raises_clear_error() -> None:
    with pytest.raises(RuntimeError, match="no usable LLM"):
        Llm(env=_env(LLM_MODELS="anthropic:claude-x"), providers={"anthropic": FakeProvider()})


# ---------- fallback and retries ----------

def test_falls_back_to_next_entry_on_retryable_error() -> None:
    fake = FakeProvider(failures={"a": StatusError(503)})
    llm = Llm(env=_env(LLM_MODELS="gemini:a,gemini:b", GEMINI_API_KEY="k"), providers={"gemini": fake})
    resp = llm.complete("sys", "usr", temperature=0.3, json_mode=True)
    assert resp.text == "answer from b"
    models = [c[0] for c in fake.calls]
    assert models == ["a"] * client_mod.RETRIES_PER_MODEL + ["b"]
    assert fake.calls[-1] == ("b", "sys", "usr", 0.3, True)
    assert llm.model == "gemini:a"  # primary name unchanged for logging


def test_falls_back_across_providers() -> None:
    gem = FakeProvider(failures={"g": StatusError(429)})
    ant = FakeProvider()
    llm = Llm(
        env=_env(LLM_MODELS="gemini:g,anthropic:c", GEMINI_API_KEY="k", ANTHROPIC_API_KEY="k"),
        providers={"gemini": gem, "anthropic": ant},
    )
    assert llm.complete("s", "u").text == "answer from c"
    assert len(ant.calls) == 1


def test_non_retryable_error_skips_entry_immediately() -> None:
    fake = FakeProvider(failures={"a": StatusError(401), "b": ProviderSkip("no sdk")})
    llm = Llm(env=_env(LLM_MODELS="gemini:a,gemini:b,gemini:c", GEMINI_API_KEY="k"), providers={"gemini": fake})
    assert llm.complete("s", "u").text == "answer from c"
    assert [c[0] for c in fake.calls] == ["a", "b", "c"]


def test_all_entries_failed_raises() -> None:
    fake = FakeProvider(failures={"a": StatusError(500)})
    llm = Llm(env=_env(LLM_MODELS="gemini:a", GEMINI_API_KEY="k"), providers={"gemini": fake})
    with pytest.raises(RuntimeError, match="all models"):
        llm.complete("s", "u")


@pytest.mark.parametrize("exc,expected", [
    (StatusError(429), True),
    (StatusError(503), True),
    (StatusError(500), True),
    (TimeoutError("slow"), True),
    (RuntimeError("something odd"), True),
    (StatusError(400), False),
    (StatusError(401), False),
    (StatusError(404), False),
    (ProviderSkip("missing sdk"), False),
])
def test_is_retryable(exc: Exception, expected: bool) -> None:
    assert is_retryable(exc) is expected


# ---------- json fence stripping ----------

@pytest.mark.parametrize("raw,expected", [
    ('```json\n{"a": 1}\n```', '{"a": 1}'),
    ('```\n{"a": 1}\n```', '{"a": 1}'),
    ('  {"a": 1}  ', '{"a": 1}'),
    ('Here you go:\n```json\n{"a": 1}\n```\nDone.', '{"a": 1}'),
])
def test_strip_fences(raw: str, expected: str) -> None:
    assert strip_fences(raw) == expected
