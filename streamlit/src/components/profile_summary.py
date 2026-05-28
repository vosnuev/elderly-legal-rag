from __future__ import annotations

import streamlit as st

from services.consultation_flow import build_profile_display_items


def render_profile_summary(profile: dict[str, object]) -> None:
    age = int(profile["age"])
    region = str(profile["region"])
    conditions = list(profile.get("conditions", []))

    with st.container(border=True, key="profile_summary_card"):
        profile_items = "".join(
            f'<span class="profile-summary-item">{item}</span>'
            for item in build_profile_display_items(age, region, conditions)
        )
        st.markdown(
            f"""
            <div class="profile-summary-header">
                <p class="profile-summary-title">입력된 기본 정보</p>
                <div class="profile-summary-items">{profile_items}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("기본 정보 다시 입력", width="stretch"):
            clear_consultation_session()
            st.rerun()


def clear_consultation_session() -> None:
    for key in [
        "profile_ready",
        "consultation_profile",
        "consultation_messages",
        "backend_chat_response",
        "backend_chat_error",
        "backend_chat_session_id",
        "legal_result",
    ]:
        st.session_state.pop(key, None)
