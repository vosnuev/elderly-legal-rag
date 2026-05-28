from __future__ import annotations

from collections.abc import Iterator

import streamlit as st

from data.legal_data import FALLBACK_RESULT, LAW_SUMMARIES
from shared.backend import submit_backend_chat
from settings import settings
from structured_logging import get_logger

logger = get_logger(__name__)

CLARIFICATION_PROMPT = (
    "질문 범위가 넓어서 먼저 방향을 좁히면 더 정확히 도와드릴 수 있어요. "
    "지역별 지원, 차별 권리구제, 신청 절차, 고용 지원 중 어떤 정보가 필요한지 "
    "채팅으로 답해주세요."
)

AMBIGUOUS_WORDS = ["지원", "혜택", "도움", "신청", "받을 수"]
QUESTION_FOCUS_WORDS = [
    "장애인",
    "국가유공자",
    "회사",
    "사업주",
    "근로자",
    "차별",
    "해고",
    "임금",
    "등록",
    "복지",
    "고용",
    "민원",
    "서류",
    "처리기간",
]
MIN_CLEAR_QUESTION_LENGTH = 22


def example_chat_messages() -> Iterator[dict[str, str]]:
    yield {
        "role": "user",
        "content": "회사에서 장애 때문에 불이익을 받은 것 같아요.",
    }
    yield {
        "role": "assistant",
        "content": (
            "어떤 정보가 필요하신가요? 지역별 지원, 차별 권리구제, "
            "고용 지원 중 하나로 좁혀주시면 다음 단계로 정리해드릴게요."
        ),
    }
    yield {
        "role": "user",
        "content": "차별 권리구제 쪽으로 알고 싶어요.",
    }
    yield {
        "role": "assistant",
        "content": (
            "좋아요. 불이익이 있었던 시점, 회사가 한 조치, 남아 있는 증빙을 "
            "기준으로 장애인차별금지법과 국가인권위원회 진정 가능성을 먼저 확인해볼게요."
        ),
    }


def parse_extra_info(extra_info: str) -> list[str]:
    return [item.strip() for item in extra_info.split(",") if item.strip()]


def format_extra_info(extra_info_items: list[str]) -> str:
    return ", ".join(extra_info_items)


def build_profile_summary(
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
        summary.append(f"기타 정보: {', '.join(conditions)}")

    summary.append("연령 기준 필터링은 추후 정책 기준 확정 후 적용합니다.")
    return summary


def build_prompt_context(
    age: int | None,
    region: str,
    conditions: list[str],
) -> str:
    profile_lines = build_profile_summary(age, region, "", conditions)
    return "[기본 정보]\n" + "\n".join(f"- {line}" for line in profile_lines)


def build_profile_display_items(
    age: int,
    region: str,
    conditions: list[str],
) -> list[str]:
    items = [f"나이: {age}세", f"지역: {region}"]
    if conditions:
        items.append(f"기타 정보: {', '.join(conditions)}")
    return items


def is_ambiguous_question(question: str) -> bool:
    return bool(get_clarification_context(question)["needs_clarification"])


def get_clarification_context(question: str) -> dict[str, object]:
    stripped_question = question.strip()
    normalized_question = stripped_question.replace(" ", "").lower()
    reasons = []

    has_focus_word = any(
        word.replace(" ", "").lower() in normalized_question
        for word in QUESTION_FOCUS_WORDS
    )
    generic_word_count = sum(
        1 for word in AMBIGUOUS_WORDS if word.replace(" ", "") in normalized_question
    )

    if len(stripped_question) < MIN_CLEAR_QUESTION_LENGTH:
        reasons.append("질문이 짧아서 대상과 상황을 더 확인해야 합니다.")
    if generic_word_count and not has_focus_word:
        reasons.append("지원·혜택처럼 범위가 넓은 표현이 있어 주제를 먼저 좁혀야 합니다.")
    if not any(
        keyword.lower() in stripped_question.lower()
        for law in LAW_SUMMARIES
        for keyword in law["keywords"]
    ):
        reasons.append("현재 임시 법령 데이터와 바로 연결되는 핵심 단어가 적습니다.")

    suggestions = [
        "누가 겪는 일인지: 본인, 가족, 근로자, 사업주",
        "원하는 결과: 지원 신청, 법령 확인, 불이익 대응, 서류 확인",
        "진행 단계: 알아보는 중, 신청 전, 거절됨, 분쟁 발생",
        "기타 정보: 국가유공자, 장애인 등록 여부, 근로자/사업주 여부",
    ]

    return {
        "needs_clarification": bool(reasons),
        "reasons": reasons,
        "suggestions": suggestions,
    }


def submit_consultation_message(
    question: str,
    *,
    age: int | None = None,
    region: str = "",
    conditions: list[str] | None = None,
) -> None:
    messages = st.session_state.setdefault("consultation_messages", [])
    messages.append({"role": "user", "content": question})
    prompt_question = _compose_prompt_question(
        question,
        age=age,
        region=region,
        conditions=conditions or [],
    )

    if settings.use_backend_api:
        backend_result = submit_backend_chat(prompt_question, age=age, region=region)
        if backend_result.error:
            st.session_state["backend_chat_error"] = backend_result.error
            messages.append(
                {
                    "role": "assistant",
                    "content": backend_result.error,
                    "kind": "error",
                }
            )
            return

        response = backend_result.response
        st.session_state["backend_chat_response"] = response
        st.session_state["backend_original_question"] = prompt_question
        st.session_state.pop("backend_chat_error", None)
        messages.append(
            {
                "role": "assistant",
                "content": str(
                    response.get("summary", "답변을 가져왔습니다.")
                    if isinstance(response, dict)
                    else "답변을 가져왔습니다."
                ),
                "response": response,
            }
        )
        return

    if is_ambiguous_question(question):
        context = get_clarification_context(question)
        suggestions = "\n".join(f"- {item}" for item in context["suggestions"])
        messages.append(
            {
                "role": "assistant",
                "content": f"{CLARIFICATION_PROMPT}\n\n확인하면 좋은 정보:\n{suggestions}",
            }
        )
        st.session_state.pop("legal_result", None)
        return

    result = _find_result(
        prompt_question,
        age=age,
        region=region,
        conditions=conditions or [],
    )
    st.session_state["legal_result"] = result
    messages.append(
        {
            "role": "assistant",
            "content": str(result["summary"]),
            "result": result,
        }
    )
    _clear_pending_question()


def _compose_prompt_question(
    question: str,
    *,
    age: int | None,
    region: str,
    conditions: list[str] | None = None,
) -> str:
    return f"{build_prompt_context(age, region, conditions or [])}\n\n[사용자 질문]\n{question}"


def _clear_pending_question() -> None:
    for key in [
        "pending_question",
        "pending_age",
        "pending_region",
        "pending_conditions",
        "pending_clarification_context",
    ]:
        st.session_state.pop(key, None)


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
        result["profile"] = build_profile_summary(age, region, intent, conditions)
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
        "profile": build_profile_summary(age, region, intent, conditions),
        "cases": [
            "관련 판례는 RAG/판례 데이터 연결 후 질문 의도에 맞춰 노출합니다.",
            "현재 화면에서는 판례 영역과 렌더링 구조만 먼저 확인합니다.",
        ],
    }
