from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agent.graph import AgentRunResult, SourceSummary, ToolCallSummary, run_agent, run_agent_stream
from logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["chat"])


# Frontend가 보내는 사용자 채팅 요청 모델
class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(..., min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


# Agent가 호출한 tool 정보를 frontend에 전달하기 위한 응답 모델
class ToolCallResult(BaseModel):
    name: str
    status: str
    id: str | None = None


# RAG tool이 반환한 출처 정보를 frontend에 전달하기 위한 응답 모델
class Source(BaseModel):
    title: str | None = None
    url: str | None = None
    excerpt: str | None = None


# Frontend에 반환할 최종 채팅 응답 모델
class ChatResponse(BaseModel):
    answer: str
    tool_calls: list[ToolCallResult] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    session_id: str | None = None


def _tool_call_response(tool_call: ToolCallSummary) -> ToolCallResult:
    return ToolCallResult(
        name=tool_call.name,
        status=tool_call.status,
        id=tool_call.id,
    )


def _source_response(source: SourceSummary) -> Source:
    return Source(
        title=source.title,
        url=source.url,
        excerpt=source.excerpt,
    )


def _chat_response(result: AgentRunResult, session_id: str | None) -> ChatResponse:
    return ChatResponse(
        answer=result.answer,
        tool_calls=[_tool_call_response(tool_call) for tool_call in result.tool_calls],
        sources=[_source_response(source) for source in result.sources],
        session_id=session_id,
    )


# 사용자의 메시지를 Agent에 전달하고 자연어 답변을 반환
@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        result = await run_agent(request.message, session_id=request.session_id)
    except Exception as exc:
        logger.exception("chat agent execution failed")
        raise HTTPException(status_code=500, detail="Agent 실행 중 오류가 발생했습니다.") from exc

    return _chat_response(result, request.session_id)


def _sse_event(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/chat/stream")
def chat_stream(request: ChatRequest) -> StreamingResponse:
    async def event_generator():
        answer_parts: list[str] = []

        try:
            async for delta in run_agent_stream(
                request.message,
                session_id=request.session_id,
            ):
                if delta.type == "delta":
                    answer_parts.append(delta.content)
                    yield _sse_event("delta", {"content": delta.content})
                elif delta.type == "tool_call" and delta.tool_call is not None:
                    yield _sse_event(
                        "tool_call",
                        {"tool_call": _tool_call_response(delta.tool_call).model_dump()},
                    )
                elif delta.type == "final" and delta.result is not None:
                    yield _sse_event(
                        "final",
                        _chat_response(delta.result, request.session_id).model_dump(),
                    )
        except Exception:
            logger.exception("chat stream agent execution failed")
            yield _sse_event("error", {"message": "Agent 실행 중 오류가 발생했습니다."})

    return StreamingResponse(event_generator(), media_type="text/event-stream")


__all__ = ["router"]
