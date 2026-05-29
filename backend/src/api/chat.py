from fastapi import APIRouter, HTTPException, Request

from agent.graph import (
    answer_with_follow_up,
    answer_with_custom_intent,
    answer_with_selected_option,
    create_clarification_response,
)
from logger import get_logger
from rate_limiter import enforce_rate_limit
from schemas.chat import ChatRequest, ChatResponse
from session_store import session_store

from mock.chat import create_mock_chat_response

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])

@router.get("/chat/mock", response_model=ChatResponse)
def mock_chat() -> ChatResponse:
    return create_mock_chat_response()


@router.delete("/chat/session/{session_id}")
def delete_chat_session(session_id: str) -> dict[str, bool]:
    deleted = session_store.delete(session_id)
    return {"deleted": deleted}


# 세션 기록에 남길 사용자 발화 내용 구성
def _user_turn_content(request: ChatRequest) -> str:
    parts = [request.question]

    if request.selected_option is not None:
        selected = request.selected_option
        parts.append(f"선택 보기: {selected.title}")
        if selected.search_focus:
            parts.append(f"검색 의도: {selected.search_focus}")

    if request.custom_intent:
        parts.append(f"기타 의도: {request.custom_intent}")

    return "\n".join(parts)


# 사용자의 질문 흐름을 받아, 보기 생성/최종 답변으로 분기
@router.post("/chat", response_model=ChatResponse)
def chat(chat_request: ChatRequest, http_request: Request) -> ChatResponse:
    enforce_rate_limit(http_request, "chat")

    session_id = session_store.ensure_session_id(chat_request.session_id)
    state = session_store.get(session_id)

    user_profile_provided = "user_profile" in chat_request.model_fields_set
    if user_profile_provided and chat_request.user_profile is not None:
        session_store.save_profile(session_id, chat_request.user_profile)
    elif user_profile_provided:
        session_store.clear_profile(session_id)
    elif state.user_profile is not None:
        chat_request = chat_request.model_copy(update={"user_profile": state.user_profile})

    chat_request = chat_request.model_copy(update={"session_id": session_id})

    if chat_request.custom_intent and chat_request.selected_option:
        raise HTTPException(
            status_code=400,
            detail="selected_option과 custom_intent는 동시에 보낼 수 없습니다.",
        )

    history = state.turns

    if chat_request.selected_option:
        response = answer_with_selected_option(chat_request, history)
    elif chat_request.custom_intent:
        response = answer_with_custom_intent(chat_request, history)
    elif chat_request.is_follow_up:
        response = answer_with_follow_up(chat_request, history)
    else:
        response = create_clarification_response(chat_request)

    session_store.add_turn(session_id, "user", _user_turn_content(chat_request))
    session_store.add_turn(session_id, "assistant", response.summary)

    return response.model_copy(update={"session_id": session_id})

__all__ = ["router"]
