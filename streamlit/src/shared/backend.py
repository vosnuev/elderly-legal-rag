from __future__ import annotations

import streamlit as st

from api_client import ChatApiClient, ChatApiError
from services.consultation_flow_types import BackendChatResult
from settings import settings
from structured_logging import get_logger

logger = get_logger(__name__)


def submit_backend_chat(
    question: str,
    *,
    age: int | None,
    region: str,
    selected_option: dict[str, object] | None = None,
    custom_intent: str | None = None,
    is_follow_up: bool = False,
) -> BackendChatResult:
    try:
        with st.spinner("백엔드에서 답변을 가져오는 중입니다."):
            response = _chat_api_client().post_chat(
                _build_chat_payload(
                    question,
                    age=age,
                    region=region,
                    selected_option=selected_option,
                    custom_intent=custom_intent,
                    is_follow_up=is_follow_up,
                )
            )
    except ChatApiError as error:
        logger.warning("backend_chat_submit_failed", error=str(error))
        return BackendChatResult(error=str(error), response=None)

    if response.get("session_id"):
        st.session_state["backend_chat_session_id"] = response["session_id"]
    return BackendChatResult(error=None, response=response)


def _chat_api_client() -> ChatApiClient:
    return ChatApiClient(
        settings.backend_base_url,
        timeout_seconds=settings.backend_timeout_seconds,
    )


def _build_chat_payload(
    question: str,
    *,
    age: int | None,
    region: str,
    selected_option: dict[str, object] | None = None,
    custom_intent: str | None = None,
    is_follow_up: bool = False,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "question": question,
        "input_mode": "text",
        "is_follow_up": is_follow_up,
    }

    session_id = st.session_state.get("backend_chat_session_id")
    if session_id:
        payload["session_id"] = session_id

    user_profile = _build_user_profile(age, region)
    if user_profile is not None:
        payload["user_profile"] = user_profile

    if selected_option is not None:
        payload["selected_option"] = selected_option
    if custom_intent:
        payload["custom_intent"] = custom_intent

    return payload


def _build_user_profile(age: int | None, region: str) -> dict[str, object] | None:
    profile: dict[str, object] = {}
    if age is not None:
        profile["age"] = age

    normalized_region = region.strip()
    if normalized_region:
        region_parts = normalized_region.split(maxsplit=1)
        location: dict[str, object] = {
            "city": region_parts[0],
            "detected": bool(st.session_state.get("user_location")),
        }
        if len(region_parts) > 1:
            location["district"] = region_parts[1]

        user_location = st.session_state.get("user_location") or {}
        if user_location.get("latitude") and user_location.get("longitude"):
            location["latitude"] = float(user_location["latitude"])
            location["longitude"] = float(user_location["longitude"])

        profile["location"] = location

    return profile or None
