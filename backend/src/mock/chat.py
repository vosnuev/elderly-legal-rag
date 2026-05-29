from pathlib import Path

from schemas.chat import ChatResponse

MOCK_CHAT_RESPONSE_PATH = Path(__file__).with_name("chat_response.json")


# frontend 연결 테스트용 mock JSON을 ChatResponse schema로 검증해 반환
def create_mock_chat_response() -> ChatResponse:
    return ChatResponse.model_validate_json(
        MOCK_CHAT_RESPONSE_PATH.read_text(encoding="utf-8")
    )