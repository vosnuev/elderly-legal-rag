from __future__ import annotations

import streamlit as st

from components import (
    render_chat_history,
    render_chat_prompt,
    render_example_chat,
    render_page_hero,
    render_profile_gate,
    render_profile_summary,
)
from services.consultation_flow import (
    is_ambiguous_question,
    submit_consultation_message,
)
from settings import settings
from structured_logging import get_logger

logger = get_logger(__name__)


def render_first_page() -> None:
    render_page_hero(
        eyebrow="상담 시작하기",
        title="법률 상담소",
        copy="법을 몰라도 괜찮습니다. 내가 겪은 상황을 적으면 관련 법령·정보·판례를 알려드립니다",
    )

    profile = render_profile_gate()
    if not profile:
        return

    if settings.use_backend_api:
        st.caption(f"백엔드 API 연결 모드: {settings.backend_base_url}")

    age = int(profile["age"])
    region = str(profile["region"])
    conditions = list(profile.get("conditions", []))

    render_profile_summary(profile)

    with st.container(key="example_section"):
        if not st.session_state.get("consultation_messages"):
            render_example_chat()

    render_chat_history()

    question_text = render_chat_prompt()
    if question_text:
        logger.info(
            "legal_search_chat_submitted",
            question_length=len(question_text),
            ambiguous=is_ambiguous_question(question_text),
            has_age=True,
            has_region=True,
            condition_count=len(conditions),
        )
        submit_consultation_message(
            question_text,
            age=age,
            region=region,
            conditions=conditions,
        )
        st.rerun()
