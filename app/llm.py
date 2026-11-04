"""LLM provider wrapper. Only this file knows which vendor is used."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger(__name__)

RETRIES_PER_MODEL = 2
RETRY_SLEEP_SEC = 1.0
DEFAULT_MODELS = "gemini-3.5-flash,gemini-flash-latest,gemini-3.8-flash,gemini-2.5-flash"


@dataclass(frozen=True)
class LlmResponse:
    text: str
    input_tokens: int
    output_tokens: int


class Llm:
    """Thin client over Gemini. Swap this class to change vendor."""

    def __init__(self, model: str | None = None) -> None:
        from google import genai

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set (see .env.example)")
        self._client = genai.Client(api_key=api_key)
        chain = model or os.environ.get("GEMINI_MODEL", DEFAULT_MODELS)
        self.models = [m.strip() for m in chain.split(",") if m.strip()]
        self.model = self.models[0]

    def complete(self, system: str, user: str, *, temperature: float = 0.0, json_mode: bool = False) -> LlmResponse:
        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
            response_mime_type="application/json" if json_mode else "text/plain",
        )
        last_error: Exception | None = None
        for model in self.models:
            for attempt in range(1, RETRIES_PER_MODEL + 1):
                try:
                    resp = self._client.models.generate_content(model=model, contents=user, config=config)
                    usage = resp.usage_metadata
                    if model != self.model:
                        log.warning("answered by fallback model %s", model)
                    return LlmResponse(
                        text=resp.text or "",
                        input_tokens=getattr(usage, "prompt_token_count", 0) or 0,
                        output_tokens=getattr(usage, "candidates_token_count", 0) or 0,
                    )
                except Exception as exc:  # noqa: BLE001 - vendor raises many types
                    last_error = exc
                    log.warning("LLM %s attempt %d failed: %s", model, attempt, str(exc)[:200])
                    time.sleep(RETRY_SLEEP_SEC * attempt)
        raise RuntimeError(f"LLM failed on all models: {last_error}")
