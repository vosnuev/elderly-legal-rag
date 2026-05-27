from fastapi import APIRouter, HTTPException

from agent.graph import (
    answer_with_follow_up,
    answer_with_custom_intent,
    answer_with_selected_option,
    create_clarification_response,
)
from logger import get_logger
from schemas.chat import ChatRequest, ChatResponse
from session_store import session_store

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


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


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    session_id = session_store.ensure_session_id(request.session_id)
    state = session_store.get(session_id)

    if request.user_profile is not None:
        session_store.save_profile(session_id, request.user_profile)
    elif state.user_profile is not None:
        request = request.model_copy(update={"user_profile": state.user_profile})

    request = request.model_copy(update={"session_id": session_id})

    if request.custom_intent and request.selected_option:
        raise HTTPException(
            status_code=400,
            detail="selected_option과 custom_intent는 동시에 보낼 수 없습니다.",
        )

    history = state.turns

    if request.selected_option:
        response = answer_with_selected_option(request, history)
    elif request.custom_intent:
        response = answer_with_custom_intent(request, history)
    elif request.is_follow_up:
        response = answer_with_follow_up(request, history)
    else:
        response = create_clarification_response(request)

    session_store.add_turn(session_id, "user", _user_turn_content(request))
    session_store.add_turn(session_id, "assistant", response.summary)

    return response.model_copy(update={"session_id": session_id})

__all__ = ["router"]
