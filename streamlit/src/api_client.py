from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from pydantic import AnyUrl

from structured_logging import get_logger

logger = get_logger(__name__)


class ChatApiError(RuntimeError):
    """Raised when the Streamlit app cannot reach or parse the chat API."""


class ChatApiClient:
    def __init__(self, base_url: AnyUrl | str, *, timeout_seconds: float) -> None:
        self.base_url = str(base_url).rstrip("/") + "/"
        self.timeout_seconds = timeout_seconds

    def post_chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request_json("POST", "api/chat", payload=payload)

    def get_mock_chat(self) -> dict[str, Any]:
        return self._request_json("GET", "api/chat/mock")

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
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = Request(url, data=body, headers=headers, method=method)
        logger.info("chat_api_request_started", method=method, path=path)

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            logger.warning(
                "chat_api_http_error",
                method=method,
                path=path,
                status_code=error.code,
                detail=detail[:500],
            )
            raise ChatApiError(f"백엔드 응답 오류: HTTP {error.code}") from error
        except URLError as error:
            logger.warning(
                "chat_api_connection_failed",
                method=method,
                path=path,
                reason=str(error.reason),
            )
            raise ChatApiError("백엔드 API에 연결할 수 없습니다.") from error
        except TimeoutError as error:
            logger.warning(
                "chat_api_timeout",
                method=method,
                path=path,
                timeout_seconds=self.timeout_seconds,
            )
            raise ChatApiError("백엔드 API 응답 시간이 초과되었습니다.") from error

        try:
            parsed = json.loads(response_body)
        except json.JSONDecodeError as error:
            logger.warning(
                "chat_api_json_parse_failed",
                method=method,
                path=path,
                response_length=len(response_body),
            )
            raise ChatApiError("백엔드 응답 JSON을 해석할 수 없습니다.") from error

        if not isinstance(parsed, dict):
            logger.warning(
                "chat_api_unexpected_payload",
                method=method,
                path=path,
                payload_type=type(parsed).__name__,
            )
            raise ChatApiError("백엔드 응답 형식이 올바르지 않습니다.")

        logger.info(
            "chat_api_request_succeeded",
            method=method,
            path=path,
            response_field_count=len(parsed),
        )
        return parsed
