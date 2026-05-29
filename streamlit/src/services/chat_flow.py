from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import streamlit as st

from chat_backend_client import (
    ChatBackendError,
    ChatBackendRequest,
    ChatBackendResponse,
    get_chat_backend_client,
)
from forms import build_initial_consultation_prompt, build_user_turn_message
from response_renderer import render_agent_markdown
from settings import settings
from structured_logging import get_logger

logger = get_logger(__name__)


def example_chat_messages() -> Iterator[dict[str, str]]:
    yield {
        "role": "user",
        "content": "회사에서 장애 때문에 불이익을 받은 것 같아요.",
    }
    yield {
        "role": "assistant",
        "content": (
            "어떤 불이익인지, 현재 진행 단계가 어디인지 알려주시면 "
            "관련 법령과 대응 절차를 이어서 정리해드릴게요."
        ),
    }


def submit_consultation_message(
    question: str,
    *,
    form_data: dict[str, object],
) -> None:
    if st.session_state.get("chat_response_pending"):
        logger.info("consultation_chat_ignored_pending_response")
        return

    include_initial_context = not st.session_state.get("backend_context_seeded", False)
    backend_message = build_user_turn_message(
        question,
        form_data,
        include_initial_context=include_initial_context,
    )
    _submit_backend_message(
        display_message=question,
        backend_message=backend_message,
        context_seeded=include_initial_context,
        turn_kind="user_chat",
    )


def submit_initial_consultation(
    *,
    form_data: dict[str, object],
) -> None:
    if st.session_state.get("backend_context_seeded"):
        return

    _submit_backend_message(
        display_message="상담 기본 정보를 바탕으로 상담을 시작해 주세요.",
        backend_message=build_initial_consultation_prompt(form_data),
        context_seeded=True,
        turn_kind="initial_context",
    )


def _submit_backend_message(
    *,
    display_message: str,
    backend_message: str,
    context_seeded: bool,
    turn_kind: str,
) -> None:
    if st.session_state.get("chat_response_pending"):
        logger.info("consultation_chat_ignored_pending_response")
        return

    messages = st.session_state.setdefault("consultation_messages", [])
    turn_index = _next_user_turn_index(messages)
    messages.append({"role": "user", "content": display_message})

    with st.chat_message("user"):
        st.write(display_message)

    session_id = _ensure_session_id()
    request = ChatBackendRequest(
        session_id=session_id,
        message=backend_message,
        metadata={
            "source": "streamlit",
            "turn_index": turn_index,
            "context_seeded": context_seeded,
            "turn_kind": turn_kind,
            "mock": settings.chat_backend_mock,
        },
    )

    logger.info(
        "consultation_chat_submitted",
        turn_index=turn_index,
        context_seeded=context_seeded,
        turn_kind=turn_kind,
        message_length=len(backend_message),
        mock=settings.chat_backend_mock,
    )
    if settings.log_llm_context:
        logger.info(
            "llm_context_constructed",
            session_id=session_id,
            turn_index=turn_index,
            context_seeded=context_seeded,
            turn_kind=turn_kind,
            message=backend_message,
        )

    st.session_state["chat_response_pending"] = True
    try:
        response = _stream_backend_response(request)
    except ChatBackendError as error:
        logger.warning("consultation_chat_failed", error=str(error))
        messages.append(
            {
                "role": "assistant",
                "content": str(error),
                "kind": "error",
            }
        )
        return
    finally:
        st.session_state["chat_response_pending"] = False

    if response.session_id:
        st.session_state["backend_chat_session_id"] = response.session_id
    st.session_state["backend_context_seeded"] = True
    st.session_state["backend_chat_response"] = _response_to_dict(response)
    messages.append(
        {
            "role": "assistant",
            "content": response.answer,
            "response": _response_to_dict(response),
        }
    )


def _stream_backend_response(request: ChatBackendRequest) -> ChatBackendResponse:
    client = get_chat_backend_client()
    streamed_answer = ""
    final_response: ChatBackendResponse | None = None

    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown(_render_shimmer(), unsafe_allow_html=True)
        with st.spinner("답변을 생성하는 중입니다."):
            for event in client.stream_chat(request):
                if event.type == "delta":
                    streamed_answer += event.content
                    render_agent_markdown(streamed_answer, target=placeholder)
                elif event.type == "final" and event.response is not None:
                    final_response = event.response

    if final_response is not None:
        return final_response

    return ChatBackendResponse(
        answer=streamed_answer or "답변을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.",
        session_id=request.session_id,
    )


def _render_shimmer() -> str:
    return """
    <div class="chat-shimmer" aria-label="답변 생성 중">
        <div class="chat-shimmer-line chat-shimmer-line-wide"></div>
        <div class="chat-shimmer-line"></div>
        <div class="chat-shimmer-line chat-shimmer-line-short"></div>
    </div>
    """


def _next_user_turn_index(messages: list[dict[str, object]]) -> int:
    return sum(1 for message in messages if message.get("role") == "user") + 1


def _ensure_session_id() -> str:
    session_id = st.session_state.get("backend_chat_session_id")
    if isinstance(session_id, str) and session_id.strip():
        return session_id

    session_id = f"streamlit-{uuid4()}"
    st.session_state["backend_chat_session_id"] = session_id
    st.session_state.setdefault("backend_context_seeded", False)
    return session_id


def _response_to_dict(response: ChatBackendResponse) -> dict[str, object]:
    return {
        "answer": response.answer,
        "tool_calls": [
            {"name": tool_call.name, "status": tool_call.status}
            for tool_call in response.tool_calls
        ],
        "sources": [
            {
                "title": source.title,
                "url": source.url,
                "excerpt": source.excerpt,
            }
            for source in response.sources
        ],
        "session_id": response.session_id,
    }
