from __future__ import annotations

import streamlit as st


def render_page_hero(*, eyebrow: str, title: str, copy: str | None = None) -> None:
    copy_html = f'<p class="hero-copy">{copy}</p>' if copy else ""
    st.markdown(
        f"""
        <section class="search-hero">
            <div class="page-header">
                <div class="page-header-content">
                    <p class="eyebrow">{eyebrow}</p>
                    <h1>{title}</h1>
                    {copy_html}
                </div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
