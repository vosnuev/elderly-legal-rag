from __future__ import annotations

from collections.abc import Callable

import streamlit as st

from pages.consulting_page import render_consulting_page
from pages.law_record_page import render_law_record_page

PageRenderer = Callable[[], None]

PAGES: dict[str, PageRenderer] = {
    "내 상황 상담": render_consulting_page,
    "주요 법령": render_law_record_page,
}


def render_sidebar() -> str:
    st.sidebar.markdown(
        """
        <div class="sidebar-logo">
            <div class="sidebar-logo-mark">L</div>
            <div>
                <p class="sidebar-logo-title">법률 RAG</p>
                <p class="sidebar-logo-subtitle">상담 프론트</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    page = st.sidebar.radio(
        "메뉴",
        list(PAGES.keys()),
        label_visibility="collapsed",
    )

    if st.sidebar.button("로그아웃", width="stretch"):
        st.sidebar.info("로그아웃 요청이 기록되었습니다.")

    return page
