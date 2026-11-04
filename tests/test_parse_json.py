"""Planner reply parsing must survive fences, prose around the object and bad escapes."""

from __future__ import annotations

import pytest

from app.agent import PlanError, _parse_json


def test_strips_code_fence() -> None:
    assert _parse_json('```json\n{"sql": "SELECT 1"}\n```') == {"sql": "SELECT 1"}


def test_extracts_object_from_prose() -> None:
    assert _parse_json('Here you go: {"a": 1} hope it helps') == {"a": 1}


def test_repairs_invalid_escapes() -> None:
    raw = '{"a": "x' + chr(92) + 'u12 y", "b": "c:' + chr(92) + 'path"}'  # \u12 and \p are not valid JSON escapes
    assert _parse_json(raw) == {"a": "x\\u12 y", "b": "c:\\path"}


def test_raises_plan_error_on_garbage() -> None:
    with pytest.raises(PlanError):
        _parse_json("no json here")
    with pytest.raises(PlanError):
        _parse_json("[1, 2]")
