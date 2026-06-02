from __future__ import annotations

import streamlit as st

from components import (
    render_chat_history,
    render_chat_prompt,
    render_consultation_summary,
    render_example_chat,
    render_page_hero,
)
from forms import render_consultation_form_gate
from services import submit_consultation_message, submit_initial_consultation
from structured_logging import get_logger

logger = get_logger(__name__)


def render_consulting_page() -> None:
    render_page_hero(
        eyebrow="상담 시작하기",
        title="법률 상담소",
        copy="법을 몰라도 괜찮습니다. 내가 겪은 상황을 적으면 관련 법령·정보·판례를 알려드립니다.",
    )

    form_data = render_consultation_form_gate()
    if not form_data:
        return

    render_consultation_summary(form_data)

    if st.session_state.pop("initial_consultation_pending", False):
        submit_initial_consultation(form_data=form_data)
        st.rerun()

    with st.container(key="example_section"):
        if not st.session_state.get("consultation_messages"):
            render_example_chat()

    render_chat_history()

    question_text = render_chat_prompt()
    if question_text:
        logger.info(
            "consultation_chat_input_received",
            question_length=len(question_text),
        )
        submit_consultation_message(
            question_text,
            form_data=form_data,
        )
        st.rerun()
