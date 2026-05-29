from __future__ import annotations

import pandas as pd
import streamlit as st

from components import render_page_hero
from data.legal_data import LAW_SUMMARIES
from structured_logging import get_logger

logger = get_logger(__name__)


def _laws_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "분야": law["category"],
                "법령": law["name"],
                "주요 조항": law["articles"],
                "핵심 내용": law["summary"],
            }
            for law in LAW_SUMMARIES
        ]
    )


def render_second_page() -> None:
    render_page_hero(
        eyebrow="주요 법령",
        title="자주 확인하는 법령 정리",
    )

    with st.container(key="major_laws_content"):
        categories = ["전체", *sorted({law["category"] for law in LAW_SUMMARIES})]
        selected_category = st.segmented_control(
            "분야",
            categories,
            default="전체",
            label_visibility="collapsed",
        )

        laws = [
            law
            for law in LAW_SUMMARIES
            if selected_category == "전체" or law["category"] == selected_category
        ]
        logger.info(
            "major_laws_view_rendered",
            category=selected_category,
            law_count=len(laws),
        )

        for law in laws:
            with st.container(border=True):
                st.markdown(
                    f"""
                    <div class="law-card-heading">
                        <p>{law["category"]}</p>
                        <h3>{law["name"]}</h3>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.write(law["summary"])
                st.markdown(
                    f'<div class="law-article-box"><strong>주요 조항</strong> {law["articles"]}</div>',
                    unsafe_allow_html=True,
                )

                with st.expander("상세 내용"):
                    for detail in law["details"]:
                        st.markdown(f"- {detail}")

        st.divider()
        st.subheader("법령 표")
        st.dataframe(_laws_table(), width="stretch", hide_index=True)
