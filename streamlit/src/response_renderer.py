from __future__ import annotations

import html
import re
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

HTML_TAG_PATTERN = re.compile(r"<[^<>\n]{1,120}>")
LINE_BREAK_TAG_PATTERN = re.compile(r"<\s*br\s*/?\s*>", re.IGNORECASE)
KEYCAP_NUMBER_PATTERN = re.compile(r"([0-9])\ufe0f?\u20e3")
SPACED_STRONG_PATTERN = re.compile(r"\*\*\s+([^*\n]+?)\s+\*\*")
INLINE_CODE_PATTERN = re.compile(r"`([^`\n]+)`")
INLINE_STRONG_PATTERN = re.compile(r"\*\*([^*\n]+)\*\*")
CIRCLED_NUMBER_MAP = {
    "①": "1.",
    "②": "2.",
    "③": "3.",
    "④": "4.",
    "⑤": "5.",
    "⑥": "6.",
    "⑦": "7.",
    "⑧": "8.",
    "⑨": "9.",
}
TOOL_STATUS_LABELS = {
    "started": "조회 중",
    "running": "조회 중",
    "pending": "대기",
    "completed": "완료",
    "complete": "완료",
    "success": "완료",
    "succeeded": "완료",
    "error": "오류",
    "failed": "오류",
    "failure": "오류",
}
TOOL_STATUS_CLASSES = {
    "started": "is-running",
    "running": "is-running",
    "pending": "is-pending",
    "completed": "is-complete",
    "complete": "is-complete",
    "success": "is-complete",
    "succeeded": "is-complete",
    "error": "is-error",
    "failed": "is-error",
    "failure": "is-error",
}


def render_agent_markdown(value: str, target: Any | None = None) -> None:
    renderer = target or st
    renderer.markdown(_sanitize_agent_markdown(value), unsafe_allow_html=True)


def render_agent_blocks(blocks: list[dict[str, Any]], target: Any | None = None) -> None:
    renderer = target or st
    renderer.markdown(_render_agent_blocks(blocks), unsafe_allow_html=True)


def _sanitize_agent_markdown(value: str) -> str:
    def replace_tag(match: re.Match[str]) -> str:
        tag = match.group(0)
        if LINE_BREAK_TAG_PATTERN.fullmatch(tag):
            return "<br>"
        return html.escape(tag)

    normalized = _normalize_agent_markdown(value)
    escaped = HTML_TAG_PATTERN.sub(replace_tag, normalized)
    return _render_tabular_text_blocks(escaped)


def _normalize_agent_markdown(value: str) -> str:
    normalized = _normalize_number_icons(value.replace("\r\n", "\n"))
    return SPACED_STRONG_PATTERN.sub(r"**\1**", normalized)


def _normalize_number_icons(value: str) -> str:
    normalized = KEYCAP_NUMBER_PATTERN.sub(r"\1.", value)
    for icon, text_number in CIRCLED_NUMBER_MAP.items():
        normalized = normalized.replace(icon, text_number)
    return normalized


def _render_agent_blocks(blocks: list[dict[str, Any]]) -> str:
    rendered_blocks: list[str] = []
    for block in blocks:
        block_type = block.get("type")
        if block_type == "tool_call":
            tool_call = block.get("tool_call")
            if isinstance(tool_call, dict):
                rendered_blocks.append(_render_tool_call_card(tool_call))
            continue

        content = block.get("content")
        if isinstance(content, str) and content.strip():
            rendered_blocks.append(_sanitize_agent_markdown(content))

    return "\n\n".join(rendered_blocks)


def _render_tool_call_card(tool_call: dict[str, Any]) -> str:
    name = str(tool_call.get("name") or "도구")
    status = str(tool_call.get("status") or "started").lower()
    label = TOOL_STATUS_LABELS.get(status, status)
    status_class = TOOL_STATUS_CLASSES.get(status, "is-pending")
    return (
        f'<div class="agent-tool-card {status_class}" role="status" aria-live="polite">'
        '<span class="agent-tool-dot" aria-hidden="true"></span>'
        '<span class="agent-tool-copy">'
        '<span class="agent-tool-eyebrow">도구 호출</span>'
        f'<span class="agent-tool-name">{html.escape(name)}</span>'
        "</span>"
        f'<span class="agent-tool-status">{html.escape(label)}</span>'
        "</div>"
    )


def _render_tabular_text_blocks(value: str) -> str:
    lines = value.split("\n")
    rendered: list[str] = []
    index = 0
    while index < len(lines):
        if "\t" not in lines[index]:
            rendered.append(lines[index])
            index += 1
            continue

        start = index
        rows: list[list[str]] = []
        while index < len(lines) and "\t" in lines[index]:
            cells = [cell.strip() for cell in lines[index].split("\t")]
            if len(cells) < 2:
                break
            rows.append(cells)
            index += 1

        if len(rows) < 2:
            rendered.extend(lines[start:index])
            continue

        rendered.append(_render_tabular_rows(rows))

    return "\n".join(rendered)


def _render_tabular_rows(rows: list[list[str]]) -> str:
    column_count = max(len(row) for row in rows)
    normalized_rows = [row + [""] * (column_count - len(row)) for row in rows]
    header = normalized_rows[0]
    body_rows = normalized_rows[1:]

    header_cells = "".join(
        f"<th>{_render_inline_markdown_html(cell)}</th>" for cell in header
    )
    body = "\n".join(
        "<tr>"
        + "".join(f"<td>{_render_inline_markdown_html(cell)}</td>" for cell in row)
        + "</tr>"
        for row in body_rows
    )
    return (
        '<div class="agent-table-wrap">'
        '<table class="agent-summary-table">'
        f"<thead><tr>{header_cells}</tr></thead>"
        f"<tbody>{body}</tbody>"
        "</table>"
        "</div>"
    )


def _render_inline_markdown_html(value: str) -> str:
    escaped = html.escape(value)
    escaped = INLINE_CODE_PATTERN.sub(r"<code>\1</code>", escaped)
    return INLINE_STRONG_PATTERN.sub(r"<strong>\1</strong>", escaped)


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


def render_chat_response(response: dict[str, Any], *, key_prefix: str = "chat_response") -> None:
    if response.get("answer"):
        _render_backend_answer(response, key_prefix=key_prefix)
        return

    logger.info(
        "chat_response_rendered",
        kind=response.get("kind"),
        law_count=len(response.get("laws") or []),
        source_count=len(response.get("sources") or []),
        option_count=len(response.get("options") or []),
    )

    with st.container(border=True, key=f"{key_prefix}_card"):
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


def _render_backend_answer(response: dict[str, Any], *, key_prefix: str) -> None:
    logger.info(
        "backend_chat_response_rendered",
        tool_call_count=len(response.get("tool_calls") or []),
        source_count=len(response.get("sources") or []),
    )

    with st.container(border=True, key=f"{key_prefix}_card"):
        content_blocks = response.get("content_blocks")
        if isinstance(content_blocks, list) and content_blocks:
            render_agent_blocks(
                [block for block in content_blocks if isinstance(block, dict)]
            )
        else:
            render_agent_markdown(str(response["answer"]))

        tool_calls = response.get("tool_calls") or []
        sources = response.get("sources") or []
        if tool_calls and not content_blocks:
            render_agent_blocks(
                [
                    {"type": "tool_call", "tool_call": tool_call}
                    for tool_call in tool_calls
                    if isinstance(tool_call, dict)
                ]
            )

        if not sources:
            return

        with st.expander("출처", expanded=False):
            for source in sources:
                if isinstance(source, dict):
                    title = source.get("title") or "출처명 미확인"
                    url = source.get("url")
                    if url:
                        st.markdown(f"- [{title}]({url})")
                    else:
                        st.markdown(f"- {title}")
                    if source.get("excerpt"):
                        st.caption(str(source["excerpt"]))
