from __future__ import annotations

from langchain_core.tools import BaseTool, tool

from logger import get_logger


logger = get_logger(__name__)


# LangSmith tool call 검증용 mock 검색 tool
@tool
def mock_policy_search_tool(query: str) -> str:
    """기초연금, 복지 정책, 신청 방법 질문을 검증용 mock 문서에서 검색합니다."""
    logger.info("mock_policy_search_tool called query=%s", query)
    return (
        "mock 검색 결과: 기초연금은 만 65세 이상 어르신 중 소득인정액 기준을 "
        "충족하는 경우 신청할 수 있습니다. 신청은 주소지 관할 읍면동 주민센터 "
        "또는 국민연금공단 지사에서 할 수 있습니다."
    )


# RAG MCP 연결 전까지 agent에 붙일 임시 검색 tool
@tool
def rag_search_tool(query: str) -> str:
    """사용자 질문과 관련된 정보를 찾기 위해 외부 RAG 문서를 검색합니다."""
    return "RAG 검색 도구는 아직 연결되지 않았습니다."


# 현재 agent가 사용할 LangChain tool 목록 반환
def get_tools() -> list[BaseTool]:
    return [mock_policy_search_tool, rag_search_tool]
