from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from app import app


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
        with patch("api.chat.run_agent", return_value="신청은 주민센터에서 할 수 있습니다.") as run_agent:
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


if __name__ == "__main__":
    unittest.main()
