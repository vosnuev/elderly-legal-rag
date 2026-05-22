from __future__ import annotations

import streamlit as st

from settings import settings


def main() -> None:
    st.set_page_config(page_title=settings.page_title, layout=settings.layout)
    st.title(settings.app_title)
    st.caption("Streamlit 기반 Python 프레임워크 프로젝트 초기 화면입니다.")

    st.subheader("Runtime")
    st.json(
        {
            "settings": "pydantic-settings",
            "backend_base_url": str(settings.backend_base_url),
        }
    )


if __name__ == "__main__":
    main()
