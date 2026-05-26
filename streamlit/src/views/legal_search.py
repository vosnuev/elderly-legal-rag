from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import streamlit as st
from streamlit_geolocation import streamlit_geolocation

from structured_logging import get_logger

from .legal_data import FALLBACK_RESULT, LAW_SUMMARIES

logger = get_logger(__name__)


EXAMPLE_SITUATIONS = [
    "장애인 등록이 되어 있는데 받을 수 있는 지원이 궁금해요",
    "회사에서 장애 때문에 불이익을 받은 것 같아요",
    "국가유공자인 가족이 복지 혜택을 받을 수 있는지 알고 싶어요",
    "장애인 고용과 관련해서 사업주가 지켜야 할 법이 궁금해요",
]

INTENT_OPTIONS = [
    "복지 서비스",
    "고용 지원",
    "차별/권리구제",
    "지역별 지원",
    "신청 절차",
]

AMBIGUOUS_WORDS = ["지원", "혜택", "도움", "신청", "받을 수"]


@st.cache_data(ttl=3600)
def _reverse_geocode_region(latitude: float, longitude: float) -> str:
    params = urlencode(
        {
            "format": "jsonv2",
            "lat": latitude,
            "lon": longitude,
            "accept-language": "ko",
        }
    )
    request = Request(
        f"https://nominatim.openstreetmap.org/reverse?{params}",
        headers={"User-Agent": "SKN28-Streamlit-Legal-Assistant/0.1"},
    )
    with urlopen(request, timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))

    address = payload.get("address", {})
    city = (
        address.get("city")
        or address.get("municipality")
        or address.get("province")
        or address.get("state")
    )
    district = address.get("borough") or address.get("city_district") or address.get("county")

    if city and district:
        return f"{city} {district}"
    return city or district or ""


def _is_ambiguous_question(question: str) -> bool:
    normalized_question = question.replace(" ", "")
    return len(question.strip()) < 16 or any(
        word.replace(" ", "") in normalized_question for word in AMBIGUOUS_WORDS
    )


def _find_result(
    question: str,
    *,
    age: int | None = None,
    region: str = "",
    intent: str = "",
    conditions: list[str] | None = None,
) -> dict[str, object]:
    normalized_question = question.lower()
    scored_laws = []
    conditions = conditions or []

    for law in LAW_SUMMARIES:
        score = sum(
            1 for keyword in law["keywords"] if keyword.lower() in normalized_question
        )
        if law["category"].lower() in normalized_question:
            score += 1
        if score:
            scored_laws.append((score, law))

    if not scored_laws:
        result = dict(FALLBACK_RESULT)
        result["profile"] = _build_profile_summary(age, region, intent, conditions)
        logger.info(
            "legal_search_result_resolved",
            fallback=True,
            matched_law_count=0,
            question_length=len(question.strip()),
            has_age=age is not None,
            has_region=bool(region.strip()),
            has_intent=bool(intent),
            condition_count=len(conditions),
        )
        return result

    scored_laws.sort(key=lambda item: item[0], reverse=True)
    matched_laws = [law for _, law in scored_laws[:3]]
    primary_law = matched_laws[0]
    logger.info(
        "legal_search_result_resolved",
        fallback=False,
        matched_law_count=len(matched_laws),
        question_length=len(question.strip()),
        has_age=age is not None,
        has_region=bool(region.strip()),
        has_intent=bool(intent),
        condition_count=len(conditions),
        primary_law=primary_law["name"],
    )

    return {
        "title": primary_law["name"],
        "summary": primary_law["summary"],
        "laws": [f"{law['name']} {law['articles']}" for law in matched_laws],
        "details": primary_law["details"],
        "sources": primary_law["sources"],
        "profile": _build_profile_summary(age, region, intent, conditions),
        "cases": [
            "관련 판례는 RAG/판례 데이터 연결 후 질문 의도에 맞춰 노출합니다.",
            "현재 화면에서는 판례 영역과 렌더링 구조만 먼저 확인합니다.",
        ],
    }


def _build_profile_summary(
    age: int | None,
    region: str,
    intent: str,
    conditions: list[str],
) -> list[str]:
    summary = []
    if age:
        summary.append(f"나이: {age}세")
    else:
        summary.append("나이: 미입력")

    if region.strip():
        summary.append(f"지역: {region.strip()}")
    else:
        summary.append("지역: 미입력")

    if intent:
        summary.append(f"질문 의도: {intent}")

    if conditions:
        summary.append(f"특수 조건: {', '.join(conditions)}")

    summary.append("연령 기준 필터링은 추후 정책 기준 확정 후 적용합니다.")
    return summary


def _get_profile_inputs() -> tuple[int | None, str]:
    autofill_region = st.session_state.pop("pending_autofill_region", "")
    if autofill_region:
        st.session_state["region_input"] = autofill_region

    with st.container(border=True):
        st.markdown("#### 기본 정보")
        st.caption("지역은 검색 정확도에 먼저 사용하고, 연령 기준은 일단 보류합니다.")

        age_col, region_col = st.columns([1, 2])
        with age_col:
            age = st.number_input(
                "나이",
                min_value=0,
                max_value=120,
                value=None,
                placeholder="예: 35",
                step=1,
            )
        with region_col:
            region = st.text_input(
                "사는 지역",
                placeholder="예: 서울시 강남구",
                key="region_input",
            )

        location_col, notice_col = st.columns([1, 2])
        with location_col:
            st.caption("현재 위치")
            location = streamlit_geolocation()
        with notice_col:
            if location and location.get("latitude") and location.get("longitude"):
                st.session_state["user_location"] = location
                latitude = float(location["latitude"])
                longitude = float(location["longitude"])
                try:
                    detected_region = _reverse_geocode_region(latitude, longitude)
                except Exception as error:
                    logger.warning(
                        "location_reverse_geocode_failed",
                        error=str(error),
                    )
                    detected_region = ""

                if detected_region:
                    st.success(f"위치 확인 완료: {detected_region}")
                    if st.session_state.get("region_input") != detected_region:
                        st.session_state["pending_autofill_region"] = detected_region
                        st.rerun()
                else:
                    st.success(f"위치 확인 완료: {latitude:.5f}, {longitude:.5f}")
                    st.caption("지역명 변환에 실패해 좌표만 표시합니다.")
                if location.get("accuracy"):
                    st.caption(f"정확도 약 {location['accuracy']:.0f}m")
            else:
                st.caption("브라우저 위치 권한을 허용하면 위도/경도를 가져옵니다.")

    return age, region


def _render_popular_questions() -> None:
    cols = st.columns(2)
    for index, question in enumerate(EXAMPLE_SITUATIONS):
        with cols[index % 2]:
            if st.button(question, width="stretch"):
                logger.info("legal_search_example_selected", example_index=index)
                st.session_state["legal_result"] = _find_result(question)


def _render_result(result: dict[str, object]) -> None:
    logger.info(
        "legal_search_result_rendered",
        law_count=len(result.get("laws", [])),
        source_count=len(result.get("sources", [])),
    )

    with st.container(border=True):
        st.caption("상담 답변")
        st.subheader(str(result["title"]))
        st.info(str(result["summary"]))

        profile_tab, law_tab, info_tab, case_tab, source_tab = st.tabs(
            ["입력 기준", "관련 법령", "정보 정리", "판례", "출처"]
        )
        with profile_tab:
            for profile in result.get("profile", []):
                st.markdown(f"- {profile}")
        with law_tab:
            for law in result["laws"]:
                st.markdown(f"- **{law}**")
        with info_tab:
            for detail in result["details"]:
                st.markdown(f"- {detail}")
        with case_tab:
            for case in result.get("cases", ["판례 데이터 연결 후 표시합니다."]):
                st.markdown(f"- {case}")
        with source_tab:
            for source in result["sources"]:
                st.markdown(f"- {source}")

        st.warning("실제 법률 판단이나 신청 전에는 최신 법령과 담당 기관 안내를 확인하세요.")


def _render_intent_choices() -> None:
    pending_question = st.session_state.get("pending_question")
    if not pending_question:
        return

    with st.chat_message("assistant"):
        st.warning("상황을 더 정확히 이해하려면 먼저 어떤 정보가 필요한지 골라주세요.")
    cols = st.columns(len(INTENT_OPTIONS))
    for col, intent in zip(cols, INTENT_OPTIONS, strict=True):
        with col:
            if st.button(intent, width="stretch"):
                logger.info(
                    "legal_search_intent_selected",
                    intent=intent,
                    has_age=st.session_state.get("pending_age") is not None,
                    has_region=bool(st.session_state.get("pending_region", "")),
                    condition_count=len(
                        st.session_state.get("pending_conditions", [])
                    ),
                )
                st.session_state["legal_result"] = _find_result(
                    str(pending_question),
                    age=st.session_state.get("pending_age"),
                    region=st.session_state.get("pending_region", ""),
                    intent=intent,
                    conditions=st.session_state.get("pending_conditions", []),
                )
                st.session_state.pop("pending_question", None)


def render_legal_search() -> None:
    st.markdown('<section class="search-hero">', unsafe_allow_html=True)
    st.markdown('<p class="eyebrow">내 상황 상담</p>', unsafe_allow_html=True)
    st.markdown(
        "<h1>상황을 설명하면 맞는 법령을 찾아드려요</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="hero-copy">법 이름을 몰라도 괜찮습니다. 겪고 있는 상황을 적으면 필요한 조건을 대화로 확인하고 관련 법령·정보·판례 방향을 정리합니다.</p>',
        unsafe_allow_html=True,
    )
    st.markdown("</section>", unsafe_allow_html=True)

    age, region = _get_profile_inputs()

    with st.form("legal_search_form"):
        question = st.text_area(
            "상황 설명",
            key="legal_question",
            placeholder="예: 장애인 등록이 되어 있는데 서울에서 받을 수 있는 지원을 알고 싶어요.",
            label_visibility="collapsed",
            height=96,
        )
        submitted = st.form_submit_button("상담 시작", width="stretch")

    if submitted:
        question_text = question.strip()
        if question_text:
            is_ambiguous = _is_ambiguous_question(question_text)
            logger.info(
                "legal_search_submitted",
                question_length=len(question_text),
                ambiguous=is_ambiguous,
                has_age=age is not None,
                has_region=bool(region.strip()),
            )

            if is_ambiguous:
                st.session_state["pending_question"] = question_text
                st.session_state["pending_age"] = age
                st.session_state["pending_region"] = region
                st.session_state["pending_conditions"] = []
                st.session_state.pop("legal_result", None)
            else:
                st.session_state["legal_result"] = _find_result(
                    question_text,
                    age=age,
                    region=region,
                    conditions=[],
                )
                st.session_state.pop("pending_question", None)
        else:
            logger.warning("legal_search_submitted_empty")
            st.warning("상황을 한두 문장으로 입력해 주세요.")

    _render_intent_choices()

    st.markdown("#### 예시 상황")
    _render_popular_questions()

    if "legal_result" in st.session_state:
        st.divider()
        _render_result(st.session_state["legal_result"])
