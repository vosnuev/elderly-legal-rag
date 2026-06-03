from __future__ import annotations

from pathlib import Path
from random import sample

import streamlit as st

CHAT_AVATAR_PALETTE = (
    ("#B5EAD7", "#1E6F59"),
    ("#FFDAC1", "#8A4A24"),
    ("#C7CEEA", "#3F4F9E"),
    ("#FFFACD", "#7A6500"),
)


def _chat_avatar_css_variables() -> str:
    if "chat_avatar_colors" not in st.session_state:
        user_color, assistant_color = sample(CHAT_AVATAR_PALETTE, k=2)
        st.session_state["chat_avatar_colors"] = {
            "user_bg": user_color[0],
            "user_fg": user_color[1],
            "assistant_bg": assistant_color[0],
            "assistant_fg": assistant_color[1],
        }

    colors = st.session_state["chat_avatar_colors"]
    return (
        ":root {"
        f"--chat-user-avatar-bg: {colors['user_bg']};"
        f"--chat-user-avatar-fg: {colors['user_fg']};"
        f"--chat-assistant-avatar-bg: {colors['assistant_bg']};"
        f"--chat-assistant-avatar-fg: {colors['assistant_fg']};"
        "}"
    )


def apply_styles() -> None:
    css_path = Path(__file__).with_name("app.css")
    st.markdown(
        f"<style>{_chat_avatar_css_variables()}{css_path.read_text(encoding='utf-8')}</style>",
        unsafe_allow_html=True,
    )
