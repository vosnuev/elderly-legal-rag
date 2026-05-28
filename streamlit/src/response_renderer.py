from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from structured_logging import get_logger

logger = get_logger(__name__)

EVIDENCE_LABELS = {
    "not_applicable": "근거 상태: 해당 없음",
    "sufficient": "근거 상태: 충분",
    "insufficient": "근거 상태: 부족",
    "rag_error": "근거 상태: RAG 오류",
    "llm_fallback": "근거 상태: LLM fallback",
}

ELIGIBILITY_LABELS = {
    "eligible": "대상 가능성이 높음",
    "not_eligible": "대상 가능성이 낮음",
    "possibly_eligible": "대상 가능성 있음",
    "confirmation_required": "추가 확인 필요",
    "unknown": "판단 보류",
}


def _render_table(table_data: dict[str, Any]) -> None:
    headers = table_data.get("headers") or []
    rows = table_data.get("rows") or []
    if not headers or not rows:
        return

    st.dataframe(pd.DataFrame(rows, columns=headers), use_container_width=True)


def _render_laws(laws: list[dict[str, Any]]) -> None:
    if not laws:
        st.info("관련 법령은 답변 근거가 확정되면 표시됩니다.")
        return

    for law in laws:
        name = law.get("name", "법령명 미확인")
        article = law.get("article", "")
        url = law.get("url")
        label = f"**{name}**"
        if article:
            label = f"{label} - {article}"
        if url:
            st.markdown(f"- [{label}]({url})")
        else:
            st.markdown(f"- {label}")


def _render_references(references: list[dict[str, Any]]) -> None:
    if not references:
        return

    st.markdown("##### 상세 근거")
    for reference in references:
        title = reference.get("title", "출처명 미확인")
        file_name = reference.get("file_name")
        section = reference.get("section")
        score = reference.get("score")
        parts = [str(title)]
        if file_name:
            parts.append(str(file_name))
        if section:
            parts.append(str(section))
        if score is not None:
            parts.append(f"score={score}")
        st.markdown(f"- {' / '.join(parts)}")
        excerpt = reference.get("excerpt")
        if excerpt:
            st.caption(str(excerpt))


def _render_eligibility(eligibility: dict[str, Any] | None) -> None:
    if not eligibility:
        return

    status = str(eligibility.get("status", "unknown"))
    label = ELIGIBILITY_LABELS.get(status, status)
    st.markdown(f"##### 자격 판단: {label}")
    reason = eligibility.get("reason")
    if reason:
        st.write(str(reason))

    required_info = eligibility.get("required_info") or []
    if required_info:
        st.markdown("추가로 확인할 정보")
        for item in required_info:
            st.markdown(f"- {item}")


def render_chat_response(response: dict[str, Any]) -> None:
    logger.info(
        "chat_response_rendered",
        kind=response.get("kind"),
        law_count=len(response.get("laws") or []),
        source_count=len(response.get("sources") or []),
        option_count=len(response.get("options") or []),
    )

    with st.container(border=True):
        kind = response.get("kind")
        if kind == "clarification":
            st.subheader("상황을 조금만 더 좁혀주세요")
        else:
            st.subheader("상담 답변")

        summary = response.get("summary")
        if summary:
            st.info(str(summary))

        confidence = response.get("confidence")
        evidence_status = response.get("evidence_status")
        status_label = EVIDENCE_LABELS.get(str(evidence_status), str(evidence_status))
        status_parts = []
        if evidence_status:
            status_parts.append(status_label)
        if confidence is not None:
            status_parts.append(f"신뢰도 {float(confidence):.0%}")
        if status_parts:
            st.caption(" | ".join(status_parts))

        details = response.get("details") or []
        table = response.get("table")
        laws = response.get("laws") or []
        sources = response.get("sources") or []
        references = response.get("references") or []

        law_tab, info_tab, source_tab = st.tabs(["관련 법령", "정보 정리", "출처"])
        with law_tab:
            _render_laws(laws)
        with info_tab:
            _render_eligibility(response.get("eligibility"))
            if details:
                st.markdown("##### 상세 내용")
                for detail in details:
                    st.markdown(f"- {detail}")
            if table:
                st.markdown("##### 표")
                _render_table(table)
        with source_tab:
            if sources:
                for source in sources:
                    st.markdown(f"- {source}")
            else:
                st.info("표시할 출처가 없습니다.")
            _render_references(references)

        warning = response.get("warning")
        if warning:
            st.warning(str(warning))
