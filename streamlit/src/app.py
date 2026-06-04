from __future__ import annotations

import streamlit as st

from asset_paths import ROBOT_ICON_PATH
from navigation import PAGES, render_sidebar
from settings import settings
from structured_logging import configure_logging, get_logger
from styles import apply_styles

logger = get_logger(__name__)


def main() -> None:
    configure_logging()
    logger.info("streamlit_app_started", page_count=len(PAGES))
    st.set_page_config(
        page_title=settings.page_title,
        page_icon=str(ROBOT_ICON_PATH),
        layout=settings.layout,
        initial_sidebar_state=settings.initial_sidebar_state,
    )
    apply_styles()
    selected_page = render_sidebar()
    logger.info("streamlit_page_selected", page=selected_page)
    PAGES[selected_page]()


if __name__ == "__main__":
    main()
