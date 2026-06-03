from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from uuid import uuid4

import streamlit as st

from components.geolocation_button import render_geolocation_button
from services.geolocation import detect_region_from_ip, reverse_geocode_region
from structured_logging import get_logger

logger = get_logger(__name__)

SUBJECT_OPTIONS = [
    "본인",
    "가족",
    "근로자",
    "사업주",
    "대리인/지원자",
    "여기에 없어요",
    "아직 모르겠음",
]
GOAL_OPTIONS = [
    "지원 신청",
    "법령 확인",
    "불이익 대응",
    "서류 확인",
    "기관 문의",
    "여기에 없어요",
    "아직 모르겠음",
]
STAGE_OPTIONS = [
    "알아보는 중",
    "신청 전",
    "신청/처리 중",
    "거절됨",
    "분쟁 발생",
    "여기에 없어요",
    "아직 모르겠음",
]


@dataclass(frozen=True)
class ConsultationFormData:
    age: int | None
    region: str
    subject: str
    goal: str
    stage: str
    conditions: list[str]


def render_consultation_form_gate() -> dict[str, object] | None:
    if st.session_state.get("consultation_form_ready"):
        return st.session_state.get("consultation_form")

    form_data, submitted = _render_consultation_form()
    if not submitted:
        return None

    st.session_state["consultation_form_ready"] = True
    st.session_state["consultation_form"] = asdict(form_data)
    st.session_state["consultation_messages"] = []
    st.session_state["backend_chat_session_id"] = f"streamlit-{uuid4()}"
    st.session_state["backend_context_seeded"] = False
    st.session_state["initial_consultation_pending"] = True
    logger.info(
        "consultation_form_completed",
        has_age=form_data.age is not None,
        has_region=bool(form_data.region.strip()),
        subject=form_data.subject,
        goal=form_data.goal,
        stage=form_data.stage,
        condition_count=len(form_data.conditions),
    )
    st.rerun()
    return None


def build_initial_context_message(form_data: dict[str, object]) -> str:
    lines = _build_context_lines(form_data)
    return "[상담 입력 컨텍스트]\n" + "\n".join(f"- {line}" for line in lines)


def build_initial_consultation_prompt(form_data: dict[str, object]) -> str:
    return (
        f"{build_initial_context_message(form_data)}\n\n"
        "[사용자 요청]\n"
        "위 상담 기본 정보를 바탕으로 법률 상담을 바로 시작해 주세요. "
        "아직 부족한 정보가 있으면 사용자가 답하기 쉬운 질문 1~2개로 이어가고, "
        "지금 확인 가능한 법률 쟁점이나 다음 행동이 있으면 간단히 정리해 주세요."
    )


def build_user_turn_message(
    question: str,
    form_data: dict[str, object],
    *,
    include_initial_context: bool,
) -> str:
    normalized_question = question.strip()
    if not include_initial_context:
        return normalized_question

    return (
        f"{build_initial_context_message(form_data)}\n\n"
        f"[사용자 질문]\n{normalized_question}"
    )


def build_form_display_items(form_data: dict[str, object]) -> list[str]:
    items = [
        _format_age_for_display(form_data.get("age")),
        _format_region_for_display(str(form_data.get("region", ""))),
        f"대상: {str(form_data['subject'])}",
        f"목적: {str(form_data['goal'])}",
        f"단계: {str(form_data['stage'])}",
    ]
    conditions = list(form_data.get("conditions", []))
    if conditions:
        items.append(f"기타 정보: {', '.join(str(item) for item in conditions)}")
    return items


def parse_extra_info(extra_info: str) -> list[str]:
    return [item.strip() for item in extra_info.split(",") if item.strip()]


def format_extra_info(extra_info_items: list[str]) -> str:
    return ", ".join(extra_info_items)


def _render_consultation_form() -> tuple[ConsultationFormData | None, bool]:
    autofill_region = st.session_state.pop("pending_autofill_region", "")
    if autofill_region:
        st.session_state["region_input"] = autofill_region

    with st.container(border=True, key="consultation_form_card"):
        st.markdown("#### 상담 기본 정보")
        st.caption("첫 질문에는 이 정보가 상담 컨텍스트로 함께 전달됩니다. 이후 대화는 같은 세션에서 이어집니다.")

        age_col, region_col, location_col = st.columns(
            [0.9, 1.9, 0.85],
            gap="small",
            vertical_alignment="top",
        )
        with age_col:
            current_year = date.today().year
            selected_birth_year = st.selectbox(
                "태어난 연도",
                ["선택하세요", *range(current_year, 1899, -1)],
                index=0,
                key="birth_year_select",
            )
            birth_year = (
                None
                if selected_birth_year == "선택하세요"
                else int(selected_birth_year)
            )
        with region_col:
            region = st.text_input(
                "사는 지역",
                placeholder="예: 서울시 강남구",
                key="region_input",
            )
        with location_col:
            st.markdown(
                '<div class="location-field-spacer"></div>',
                unsafe_allow_html=True,
            )
            _render_location_button()

        subject_col, goal_col, stage_col = st.columns(3)
        with subject_col:
            subject = st.selectbox(
                "누가 겪는 일인가요?",
                SUBJECT_OPTIONS,
                index=0,
                key="consultation_subject_select",
            )
        with goal_col:
            goal = st.selectbox(
                "필요한 정보",
                GOAL_OPTIONS,
                index=0,
                key="consultation_goal_select",
            )
        with stage_col:
            stage = st.selectbox(
                "진행 단계",
                STAGE_OPTIONS,
                index=0,
                key="consultation_stage_select",
            )

        extra_info = st.text_area(
            "기타 정보",
            value=format_extra_info(st.session_state.get("form_conditions", [])),
            placeholder="예: 국가유공자, 장애인 등록 완료, 근로자",
            key="consultation_extra_info",
            height=96,
        )
        conditions = parse_extra_info(extra_info)
        st.session_state["form_conditions"] = conditions

        submitted = st.button(
            "상담 시작",
            key="start_consultation_button",
            width="stretch",
            type="primary",
        )

    age = _calculate_age_from_birth_year(birth_year)
    normalized_region = region.strip()

    return (
        ConsultationFormData(
            age=age,
            region=normalized_region,
            subject=subject or "아직 모르겠음",
            goal=goal or "아직 모르겠음",
            stage=stage or "아직 모르겠음",
            conditions=conditions,
        ),
        submitted,
    )


def _render_location_button() -> None:
    location = render_geolocation_button(key="use_location_button")
    if not location or not location.get("latitude") or not location.get("longitude"):
        _autofill_region_from_ip_fallback()
        _render_location_error()
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
        st.session_state["location_error"] = {
            "message": "위치를 지역명으로 바꾸지 못했습니다. 지역을 직접 입력해 주세요."
        }
        detected_region = ""

    if detected_region and st.session_state.get("region_input") != detected_region:
        st.session_state.pop("location_error", None)
        st.session_state["pending_autofill_region"] = detected_region
        st.rerun()

    if not detected_region:
        if "location_error" not in st.session_state:
            st.session_state["location_error"] = {
                "message": "현재 위치를 찾지 못했습니다. 지역을 직접 입력해 주세요."
            }
        _render_location_error()


def _autofill_region_from_ip_fallback() -> None:
    error = st.session_state.get("location_error")
    if not isinstance(error, dict) or error.get("ip_fallback_attempted"):
        return

    error["ip_fallback_attempted"] = True
    try:
        detected_region = detect_region_from_ip()
    except Exception as fallback_error:
        logger.warning(
            "location_ip_fallback_failed",
            error=str(fallback_error),
        )
        return

    if not detected_region:
        return

    st.session_state["location_error"] = {
        "message": "브라우저 위치를 확인하지 못해 네트워크 기반 대략 위치를 사용했습니다."
    }
    if st.session_state.get("region_input") != detected_region:
        st.session_state["pending_autofill_region"] = detected_region
        st.rerun()


def _render_location_error() -> None:
    error = st.session_state.get("location_error")
    if not isinstance(error, dict):
        return
    code = error.get("code")
    if code == 1:
        message = "위치 권한이 차단되었습니다. 브라우저 위치 권한을 허용하거나 지역을 직접 입력해 주세요."
    elif code == 2:
        message = "현재 위치를 확인하지 못했습니다. 다시 시도하거나 지역을 직접 입력해 주세요."
    elif code == 3:
        message = "위치 확인 시간이 초과되었습니다. 다시 시도하거나 지역을 직접 입력해 주세요."
    else:
        message = str(
            error.get("message")
            or "현재 위치를 찾지 못했습니다. 지역을 직접 입력해 주세요."
        )
    st.caption(message)


def _build_context_lines(form_data: dict[str, object]) -> list[str]:
    conditions = list(form_data.get("conditions", []))
    lines = [
        _format_age_for_context(form_data.get("age")),
        _format_region_for_context(str(form_data.get("region", ""))),
        f"상담 대상: {str(form_data['subject'])}",
        f"사용자가 원하는 정보: {str(form_data['goal'])}",
        f"진행 단계: {str(form_data['stage'])}",
    ]
    if conditions:
        lines.append(f"기타 정보: {', '.join(str(item) for item in conditions)}")
    return lines


def _calculate_age_from_birth_year(birth_year: int | None) -> int | None:
    if not birth_year:
        return None
    return date.today().year - birth_year


def _format_age_for_display(age: object) -> str:
    if age is None:
        return "나이: 미입력"
    return f"나이: {int(age)}세"


def _format_region_for_display(region: str) -> str:
    if not region.strip():
        return "지역: 미입력"
    return f"지역: {region.strip()}"


def _format_age_for_context(age: object) -> str:
    if age is None:
        return "나이: 사용자가 입력하지 않음"
    return f"나이: {int(age)}세"


def _format_region_for_context(region: str) -> str:
    if not region.strip():
        return "지역: 사용자가 입력하지 않음"
    return f"지역: {region.strip()}"
