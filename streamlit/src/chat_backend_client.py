from __future__ import annotations

import json
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

import streamlit as st

from settings import settings
from structured_logging import get_logger

logger = get_logger(__name__)


class ChatBackendError(RuntimeError):
    """Raised when Streamlit cannot reach or parse the chat backend."""


@dataclass(frozen=True)
class ChatBackendRequest:
    session_id: str
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolCallResult:
    name: str
    status: str


@dataclass(frozen=True)
class Source:
    title: str | None = None
    url: str | None = None
    excerpt: str | None = None


@dataclass(frozen=True)
class ChatBackendResponse:
    answer: str
    tool_calls: list[ToolCallResult] = field(default_factory=list)
    sources: list[Source] = field(default_factory=list)
    session_id: str | None = None


@dataclass(frozen=True)
class ChatStreamEvent:
    type: str
    content: str = ""
    response: ChatBackendResponse | None = None


class ChatBackendClient:
    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float,
        mock: bool,
        mock_chunk_delay_seconds: float,
    ) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout_seconds = timeout_seconds
        self.mock = mock
        self.mock_chunk_delay_seconds = mock_chunk_delay_seconds

    def stream_chat(self, request: ChatBackendRequest) -> Iterator[ChatStreamEvent]:
        if self.mock:
            yield from self._stream_mock_chat(request)
            return

        response = self._post_chat(request)
        yield ChatStreamEvent(type="delta", content=response.answer)
        yield ChatStreamEvent(type="final", response=response)

    def _post_chat(self, request: ChatBackendRequest) -> ChatBackendResponse:
        payload = {
            "session_id": request.session_id,
            "message": request.message,
            "metadata": request.metadata,
        }
        parsed = self._request_json("POST", "chat", payload=payload)
        return _parse_chat_response(parsed, fallback_session_id=request.session_id)

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = urljoin(self.base_url, path)
        body = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json; charset=utf-8"

        request = Request(url, data=body, headers=headers, method=method)
        logger.info("chat_backend_request_started", method=method, path=path)

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            logger.warning(
                "chat_backend_http_error",
                method=method,
                path=path,
                status_code=error.code,
                detail=detail[:500],
            )
            raise ChatBackendError(f"백엔드 응답 오류: HTTP {error.code}") from error
        except URLError as error:
            logger.warning(
                "chat_backend_connection_failed",
                method=method,
                path=path,
                reason=str(error.reason),
            )
            raise ChatBackendError("백엔드 API에 연결할 수 없습니다.") from error
        except TimeoutError as error:
            logger.warning(
                "chat_backend_timeout",
                method=method,
                path=path,
                timeout_seconds=self.timeout_seconds,
            )
            raise ChatBackendError("백엔드 API 응답 시간이 초과되었습니다.") from error

        try:
            parsed = json.loads(response_body)
        except json.JSONDecodeError as error:
            logger.warning(
                "chat_backend_json_parse_failed",
                method=method,
                path=path,
                response_length=len(response_body),
            )
            raise ChatBackendError("백엔드 응답 JSON을 해석할 수 없습니다.") from error

        if not isinstance(parsed, dict):
            logger.warning(
                "chat_backend_unexpected_payload",
                method=method,
                path=path,
                payload_type=type(parsed).__name__,
            )
            raise ChatBackendError("백엔드 응답 형식이 올바르지 않습니다.")

        logger.info(
            "chat_backend_request_succeeded",
            method=method,
            path=path,
            response_field_count=len(parsed),
        )
        return parsed

    def _stream_mock_chat(self, request: ChatBackendRequest) -> Iterator[ChatStreamEvent]:
        answer = _build_mock_answer(request)
        for chunk in _chunk_text(answer):
            if self.mock_chunk_delay_seconds > 0:
                time.sleep(self.mock_chunk_delay_seconds)
            yield ChatStreamEvent(type="delta", content=chunk)

        yield ChatStreamEvent(
            type="final",
            response=ChatBackendResponse(
                answer=answer,
                tool_calls=[ToolCallResult(name="mock_agent.stream", status="completed")],
                sources=[],
                session_id=request.session_id,
            ),
        )


@st.cache_resource(show_spinner=False)
def _cached_chat_backend_client(
    base_url: str,
    timeout_seconds: float,
    mock: bool,
    mock_chunk_delay_seconds: float,
) -> ChatBackendClient:
    return ChatBackendClient(
        base_url,
        timeout_seconds=timeout_seconds,
        mock=mock,
        mock_chunk_delay_seconds=mock_chunk_delay_seconds,
    )


def get_chat_backend_client() -> ChatBackendClient:
    return _cached_chat_backend_client(
        str(settings.backend_base_url),
        settings.backend_timeout_seconds,
        settings.chat_backend_mock,
        settings.chat_mock_chunk_delay_seconds,
    )


def _parse_chat_response(
    payload: dict[str, Any],
    *,
    fallback_session_id: str,
) -> ChatBackendResponse:
    answer = payload.get("answer")
    if answer is None:
        answer = payload.get("summary", "")

    tool_calls = [
        ToolCallResult(
            name=str(item.get("name", "")),
            status=str(item.get("status", "")),
        )
        for item in payload.get("tool_calls", [])
        if isinstance(item, dict)
    ]
    sources = [
        Source(
            title=item.get("title"),
            url=item.get("url"),
            excerpt=item.get("excerpt"),
        )
        for item in payload.get("sources", [])
        if isinstance(item, dict)
    ]

    return ChatBackendResponse(
        answer=str(answer),
        tool_calls=tool_calls,
        sources=sources,
        session_id=str(payload.get("session_id") or fallback_session_id),
    )


def _build_mock_answer(request: ChatBackendRequest) -> str:
    turn_index = request.metadata.get("turn_index", 1)
    context_seeded = request.metadata.get("context_seeded", False)
    prefix = "상담 컨텍스트를 확인했습니다." if context_seeded else "이전 상담 흐름을 이어서 확인했습니다."
    return (
        f"{prefix}\n\n"
        f"- 세션: `{request.session_id}`\n"
        f"- turn: {turn_index}\n"
        "- backend main agent가 연결되면 같은 payload 계약으로 `/chat`에 전달됩니다.\n\n"
        "현재는 mock stream 응답입니다. 실제 backend 연결 전에도 화면 흐름, session_id 유지, "
        "assistant 응답 렌더링을 확인할 수 있습니다."
    )


def _chunk_text(value: str, *, size: int = 18) -> Iterator[str]:
    for index in range(0, len(value), size):
        yield value[index : index + size]
