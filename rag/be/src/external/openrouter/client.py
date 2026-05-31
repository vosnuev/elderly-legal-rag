from __future__ import annotations

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from settings import settings


def create_openrouter_chat_model(
    model_name: str | None = None,
) -> ChatOpenAI | None:
    api_key = _openrouter_api_key()
    selected_model = model_name or settings.graph_llm_model or settings.llm_model
    if api_key is None or not selected_model:
        return None

    return ChatOpenAI(
        model=selected_model,
        api_key=api_key,
        base_url=settings.openrouter_base_url,
        temperature=0,
        timeout=settings.query_timeout_ms / 1000,
        max_retries=2,
    )


def create_openrouter_embeddings() -> OpenAIEmbeddings | None:
    api_key = _openrouter_api_key()
    if api_key is None:
        return None

    return OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=api_key,
        base_url=settings.openrouter_base_url,
        dimensions=settings.embedding_dimensions,
    )


def _openrouter_api_key() -> str | None:
    if settings.openrouter_api_key is None:
        return None
    value = settings.openrouter_api_key.get_secret_value().strip()
    return value or None
