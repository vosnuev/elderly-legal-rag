from __future__ import annotations

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from settings import settings


def create_openrouter_chat_model(
    model_name: str | None = None,
    *,
    use_default_provider: bool = True,
    provider: str | None = None,
    allow_provider_fallbacks: bool | None = None,
    thinking: str | None = None,
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
        # LLM 호출 timeout은 Memgraph query timeout과 분리한다. stream chunk
        # timeout은 HTTP 200 이후 provider가 다음 token/tool event를 오래
        # 보내지 않는 stall을 chunking retry 경로로 넘기기 위한 값이다.
        timeout=settings.graph_llm_request_timeout_seconds,
        stream_chunk_timeout=settings.graph_llm_stream_chunk_timeout_seconds,
        max_retries=settings.graph_llm_max_retries,
        extra_body=_provider_routing_body(
            use_default_provider=use_default_provider,
            provider=provider,
            allow_provider_fallbacks=allow_provider_fallbacks,
            thinking=thinking,
        ),
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


def _provider_routing_body(
    *,
    use_default_provider: bool = True,
    provider: str | None = None,
    allow_provider_fallbacks: bool | None = None,
    thinking: str | None = None,
) -> dict[str, object] | None:
    body: dict[str, object] = {}
    selected_provider = provider
    if selected_provider is None and use_default_provider:
        selected_provider = settings.graph_llm_provider
    selected_provider = (selected_provider or "").strip()
    if selected_provider:
        # OpenRouter provider routing lives in the Chat Completions request body.
        # `order` is the preferred provider sequence. With fallbacks enabled,
        # OpenRouter tries backup providers when the preferred one is unavailable.
        body["provider"] = {
            "order": [selected_provider],
            "allow_fallbacks": (
                settings.graph_llm_provider_allow_fallbacks
                if allow_provider_fallbacks is None
                else allow_provider_fallbacks
            ),
        }
    selected_thinking = settings.graph_llm_thinking if thinking is None else thinking
    thinking_type = (selected_thinking or "").strip()
    if thinking_type:
        # DeepSeek V4 defaults to thinking mode. LangChain agents can send
        # tool_choice values that DeepSeek rejects in thinking mode, so this is
        # configurable per graph model.
        body["thinking"] = {"type": thinking_type}
    return body or None
