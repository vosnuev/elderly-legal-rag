from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

from agent.openrouter_llm import get_chat_llm
from agent.tool import get_tools
from logger import get_logger
from prompt import render_prompt

logger = get_logger(__name__)

_MAIN_AGENT: Any | None = None
_MAIN_AGENT_LOCK: asyncio.Lock | None = None


@dataclass(frozen=True)
class ToolCallSummary:
    name: str
    status: str
    id: str | None = None


@dataclass(frozen=True)
class SourceSummary:
    title: str | None = None
    url: str | None = None
    excerpt: str | None = None


@dataclass(frozen=True)
class AgentRunResult:
    answer: str
    tool_calls: list[ToolCallSummary] = field(default_factory=list)
    sources: list[SourceSummary] = field(default_factory=list)


@dataclass(frozen=True)
class AgentStreamEvent:
    type: str
    content: str = ""
    tool_call: ToolCallSummary | None = None
    result: AgentRunResult | None = None


def _main_agent_lock() -> asyncio.Lock:
    global _MAIN_AGENT_LOCK
    if _MAIN_AGENT_LOCK is None:
        _MAIN_AGENT_LOCK = asyncio.Lock()
    return _MAIN_AGENT_LOCK


# Main Agent Orchestrator 생성
async def create_main_agent() -> Any:
    global _MAIN_AGENT
    if _MAIN_AGENT is not None:
        return _MAIN_AGENT

    async with _main_agent_lock():
        if _MAIN_AGENT is not None:
            return _MAIN_AGENT

        _MAIN_AGENT = create_agent(
            model=get_chat_llm(),
            tools=await get_tools(),
            system_prompt=render_prompt("system_prompt.j2"),
            checkpointer=InMemorySaver(),
        )
        return _MAIN_AGENT


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


def _result_messages(result: object) -> list[object]:
    if not isinstance(result, dict):
        return []

    messages = result.get("messages")
    return messages if isinstance(messages, list) else []


def _message_type(message: object) -> str:
    return str(getattr(message, "type", "") or message.__class__.__name__)


# Agent 실행 결과에서 마지막 assistant 메시지 추출
def _extract_answer(result: object) -> str:
    if not isinstance(result, dict):
        return _content_to_text(result)

    messages = _result_messages(result)
    if not messages:
        return _content_to_text(result.get("output"))

    for message in reversed(messages):
        if _message_type(message) in {"ai", "AIMessage"}:
            answer = _content_to_text(getattr(message, "content", message))
            if answer:
                return answer

    return _content_to_text(getattr(messages[-1], "content", messages[-1]))


def _tool_call_from_mapping(call: dict[str, Any]) -> ToolCallSummary | None:
    function = call.get("function")
    name = call.get("name")
    if not name and isinstance(function, dict):
        name = function.get("name")
    if not name:
        return None

    raw_id = call.get("id") or call.get("tool_call_id")
    return ToolCallSummary(
        name=str(name),
        status="started",
        id=str(raw_id) if raw_id else None,
    )


def _message_tool_calls(message: object) -> list[ToolCallSummary]:
    summaries: list[ToolCallSummary] = []
    raw_calls = getattr(message, "tool_calls", None) or []
    for call in raw_calls:
        if isinstance(call, dict):
            summary = _tool_call_from_mapping(call)
            if summary is not None:
                summaries.append(summary)

    additional_kwargs = getattr(message, "additional_kwargs", None)
    if isinstance(additional_kwargs, dict):
        for call in additional_kwargs.get("tool_calls", []) or []:
            if isinstance(call, dict):
                summary = _tool_call_from_mapping(call)
                if summary is not None:
                    summaries.append(summary)

    raw_chunks = getattr(message, "tool_call_chunks", None) or []
    for chunk in raw_chunks:
        if not isinstance(chunk, dict):
            continue
        name = chunk.get("name")
        if not name:
            continue
        raw_id = chunk.get("id") or chunk.get("tool_call_id")
        summaries.append(
            ToolCallSummary(
                name=str(name),
                status="started",
                id=str(raw_id) if raw_id else None,
            )
        )

    return summaries


def _tool_call_key(tool_call: ToolCallSummary) -> str:
    return tool_call.id or tool_call.name


def _upsert_tool_call(
    state: dict[str, ToolCallSummary],
    tool_call: ToolCallSummary,
) -> ToolCallSummary | None:
    key = _tool_call_key(tool_call)
    existing = state.get(key)
    if existing == tool_call:
        return None
    if existing is not None and existing.status == tool_call.status:
        return None

    if existing is not None and not tool_call.name:
        tool_call = ToolCallSummary(
            name=existing.name,
            status=tool_call.status,
            id=tool_call.id or existing.id,
        )

    state[key] = tool_call
    return tool_call


def _record_tool_message(
    message: object,
    state: dict[str, ToolCallSummary],
) -> ToolCallSummary | None:
    if _message_type(message) not in {"tool", "ToolMessage"}:
        return None

    raw_id = getattr(message, "tool_call_id", None)
    key = str(raw_id) if raw_id else ""
    existing = state.get(key) if key else None
    name = str(getattr(message, "name", None) or (existing.name if existing else "tool"))
    status = "error" if str(getattr(message, "status", "")).lower() == "error" else "completed"
    return _upsert_tool_call(
        state,
        ToolCallSummary(name=name, status=status, id=str(raw_id) if raw_id else None),
    )


def _collect_tool_calls(messages: list[object]) -> list[ToolCallSummary]:
    state: dict[str, ToolCallSummary] = {}
    for message in messages:
        for tool_call in _message_tool_calls(message):
            _upsert_tool_call(state, tool_call)
        _record_tool_message(message, state)
    return list(state.values())


def _json_payloads(value: object) -> list[object]:
    if isinstance(value, str):
        try:
            return [json.loads(value)]
        except json.JSONDecodeError:
            return []
    if isinstance(value, dict):
        text = value.get("text")
        if isinstance(text, str):
            return _json_payloads(text)
        return [value]
    if isinstance(value, list):
        payloads: list[object] = []
        for item in value:
            payloads.extend(_json_payloads(item))
        return payloads
    return []


def _candidate_source_mappings(payload: object) -> list[dict[str, Any]]:
    mappings: list[dict[str, Any]] = []
    if isinstance(payload, list):
        for item in payload:
            mappings.extend(_candidate_source_mappings(item))
        return mappings
    if not isinstance(payload, dict):
        return mappings

    rows = payload.get("rows")
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict):
                mappings.append(row)

    content = payload.get("content")
    if isinstance(content, list):
        mappings.extend(_candidate_source_mappings(content))

    mappings.append(payload)
    return mappings


def _first_text(mapping: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _truncate(value: str, *, limit: int = 260) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "..."


def _source_from_mapping(mapping: dict[str, Any]) -> SourceSummary | None:
    combined: dict[str, Any] = dict(mapping)
    properties = mapping.get("properties")
    if isinstance(properties, dict):
        combined.update(properties)

    title = _first_text(
        combined,
        (
            "title",
            "file_name",
            "source_file",
            "document_title",
            "law_name",
            "article",
            "name",
            "id",
        ),
    )
    url = _first_text(combined, ("url", "source_url", "link"))
    excerpt = _first_text(
        combined,
        ("excerpt", "evidence_text", "content", "text", "raw_content"),
    )
    if excerpt:
        excerpt = _truncate(excerpt)

    if not title and not excerpt:
        return None
    return SourceSummary(title=title, url=url, excerpt=excerpt)


def _extract_sources_from_messages(messages: list[object]) -> list[SourceSummary]:
    sources: list[SourceSummary] = []
    seen: set[tuple[str | None, str | None, str | None]] = set()
    for message in messages:
        if _message_type(message) not in {"tool", "ToolMessage"}:
            continue
        for payload in _json_payloads(getattr(message, "content", None)):
            for mapping in _candidate_source_mappings(payload):
                source = _source_from_mapping(mapping)
                if source is None:
                    continue
                key = (source.title, source.url, source.excerpt)
                if key in seen:
                    continue
                seen.add(key)
                sources.append(source)
                if len(sources) >= 5:
                    return sources
    return sources


def _extract_run_result(result: object) -> AgentRunResult:
    answer = _extract_answer(result)
    messages = _result_messages(result)
    return AgentRunResult(
        answer=answer,
        tool_calls=_collect_tool_calls(messages),
        sources=_extract_sources_from_messages(messages),
    )


# 사용자 메시지를 Main Agent에 전달하고, 최종 텍스트 답변과 tool metadata 반환
async def run_agent(message: str, session_id: str | None = None) -> AgentRunResult:
    agent = await create_main_agent()
    result = await agent.ainvoke(
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

    run_result = _extract_run_result(result)
    if run_result.answer:
        return run_result

    logger.warning("agent returned empty answer")
    return AgentRunResult(
        answer="답변을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.",
        tool_calls=run_result.tool_calls,
        sources=run_result.sources,
    )


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


async def run_agent_stream(
    message: str,
    session_id: str | None = None,
) -> AsyncIterator[AgentStreamEvent]:
    agent = await create_main_agent()
    chunks = agent.astream(
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

    answer_parts: list[str] = []
    tool_calls: dict[str, ToolCallSummary] = {}
    tool_messages: list[object] = []

    async for chunk in chunks:
        message_chunk = chunk[0] if isinstance(chunk, tuple) and chunk else chunk

        for tool_call in _message_tool_calls(message_chunk):
            event_tool_call = _upsert_tool_call(tool_calls, tool_call)
            if event_tool_call is not None:
                yield AgentStreamEvent(type="tool_call", tool_call=event_tool_call)

        completed_call = _record_tool_message(message_chunk, tool_calls)
        if completed_call is not None:
            tool_messages.append(message_chunk)
            yield AgentStreamEvent(type="tool_call", tool_call=completed_call)

        text = _stream_chunk_to_text(message_chunk)
        if text:
            answer_parts.append(text)
            yield AgentStreamEvent(type="delta", content=text)

    answer = "".join(answer_parts).strip()
    if not answer:
        logger.warning("agent stream returned empty answer")
        answer = "답변을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요."

    yield AgentStreamEvent(
        type="final",
        result=AgentRunResult(
            answer=answer,
            tool_calls=list(tool_calls.values()),
            sources=_extract_sources_from_messages(tool_messages),
        ),
    )


def clear_main_agent_cache() -> None:
    global _MAIN_AGENT
    _MAIN_AGENT = None
