# 역할: sub-agent별 LLM override 설정을 graph 기본 설정과 병합한다.
from __future__ import annotations

from typing import Any


def agent_model_name(settings_obj: Any, field_name: str) -> str | None:
    return _blank_to_none(getattr(settings_obj, field_name, None))


def agent_provider(settings_obj: Any, field_name: str) -> str | None:
    value = getattr(settings_obj, field_name, None)
    if value is None:
        value = getattr(settings_obj, "graph_llm_provider", None)
    return _blank_to_none(value)


def agent_provider_allow_fallbacks(
    settings_obj: Any,
    field_name: str,
) -> bool | None:
    value = getattr(settings_obj, field_name, None)
    if value is None:
        value = getattr(settings_obj, "graph_llm_provider_allow_fallbacks", None)
    return value


def agent_retry_without_provider(settings_obj: Any, field_name: str) -> bool:
    value = getattr(settings_obj, field_name, None)
    if value is None:
        value = getattr(settings_obj, "graph_llm_retry_without_provider", False)
    return bool(value)


def agent_thinking(settings_obj: Any, field_name: str) -> str | None:
    value = getattr(settings_obj, field_name, None)
    if value is None:
        value = getattr(settings_obj, "graph_llm_thinking", None)
    return value


def _blank_to_none(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None
