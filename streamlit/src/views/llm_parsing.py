import json
import re

import pandas as pd
import streamlit as st

from structured_logging import get_logger

logger = get_logger(__name__)


SAMPLE_OUTPUTS = {
    "정상 JSON 응답": '{"summary": "장애인 의무고용률은 공공기관 3.8%, 민간기업 3.1%입니다.", "details": ["상시근로자 50인 이상 사업장은 장애인 의무고용 대상입니다.", "의무고용률은 공공기관 3.8%, 민간기업 3.1%로 정해져 있습니다."], "laws": [{"name": "장애인고용촉진 및 직업재활법", "article": "제28조"}], "table": {"headers": ["구분", "의무고용률"], "rows": [["공공기관", "3.8%"], ["민간기업", "3.1%"]]}, "sources": ["국가법령정보센터"], "warning": "이 출력은 mock JSON입니다."}',
    "Markdown 표/리스트 출력": "장애인 의무고용률은 다음과 같습니다.\n\n| 구분 | 의무고용률 |\n| --- | --- |\n| 공공기관 | 3.8% |\n| 민간기업 | 3.1% |\n\n- 상시근로자 50인 이상\n- 이행하지 않을 경우 부담금 발생\n",
    "HTML 혼합 출력": "<div>장애인고용촉진법 제28조에 따라...</div>\n\n- 공공기관: 3.8%\n- 민간기업: 3.1%\n",
    "잘못된 테이블 포맷": "구분 | 의무고용률\n공공기관 | 3.8%\n민간기업 | 3.1%\n",
}


def parse_json(text: str) -> dict | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        logger.warning(
            "llm_json_parse_failed",
            error=str(error),
            response_length=len(text),
        )
        return None


def parse_markdown_table(text: str) -> pd.DataFrame | None:
    lines = [line.strip() for line in text.splitlines() if "|" in line]
    if len(lines) < 2:
        logger.info(
            "llm_markdown_table_parse_skipped",
            pipe_line_count=len(lines),
            reason="not_enough_table_lines",
        )
        return None

    header_line = lines[0]
    separator_line = lines[1]
    if not re.match(r"^\|?\s*[-:]+", separator_line):
        logger.warning(
            "llm_markdown_table_parse_failed",
            reason="invalid_separator_line",
            separator_line=separator_line,
        )
        return None

    headers = [h.strip() for h in header_line.strip("|").split("|")]
    rows = []
    for line in lines[2:]:
        columns = [c.strip() for c in line.strip("|").split("|")]
        if len(columns) == len(headers):
            rows.append(columns)

    if not rows:
        logger.warning(
            "llm_markdown_table_parse_failed",
            header_count=len(headers),
            reason="no_matching_rows",
        )
        return None

    logger.info(
        "llm_markdown_table_parse_succeeded",
        column_count=len(headers),
        row_count=len(rows),
    )
    return pd.DataFrame(rows, columns=headers)


def parse_bullet_list(text: str) -> list[str]:
    return [line.strip()[2:] for line in text.splitlines() if line.strip().startswith("- ")]


def render_llm_parsing() -> None:
    st.title("LLM 출력 파싱 테스트")
    st.write(
        "여러 유형의 mock LLM 출력을 넣어서 JSON, markdown 표, 리스트를 각각 파싱해보는 테스트 페이지입니다."
    )

    status = getattr(st, "status", None)
    if status:
        status("파싱 테스트 준비 완료")
    else:
        st.info("파싱 테스트 준비 완료")

    selected_example = st.selectbox("샘플 LLM 출력 선택", list(SAMPLE_OUTPUTS.keys()))
    raw_text = SAMPLE_OUTPUTS[selected_example]
    logger.info(
        "llm_response_received",
        response_length=len(raw_text),
        sample_name=selected_example,
        source="mock_sample",
    )

    st.subheader("원본 LLM 출력")
    st.code(raw_text, language="markdown")

    st.subheader("파싱 결과")
    parsed_json = parse_json(raw_text)
    if parsed_json is not None:
        logger.info(
            "llm_json_parse_succeeded",
            field_count=len(parsed_json),
            sample_name=selected_example,
        )
        st.markdown("**JSON 파싱 성공**")
        st.json(parsed_json)
    else:
        logger.info(
            "llm_fallback_parsing_started",
            sample_name=selected_example,
        )
        st.markdown("**JSON 파싱 실패 — markdown/table parsing 시도**")
        table = parse_markdown_table(raw_text)
        if table is not None:
            st.markdown("**마크다운 표 파싱 결과**")
            st.dataframe(table, use_container_width=True)
        else:
            st.warning("표 형태 파싱에 실패했습니다.")

        bullets = parse_bullet_list(raw_text)
        logger.info(
            "llm_bullet_list_parsed",
            item_count=len(bullets),
            sample_name=selected_example,
        )
        if bullets:
            st.markdown("**리스트 항목 추출**")
            for item in bullets:
                st.write(f"- {item}")
        else:
            st.info("리스트 항목이 없습니다.")

    st.markdown("---")
    st.write("이 페이지는 백엔드가 없는 상태에서 LLM 출력 형태별 parser를 검증하는 용도입니다.")
