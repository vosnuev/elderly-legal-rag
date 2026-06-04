from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from typing import Any
from uuid import uuid4

import streamlit as st

from asset_paths import ROBOT_ICON_PATH
from chat_backend_client import (
    ChatBackendError,
    ChatBackendRequest,
    ChatBackendResponse,
    ToolCallResult,
    get_chat_backend_client,
)
from forms import build_initial_consultation_prompt, build_user_turn_message
from response_renderer import render_agent_blocks
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
        display_message="아래 박스에 상담내용을 적어주세요. 상담 기본 정보를 바탕으로 상담 진행됩니다.",
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
    tool_calls: list[ToolCallResult] = []
    content_blocks: list[dict[str, Any]] = []

    with st.chat_message("assistant", avatar=str(ROBOT_ICON_PATH)):
        placeholder = st.empty()
        placeholder.markdown(_render_shimmer(), unsafe_allow_html=True)
        with st.spinner("답변을 생성하는 중입니다."):
            for event in client.stream_chat(request):
                if event.type == "delta":
                    streamed_answer += event.content
                    _append_text_block(content_blocks, event.content)
                    render_agent_blocks(content_blocks, target=placeholder)
                elif event.type == "tool_call" and event.tool_call is not None:
                    tool_calls = _upsert_tool_call(tool_calls, event.tool_call)
                    _upsert_tool_call_block(content_blocks, event.tool_call)
                    render_agent_blocks(content_blocks, target=placeholder)
                elif event.type == "final" and event.response is not None:
                    final_response = event.response
                    if final_response.tool_calls:
                        for tool_call in final_response.tool_calls:
                            _upsert_tool_call_block(content_blocks, tool_call)
                        render_agent_blocks(content_blocks, target=placeholder)

    if final_response is not None:
        final_blocks = _finalize_content_blocks(
            content_blocks,
            answer=final_response.answer,
            tool_calls=final_response.tool_calls,
        )
        return replace(final_response, content_blocks=final_blocks)

    return ChatBackendResponse(
        answer=streamed_answer or "답변을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.",
        tool_calls=tool_calls,
        content_blocks=_finalize_content_blocks(
            content_blocks,
            answer=streamed_answer,
            tool_calls=tool_calls,
        ),
        session_id=request.session_id,
    )


def _upsert_tool_call(
    tool_calls: list[ToolCallResult],
    next_tool_call: ToolCallResult,
) -> list[ToolCallResult]:
    key = next_tool_call.id or next_tool_call.name
    updated = list(tool_calls)
    for index, tool_call in enumerate(updated):
        if (tool_call.id or tool_call.name) == key:
            updated[index] = next_tool_call
            return updated
    updated.append(next_tool_call)
    return updated


def _append_text_block(content_blocks: list[dict[str, Any]], content: str) -> None:
    if not content:
        return

    if content_blocks and content_blocks[-1].get("type") == "text":
        content_blocks[-1]["content"] = f"{content_blocks[-1].get('content', '')}{content}"
        return

    content_blocks.append({"type": "text", "content": content})


def _upsert_tool_call_block(
    content_blocks: list[dict[str, Any]],
    next_tool_call: ToolCallResult,
) -> None:
    key = _tool_call_key(next_tool_call)
    serialized = _tool_call_to_dict(next_tool_call)
    for block in content_blocks:
        if block.get("type") != "tool_call":
            continue
        tool_call = block.get("tool_call")
        if not isinstance(tool_call, dict):
            continue
        if _tool_call_dict_key(tool_call) == key:
            block["tool_call"] = serialized
            return

    content_blocks.append({"type": "tool_call", "tool_call": serialized})


def _finalize_content_blocks(
    content_blocks: list[dict[str, Any]],
    *,
    answer: str,
    tool_calls: list[ToolCallResult],
) -> list[dict[str, Any]]:
    finalized = [dict(block) for block in content_blocks if _is_valid_content_block(block)]
    has_text_block = any(block.get("type") == "text" for block in finalized)
    if not has_text_block and answer:
        finalized.append({"type": "text", "content": answer})

    for tool_call in tool_calls:
        _upsert_tool_call_block(finalized, tool_call)

    return finalized


def _is_valid_content_block(block: dict[str, Any]) -> bool:
    if block.get("type") == "text":
        return bool(str(block.get("content") or "").strip())
    if block.get("type") == "tool_call":
        return isinstance(block.get("tool_call"), dict)
    return False


def _tool_call_key(tool_call: ToolCallResult) -> str:
    return tool_call.id or tool_call.name


def _tool_call_dict_key(tool_call: dict[str, Any]) -> str:
    raw_id = tool_call.get("id")
    if raw_id:
        return str(raw_id)
    return str(tool_call.get("name") or "")


def _tool_call_to_dict(tool_call: ToolCallResult) -> dict[str, str | None]:
    return {"name": tool_call.name, "status": tool_call.status, "id": tool_call.id}


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
            _tool_call_to_dict(tool_call)
            for tool_call in response.tool_calls
        ],
        "content_blocks": response.content_blocks,
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
