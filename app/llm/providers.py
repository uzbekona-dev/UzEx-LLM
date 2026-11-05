"""Vendor adapters. SDKs are imported lazily so a missing package only hurts the provider that needs it."""

from __future__ import annotations

import re

from app.llm.base import REQUEST_TIMEOUT_SEC, LlmResponse, ProviderSkip

_FENCE_RE = re.compile(r"```(?:json|JSON)?\s*\n?(.*?)\n?\s*```", re.DOTALL)
JSON_ONLY_HINT = (
    "\n\nRespond with a single valid JSON object only. "
    "No prose, no markdown, no code fences."
)
ANTHROPIC_MAX_TOKENS = 4096


def strip_fences(text: str) -> str:
    """Return the JSON payload from a reply that may be wrapped in ``` fences."""
    match = _FENCE_RE.search(text)
    return (match.group(1) if match else text).strip()


def _import(module: str, pip_name: str):
    try:
        return __import__(module, fromlist=["_"])
    except ImportError as exc:
        raise ProviderSkip(f"{pip_name} SDK not installed (pip install {pip_name})") from exc


def _gemini_thinking(types, thinking):
    """'low' / 'minimal' / 'medium' / 'high' -> thinking_level; '0' / 'off' -> no thinking; None -> model default."""
    if not thinking or thinking == "default":
        return None
    if thinking in ("0", "off", "none"):
        return types.ThinkingConfig(thinking_budget=0)
    return types.ThinkingConfig(thinking_level=thinking)


class GeminiProvider:
    """Google Gemini via google-genai."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client = None

    def _get_client(self):
        if self._client is None:
            genai = _import("google.genai", "google-genai")
            http = genai.types.HttpOptions(timeout=int(REQUEST_TIMEOUT_SEC * 1000))
            self._client = genai.Client(api_key=self._api_key, http_options=http)
        return self._client

    def complete(self, model, system, user, *, temperature=0.0, json_mode=False, thinking=None) -> LlmResponse:
        client = self._get_client()
        from google.genai import types

        def make_config(think):
            return types.GenerateContentConfig(
                system_instruction=system,
                temperature=temperature,
                response_mime_type="application/json" if json_mode else "text/plain",
                thinking_config=_gemini_thinking(types, think),
            )

        try:
            resp = client.models.generate_content(model=model, contents=user, config=make_config(thinking))
        except Exception as exc:  # noqa: BLE001 - some models reject thinking settings: retry once without them
            if not thinking or "think" not in str(exc).lower():
                raise
            resp = client.models.generate_content(model=model, contents=user, config=make_config(None))
        usage = resp.usage_metadata
        return LlmResponse(
            text=resp.text or "",
            input_tokens=getattr(usage, "prompt_token_count", 0) or 0,
            output_tokens=getattr(usage, "candidates_token_count", 0) or 0,
        )


class AnthropicProvider:
    """Anthropic Claude via the Messages API."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client = None

    def _get_client(self):
        if self._client is None:
            anthropic = _import("anthropic", "anthropic")
            self._client = anthropic.Anthropic(api_key=self._api_key, timeout=REQUEST_TIMEOUT_SEC, max_retries=0)
        return self._client

    def complete(self, model, system, user, *, temperature=0.0, json_mode=False, thinking=None) -> LlmResponse:
        client = self._get_client()
        resp = client.messages.create(
            model=model,
            max_tokens=ANTHROPIC_MAX_TOKENS,
            temperature=temperature,
            system=system + (JSON_ONLY_HINT if json_mode else ""),
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(getattr(block, "text", "") for block in resp.content)
        return LlmResponse(
            text=strip_fences(text) if json_mode else text,
            input_tokens=getattr(resp.usage, "input_tokens", 0) or 0,
            output_tokens=getattr(resp.usage, "output_tokens", 0) or 0,
        )


class OpenAIProvider:
    """OpenAI chat completions; also any OpenAI-compatible endpoint via base_url (Groq, Ollama, ...)."""

    def __init__(self, api_key: str, base_url: str | None = None) -> None:
        self._api_key = api_key
        self._base_url = base_url or None
        self._client = None

    def _get_client(self):
        if self._client is None:
            openai = _import("openai", "openai")
            self._client = openai.OpenAI(
                api_key=self._api_key, base_url=self._base_url, timeout=REQUEST_TIMEOUT_SEC, max_retries=0
            )
        return self._client

    def complete(self, model, system, user, *, temperature=0.0, json_mode=False, thinking=None) -> LlmResponse:
        client = self._get_client()
        kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
        resp = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system + (JSON_ONLY_HINT if json_mode else "")},
                {"role": "user", "content": user},
            ],
            **kwargs,
        )
        text = resp.choices[0].message.content or ""
        usage = resp.usage
        return LlmResponse(
            text=strip_fences(text) if json_mode else text,
            input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            output_tokens=getattr(usage, "completion_tokens", 0) or 0,
        )
