# 역할: LangChain agent tool 실행 오류를 agent가 읽을 수 있는 recoverable ToolMessage로 변환한다.
from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from langchain.agents.middleware import wrap_tool_call
from langchain_core.messages import ToolMessage
from langgraph.prebuilt.tool_node import ToolCallRequest

from observability.consume.service import observer


@wrap_tool_call
def keep_going_tool_errors(
    request: ToolCallRequest,
    handler: Callable[[ToolCallRequest], ToolMessage],
) -> ToolMessage:
    """Tool handler 예외를 agent가 읽을 수 있는 실패 결과로 바꾼다.

    이 middleware는 실제 tool 실행 단계까지 도달한 오류만 처리한다. provider가
    없는 tool name을 validation 단계에서 거절한 오류나 모델 API 호출 자체의 실패는
    wrap_model_call 또는 agent 실행부 guard에서 처리해야 한다.
    """

    try:
        return handler(request)
    except Exception as exc:  # noqa: BLE001
        payload = _tool_error_payload(request, exc)
        observer.agent_from_thread(
            agent_name="tool",
            stage="tool_error",
            log=f"tool failed: {payload['tool_name']}",
            tool_usage=payload,
            data={"recoverable": True},
        )
        return ToolMessage(
            content=json.dumps(payload, ensure_ascii=False),
            tool_call_id=str(request.tool_call.get("id") or ""),
        )


def _tool_error_payload(request: ToolCallRequest, exc: Exception) -> dict[str, Any]:
    tool_call = request.tool_call
    tool_name = str(tool_call.get("name") or getattr(request.tool, "name", "tool"))
    return {
        "status": "error",
        "recoverable": True,
        "tool_name": tool_name,
        "tool_args": tool_call.get("args") or {},
        "error_type": type(exc).__name__,
        "error": str(exc),
        "instruction": (
            "이 tool 호출은 실패했다. 같은 입력으로 반복 호출하지 말고, "
            "가능하면 다른 read tool이나 더 단순한 query로 우회해서 계속 진행하라."
        ),
    }
