from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache
from typing import Any
from uuid import uuid4

from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

from agent.openrouter_llm import get_chat_llm
from agent.tool import get_tools
from logger import get_logger
from prompt import render_prompt

logger = get_logger(__name__)


# Main Agent Orchestrator 생성
@lru_cache
def create_main_agent() -> Any:
    return create_agent(
        model=get_chat_llm(),
        tools=get_tools(),
        system_prompt=render_prompt("system_prompt.j2"),
        checkpointer=InMemorySaver(),
    )


# LangGraph checkpointer가 사용할 thread_id 설정 생성
def _agent_config(session_id: str | None) -> dict[str, Any]:
    thread_id = session_id.strip() if session_id else f"anonymous-{uuid4()}"
    return {"configurable": {"thread_id": thread_id}}


# LangChain 메시지 content 값을 사용자에게 보낼 문자열로 변환
def _content_to_text(content: object) -> str:
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(part.strip() for part in parts if part.strip())

    return str(content).strip() if content is not None else ""


# Agent 실행 결과에서 마지막 assistant 메시지 추출
def _extract_answer(result: object) -> str:
    if not isinstance(result, dict):
        return _content_to_text(result)

    messages = result.get("messages")
    if not isinstance(messages, list) or not messages:
        return _content_to_text(result.get("output"))

    last_message = messages[-1]
    return _content_to_text(getattr(last_message, "content", last_message))


# 사용자 메시지를 Main Agent에 전달하고, 최종 텍스트 답변 반환
def run_agent(message: str, session_id: str | None = None) -> str:
    agent = create_main_agent()
    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": message,
                }
            ]
        },
        config=_agent_config(session_id),
    )

    answer = _extract_answer(result)
    if answer:
        return answer

    logger.warning("agent returned empty answer")
    return "답변을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요."


_INTERNAL_STREAM_MARKERS = (
    "｜DSML｜tool",
    "tool_calls>",
    "<tool_calls",
)


def _looks_like_internal_stream_text(text: str) -> bool:
    return any(marker in text for marker in _INTERNAL_STREAM_MARKERS)


def _stream_chunk_to_text(chunk: object) -> str:
    if isinstance(chunk, tuple) and chunk:
        chunk = chunk[0]

    message_type = getattr(chunk, "type", "")
    if message_type not in {"ai", "AIMessageChunk"}:
        return ""

    if getattr(chunk, "tool_calls", None) or getattr(chunk, "tool_call_chunks", None):
        return ""

    content = getattr(chunk, "content", None)
    if isinstance(content, str):
        return "" if _looks_like_internal_stream_text(content) else content

    if content is None:
        return ""

    text = _content_to_text(content)
    return "" if _looks_like_internal_stream_text(text) else text


def run_agent_stream(
    message: str,
    session_id: str | None = None,
) -> Iterator[str]:
    agent = create_main_agent()
    chunks = agent.stream(
        {
            "messages": [
                {
                    "role": "user",
                    "content": message,
                }
            ]
        },
        config=_agent_config(session_id),
        stream_mode="messages",
    )

    for chunk in chunks:
        text = _stream_chunk_to_text(chunk)
        if text:
            yield text
