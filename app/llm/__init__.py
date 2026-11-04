"""Vendor-agnostic LLM layer. Only this package talks to LLM vendors.

Public interface (unchanged for callers):
    from app.llm import Llm, LlmResponse
    Llm().complete(system, user, temperature=0.0, json_mode=False) -> LlmResponse
"""

from app.llm.base import LlmResponse, Provider, ProviderSkip
from app.llm.client import ChainEntry, Llm, LlmDeadline, parse_chain

__all__ = ["ChainEntry", "Llm", "LlmDeadline", "LlmResponse", "Provider", "ProviderSkip", "parse_chain"]
