from __future__ import annotations

from datetime import date

import streamlit as st
from streamlit_geolocation import streamlit_geolocation

from components.start_button import render_start_button
from services.consultation_flow import format_extra_info, parse_extra_info
from services.geolocation import reverse_geocode_region
from structured_logging import get_logger

logger = get_logger(__name__)


def render_profile_gate() -> dict[str, object] | None:
    if st.session_state.get("profile_ready"):
        return st.session_state.get("consultation_profile")

    age, region, conditions, submitted = _render_profile_form()
    if submitted:
        if age is None or not region.strip():
            with st.container(key="profile_warning"):
                st.warning("태어난 연도와 사는 지역을 먼저 입력해 주세요.")
            return None

        profile = {
            "age": age,
            "region": region.strip(),
            "conditions": conditions,
        }
        st.session_state["profile_ready"] = True
        st.session_state["consultation_profile"] = profile
        st.session_state["consultation_messages"] = []
        logger.info(
            "consultation_profile_completed",
            has_age=True,
            has_region=True,
            condition_count=len(conditions),
        )
        st.rerun()

    return None


def _render_profile_form() -> tuple[int | None, str, list[str], bool]:
    autofill_region = st.session_state.pop("pending_autofill_region", "")
    if autofill_region:
        st.session_state["region_input"] = autofill_region

    with st.container(border=True, key="profile_card"):
        st.markdown("#### 기본 정보")
        st.caption("상담을 시작하려면 기본정보를 먼저 입력해야 합니다. 입력값은 질문 프롬프트에 자동으로 포함됩니다.")

        age_col, region_col, location_col = st.columns([0.9, 1.2, 0.28])
        with age_col:
            current_year = date.today().year
            selected_birth_year = st.selectbox(
                "태어난 연도",
                ["선택하세요", *range(current_year, 1899, -1)],
                index=0,
                key="birth_year_select",
            )
            birth_year = None if selected_birth_year == "선택하세요" else int(selected_birth_year)
        with region_col:
            region = st.text_input(
                "사는 지역",
                placeholder="예: 서울시 강남구",
                key="region_input",
            )
        with location_col:
            st.markdown(
                '<div class="location-button-spacer"></div>',
                unsafe_allow_html=True,
            )
            _render_location_button()

        extra_info = st.text_input(
            "기타 정보",
            value=format_extra_info(st.session_state.get("profile_conditions", [])),
            placeholder="예: 국가유공자, 장애인 등록 완료, 근로자",
            key="profile_extra_info",
        )
        selected_conditions = parse_extra_info(extra_info)
        st.session_state["profile_conditions"] = selected_conditions

        submitted = render_start_button()

    return _calculate_age_from_birth_year(birth_year), region, selected_conditions, submitted


def _render_location_button() -> None:
    location = streamlit_geolocation()
    if not location or not location.get("latitude") or not location.get("longitude"):
        return

    st.session_state["user_location"] = location
    latitude = float(location["latitude"])
    longitude = float(location["longitude"])
    try:
        detected_region = reverse_geocode_region(latitude, longitude)
    except Exception as error:
        logger.warning(
            "location_reverse_geocode_failed",
            error=str(error),
        )
        detected_region = ""

    if detected_region and st.session_state.get("region_input") != detected_region:
        st.session_state["pending_autofill_region"] = detected_region
        st.rerun()


def _calculate_age_from_birth_year(birth_year: int | None) -> int | None:
    if not birth_year:
        return None
    return date.today().year - birth_year
