from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessageChunk, ToolMessage

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from app import app
from agent.graph import _stream_chunk_to_text


# FastAPI TestClient를 생성해 테스트 간 재사용
client = TestClient(app)

# health endpoint가 서비스 상태를 반환하는지 확인
class HealthApiTest(unittest.TestCase):
    def test_health_returns_ok(self) -> None:
        response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

# /chat endpoint가 run_agent 결과를 answer로 반환하는지 확인
class ChatApiTest(unittest.TestCase):
    def test_chat_returns_agent_answer(self) -> None:
        with patch(
            "api.chat.run_agent",
            return_value="신청은 주민센터에서 할 수 있습니다.",
        ) as run_agent:
            response = client.post(
                "/chat",
                json={
                    "session_id": "test-session",
                    "message": "노인일자리 신청 방법 알려줘",
                    "metadata": {"source": "unit-test"},
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "answer": "신청은 주민센터에서 할 수 있습니다.",
                "tool_calls": [],
                "sources": [],
            },
        )
        run_agent.assert_called_once_with("노인일자리 신청 방법 알려줘", session_id="test-session")

    def test_chat_stream_returns_sse_event(self) -> None:
        with patch(
            "api.chat.run_agent_stream",
            return_value=(["신청은 ", "주민센터에서 ", "할 수 있습니다."]),
        ) as run_agent_stream:
            response = client.post(
                "/chat/stream",
                json={
                    "session_id": "stream-session",
                    "message": "노인일자리 신청 방법 알려줘",
                    "metadata": {"source": "unit-test"},
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/event-stream", response.headers["content-type"])

        body = response.text
        self.assertIn("event: delta", body)
        self.assertIn("event: final", body)
        self.assertIn('"content": "신청은 "', body)
        self.assertIn('"content": "주민센터에서 "', body)
        self.assertIn('"content": "할 수 있습니다."', body)
        self.assertIn("신청은 주민센터에서 할 수 있습니다.", body)

        run_agent_stream.assert_called_once_with("노인일자리 신청 방법 알려줘", session_id="stream-session")


class AgentStreamChunkTest(unittest.TestCase):
    def test_stream_chunk_to_text_returns_assistant_content(self) -> None:
        chunk = AIMessageChunk(content="신청은 ")

        self.assertEqual(_stream_chunk_to_text(chunk), "신청은 ")

    def test_stream_chunk_to_text_ignores_tool_messages(self) -> None:
        chunk = ToolMessage(content="mock 검색 결과입니다.", tool_call_id="tool-1")

        self.assertEqual(_stream_chunk_to_text(chunk), "")

    def test_stream_chunk_to_text_ignores_tool_call_chunks(self) -> None:
        chunk = AIMessageChunk(
            content="",
            tool_call_chunks=[
                {
                    "name": "mock_policy_search_tool",
                    "args": '{"query":"노인일자리"}',
                    "id": "call-1",
                    "index": 0,
                }
            ],
        )

        self.assertEqual(_stream_chunk_to_text(chunk), "")

    def test_stream_chunk_to_text_ignores_internal_tool_markup(self) -> None:
        chunk = AIMessageChunk(content="｜DSML｜tool_calls>")

        self.assertEqual(_stream_chunk_to_text(chunk), "")

if __name__ == "__main__":
    unittest.main()
