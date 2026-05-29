from __future__ import annotations

import streamlit as st

from forms import build_form_display_items


def render_consultation_summary(form_data: dict[str, object]) -> None:
    with st.container(border=True, key="consultation_summary_card"):
        form_items = "".join(
            f'<span class="consultation-summary-item">{item}</span>'
            for item in build_form_display_items(form_data)
        )
        st.markdown(
            f"""
            <div class="consultation-summary-header">
                <p class="consultation-summary-title">입력된 상담 정보</p>
                <div class="consultation-summary-items">{form_items}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("상담 정보 다시 입력", width="stretch"):
            clear_consultation_session()
            st.rerun()


def clear_consultation_session() -> None:
    for key in [
        "consultation_form_ready",
        "consultation_form",
        "consultation_messages",
        "backend_chat_response",
        "backend_chat_error",
        "backend_chat_session_id",
        "backend_context_seeded",
        "chat_response_pending",
        "legal_result",
        "birth_year_select",
        "region_input",
        "consultation_subject_select",
        "consultation_goal_select",
        "consultation_stage_select",
        "consultation_extra_info",
        "form_conditions",
        "use_location_button",
        "pending_autofill_region",
        "user_location",
        "location_error",
    ]:
        st.session_state.pop(key, None)
