from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agent.graph import run_agent, run_agent_stream
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


# 사용자의 메시지를 Agent에 전달하고 자연어 답변을 반환
@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        answer = run_agent(request.message, session_id=request.session_id)
    except Exception as exc:
        logger.exception("chat agent execution failed")
        raise HTTPException(status_code=500, detail="Agent 실행 중 오류가 발생했습니다.") from exc

    return ChatResponse(answer=answer)

def _sse_event(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

@router.post("/chat/stream")
def chat_stream(request: ChatRequest) -> StreamingResponse:
    def event_generator():
        answer_parts: list[str] = []

        try:
            for delta in run_agent_stream(request.message, session_id=request.session_id):
                answer_parts.append(delta)
                yield _sse_event("delta", {"content": delta})

            answer = "".join(answer_parts).strip()
            if not answer:
                answer = "답변을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요."

            yield _sse_event("final", ChatResponse(answer=answer).model_dump())
        except Exception:
            logger.exception("chat stream agent execution failed")
            yield _sse_event("error", {"message": "Agent 실행 중 오류가 발생했습니다."})

    return StreamingResponse(event_generator(), media_type="text/event-stream")



__all__ = ["router"]
