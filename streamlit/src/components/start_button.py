from __future__ import annotations

import streamlit as st


def render_start_button() -> bool:
    with st.container(key="start_consultation_button"):
        _, button_col, _ = st.columns([1, 0.36, 1])
        with button_col:
            return st.button("상담 시작", width="stretch", type="primary")
