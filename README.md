# UZEX deals agent

## LLM configuration

The agent talks to LLM vendors only through `app/llm/`. The chain of models is tried in
order; each entry is retried `RETRIES_PER_MODEL` times (default 2) on 429 / 503 / 5xx /
timeouts, then the next entry is used. Auth or invalid-request errors skip the entry at
once. Every request has a 40 s timeout.

Set the chain in `.env` as comma-separated `provider:model` entries:

```
LLM_MODELS=gemini:gemini-3.5-flash,anthropic:claude-sonnet-5-5,openai:gpt-5-mini
GEMINI_API_KEY=...
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
```

Supported providers: `gemini` (google-genai), `anthropic` (Claude Messages API) and
`openai` (chat completions; set `OPENAI_BASE_URL` to use Groq, Ollama or any other
OpenAI-compatible endpoint). Entries whose API key is empty are skipped with a warning,
so you can list fallbacks before you have the keys. A bare model name means `gemini`.
If `LLM_MODELS` is unset the legacy `GEMINI_MODEL` list is used.

Tests for the chain logic run offline: `python -X utf8 -m pytest tests/test_llm.py -q`.
