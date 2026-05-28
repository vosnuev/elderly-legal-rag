from __future__ import annotations

from collections.abc import Callable

import streamlit as st

from pages.first_page import render_first_page
from pages.second_page import render_second_page
from settings import settings

PageRenderer = Callable[[], None]

PAGES: dict[str, PageRenderer] = {
    "내 상황 상담": render_first_page,
    "주요 법령": render_second_page,
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

    st.sidebar.markdown(
        f"""
        <div class="sidebar-footer">
            <strong>Backend API</strong><br>
            {settings.backend_base_url}
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.sidebar.button("로그아웃", width="stretch"):
        st.sidebar.info("로그아웃 요청이 기록되었습니다.")

    return page
