from __future__ import annotations

import sys
import unittest
from pathlib import Path
from time import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fastapi import Request, HTTPException
from fastapi.testclient import TestClient

from agent import graph
from app import app
from file_store import (
    FileValidationError,
    validate_content_type,
    validate_file_content,
    validate_file_extension,
)
from rate_limiter import InMemoryRateLimiter, RateLimitExceeded
from schemas.chat import ChatRequest, ChatResponse, ResponseKind, UserProfile
from session_store import ConversationTurn, InMemorySessionStore, session_store
from settings import settings


# 단위 테스트용 FastAPI Request 생성
def make_request(host: str = "test-client") -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/chat",
            "headers": [],
            "client": (host, 12345),
        }
    )


class FileValidationTest(unittest.TestCase):
    # 업로드 확장자, MIME, 실행 파일 내용을 차단하는지 확인
    def test_rejects_unsafe_upload_types(self) -> None:
        self.assertEqual(validate_file_extension("safe.md"), ".md")

        for file_name in ("bad.py", "bad.exe", "bad.sh", "no_extension"):
            with self.subTest(file_name=file_name):
                with self.assertRaises(FileValidationError):
                    validate_file_extension(file_name)

        with self.assertRaises(FileValidationError):
            validate_content_type(".md", "application/x-sh")
        with self.assertRaises(FileValidationError):
            validate_file_content(".md", b"#!/bin/sh\necho bad")
        with self.assertRaises(FileValidationError):
            validate_file_content(".txt", b"hello\x00world")


class SessionStoreTest(unittest.TestCase):
    # 세션 TTL과 프로필 삭제 동작 확인
    def test_session_ttl_and_clear_profile(self) -> None:
        store = InMemorySessionStore()
        session_id = store.ensure_session_id(None)
        store.save_profile(session_id, UserProfile(age=70))
        self.assertEqual(store.get(session_id).user_profile.age, 70)

        store.clear_profile(session_id)
        self.assertIsNone(store.get(session_id).user_profile)

        store.get("expired")
        store._sessions["expired"].updated_at = time() - settings.session_ttl_seconds - 1
        self.assertEqual(store.count(), 1)


class ChatApiTest(unittest.TestCase):
    # user_profile을 null로 명시하면 기존 프로필 삭제 확인
    def test_explicit_null_user_profile_clears_saved_profile(self) -> None:
        from api import chat as chat_api

        session_id = "profile-clear-test"
        session_store.delete(session_id)
        session_store.save_profile(session_id, UserProfile(age=75))

        with patch.object(
            chat_api,
            "create_clarification_response",
            return_value=ChatResponse(kind=ResponseKind.CLARIFICATION, summary="ok"),
        ):
            chat_api.chat(
                ChatRequest(question="새 질문", session_id=session_id, user_profile=None),
                make_request("profile-clear"),
            )

        self.assertIsNone(session_store.get(session_id).user_profile)
        session_store.delete(session_id)

    # user_profile을 생략하면 기존 프로필 재사용 확인
    def test_omitted_user_profile_reuses_saved_profile(self) -> None:
        from api import chat as chat_api

        session_id = "profile-reuse-test"
        captured: dict[str, UserProfile | None] = {}
        session_store.delete(session_id)
        session_store.save_profile(session_id, UserProfile(age=80))

        def fake_clarification(request: ChatRequest) -> ChatResponse:
            captured["profile"] = request.user_profile
            return ChatResponse(kind=ResponseKind.CLARIFICATION, summary="ok")

        with patch.object(chat_api, "create_clarification_response", fake_clarification):
            chat_api.chat(
                ChatRequest(question="새 질문", session_id=session_id),
                make_request("profile-reuse"),
            )

        self.assertEqual(captured["profile"].age, 80)
        session_store.delete(session_id)


class FollowUpQueryTest(unittest.TestCase):
    # 후속 질문 RAG 쿼리가 중복/과다 길이로 커지지 않는지 확인
    def test_follow_up_query_is_deduped_and_trimmed(self) -> None:
        captured: dict[str, str] = {}

        def fake_retrieve(query: str):
            captured["query"] = query
            return []

        long_history = "기초연금 신청 방법 " * 100
        history = [
            ConversationTurn(role="user", content=long_history),
            ConversationTurn(role="assistant", content="이전 답변"),
        ]
        question = "신청서는 어디서 받아?"

        with patch.object(graph, "_retrieve_documents", fake_retrieve):
            graph.answer_with_follow_up(
                ChatRequest(question=question, is_follow_up=True),
                history,
            )

        query = captured["query"]
        self.assertLessEqual(len(query), settings.rag_search_query_max_chars)
        self.assertEqual(query.count(question), 1)
        self.assertIn("이전 맥락:", query)


class RateLimiterTest(unittest.TestCase):
    # 설정된 횟수를 넘으면 RateLimitExceeded 발생 확인
    def test_rate_limiter_blocks_after_limit(self) -> None:
        old_requests = settings.rate_limit_requests
        old_window = settings.rate_limit_window_seconds
        old_enabled = settings.rate_limit_enabled
        settings.rate_limit_requests = 2
        settings.rate_limit_window_seconds = 60
        settings.rate_limit_enabled = True

        try:
            limiter = InMemoryRateLimiter()
            limiter.check("unit-test")
            limiter.check("unit-test")
            with self.assertRaises(RateLimitExceeded):
                limiter.check("unit-test")
        finally:
            settings.rate_limit_requests = old_requests
            settings.rate_limit_window_seconds = old_window
            settings.rate_limit_enabled = old_enabled


class FileStatusValidationTest(unittest.TestCase):
    # job_id가 backend 발급 uuid hex 형식인지 확인
    def test_invalid_job_id_is_rejected(self) -> None:
        from api.files import _validate_job_id

        _validate_job_id("0" * 32)
        with self.assertRaises(HTTPException):
            _validate_job_id("../bad")
        with self.assertRaises(HTTPException):
            _validate_job_id("550e8400-e29b-41d4-a716-446655440000")


class CorsConfigTest(unittest.TestCase):
    # 프론트 개발 포트에서 오는 브라우저 요청 허용 확인
    def test_local_frontend_origin_is_allowed(self) -> None:
        client = TestClient(app)
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], "http://localhost:3000")


if __name__ == "__main__":
    unittest.main()
