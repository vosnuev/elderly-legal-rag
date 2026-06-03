from __future__ import annotations

from functools import lru_cache
from typing import Any

from langchain_openai import ChatOpenAI

from logger import get_logger
from settings import settings

logger = get_logger(__name__)


# OpenRouter 호출에 붙일 기본 HTTP header 생성
def _openrouter_headers() -> dict[str, str]:
    headers = {
        "X-Title": settings.openrouter_app_title,
    }

    if settings.openrouter_app_url:
        headers["HTTP-Referer"] = settings.openrouter_app_url

    return headers


# OpenRouter provider routing 설정을 Chat Completions body에 포함한다.
def _openrouter_extra_body() -> dict[str, Any]:
    provider: dict[str, Any] = {
        "allow_fallbacks": settings.openrouter_allow_fallbacks,
    }

    if settings.openrouter_provider_order:
        provider["order"] = settings.openrouter_provider_order

    if settings.openrouter_require_parameters:
        provider["require_parameters"] = True

    return {"provider": provider}


def _reasoning_effort() -> str | None:
    if settings.llm_reasoning_effort is None:
        return None

    value = settings.llm_reasoning_effort.strip()
    if not value or value.lower() in {"none", "null", "off", "false"}:
        return None

    return value


# OpenRouter 기반 ChatOpenAI 클라이언트를 캐시해서 반환
@lru_cache
def get_chat_llm() -> ChatOpenAI:
    if settings.openrouter_api_key is None:
        logger.error("OPENROUTER_API_KEY is not set")
        raise RuntimeError("OPENROUTER_API_KEY is not set.")

    logger.info(
        "creating OpenRouter chat llm model=%s provider_order=%s allow_fallbacks=%s",
        settings.openrouter_model,
        settings.openrouter_provider_order,
        settings.openrouter_allow_fallbacks,
    )

    llm_kwargs: dict[str, Any] = {
        "model": settings.openrouter_model,
        "api_key": settings.openrouter_api_key.get_secret_value(),
        "base_url": settings.openrouter_base_url,
        "temperature": settings.llm_temperature,
        "timeout": settings.llm_timeout_ms / 1000,
        "max_retries": settings.llm_max_retries,
        "default_headers": _openrouter_headers(),
        "extra_body": _openrouter_extra_body(),
    }
    reasoning_effort = _reasoning_effort()
    if reasoning_effort:
        llm_kwargs["reasoning_effort"] = reasoning_effort
    if settings.llm_max_tokens:
        llm_kwargs["max_completion_tokens"] = settings.llm_max_tokens

    return ChatOpenAI(
        **llm_kwargs,
    )
