from __future__ import annotations

import streamlit as st

from response_renderer import render_chat_response
from services.consultation_flow import example_chat_messages


def render_example_chat() -> None:
    with st.expander("예시 채팅", expanded=True):
        for message in example_chat_messages():
            with st.chat_message(message["role"]):
                st.write(message["content"])


def render_chat_history() -> None:
    for message in st.session_state.get("consultation_messages", []):
        with st.chat_message(str(message["role"])):
            response = message.get("response")
            if isinstance(response, dict):
                render_chat_response(response)
                continue

            result = message.get("result")
            if isinstance(result, dict):
                _render_local_result(result)
                continue

            st.write(str(message["content"]))


def render_chat_prompt() -> str | None:
    prompt = st.chat_input(
        "상황을 입력하세요. 예: 회사에서 장애 때문에 불이익을 받은 것 같아요."
    )
    if prompt and prompt.strip():
        return prompt.strip()
    return None


def _render_local_result(result: dict[str, object]) -> None:
    with st.container(border=True):
        st.subheader(str(result["title"]))
        st.info(str(result["summary"]))

        law_tab, info_tab, case_tab, source_tab = st.tabs(
            ["관련 법령", "정보 정리", "판례", "출처"]
        )
        with law_tab:
            for law in result["laws"]:
                st.markdown(f"- **{law}**")
        with info_tab:
            for detail in result["details"]:
                st.markdown(f"- {detail}")
        with case_tab:
            for case in result.get("cases", ["판례 데이터 연결 후 표시합니다."]):
                st.markdown(f"- {case}")
        with source_tab:
            for source in result["sources"]:
                st.markdown(f"- {source}")

        st.warning("실제 법률 판단이나 신청 전에는 최신 법령과 담당 기관 안내를 확인하세요.")
