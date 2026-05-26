from __future__ import annotations

import pandas as pd
import streamlit as st

from structured_logging import get_logger

from .legal_data import LAW_SUMMARIES

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


def render_major_laws() -> None:
    st.markdown('<p class="eyebrow">주요 법령</p>', unsafe_allow_html=True)
    st.title("자주 확인하는 법령 정리")

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
            st.caption(law["category"])
            st.subheader(law["name"])
            st.write(law["summary"])
            st.markdown(f"**주요 조항:** {law['articles']}")

            with st.expander("확인할 내용"):
                for detail in law["details"]:
                    st.markdown(f"- {detail}")

    st.divider()
    st.subheader("전체 법령 표")
    st.dataframe(_laws_table(), width="stretch", hide_index=True)
