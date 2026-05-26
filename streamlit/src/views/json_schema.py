import streamlit as st

from structured_logging import get_logger

logger = get_logger(__name__)


RESPONSE_SCHEMA = {
    "summary": "string",
    "details": ["string"],
    "laws": [{"name": "string", "article": "string"}],
    "table": {"headers": ["string"], "rows": [["string"]]},
    "sources": ["string"],
    "warning": "string"
}


def render_json_schema() -> None:
    logger.info(
        "json_schema_view_rendered",
        field_count=len(RESPONSE_SCHEMA),
        fields=list(RESPONSE_SCHEMA.keys()),
        schema_name="response_schema",
    )

    st.title("응답 JSON 스키마")
    st.write(
        "프론트는 markdown 대신 구조화된 JSON 응답을 백엔드에서 받는 것이 안정적인 렌더링의 핵심입니다."
    )
    st.markdown(
        "### 권장 응답 구조\n"
        "```json\n"
        "{\n"
        "  \"summary\": \"...\",\n"
        "  \"details\": [\"...\"],\n"
        "  \"laws\": [{\"name\": \"...\", \"article\": \"...\"}],\n"
        "  \"table\": {\"headers\": [\"...\"], \"rows\": [[\"...\"]]},\n"
        "  \"sources\": [\"...\"],\n"
        "  \"warning\": \"...\"\n"
        "}\n"
        "```"
    )
    st.json(RESPONSE_SCHEMA)
    st.markdown("### 각 필드 역할")
    st.write(
        "- `summary`: 핵심 요약 텍스트\n"
        "- `details`: 상세 설명 리스트\n"
        "- `laws`: 관련 법령 카드 데이터\n"
        "- `table`: 자동 표 렌더링 데이터\n"
        "- `sources`: 출처 목록\n"
        "- `warning`: 사용자에게 보여줄 경고 메시지"
    )
    st.warning(
        "프론트는 markdown 파싱에 의존하지 않고, 이 JSON 스키마를 기준으로 모든 UI를 구성해야 합니다."
    )
