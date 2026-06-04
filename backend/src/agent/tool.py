from __future__ import annotations

import asyncio
import re

from langchain_core.tools import BaseTool, ToolException
from langchain_mcp_adapters.client import MultiServerMCPClient

from logger import get_logger
from settings import settings

logger = get_logger(__name__)

_TOOLS_CACHE: list[BaseTool] | None = None
_TOOLS_LOCK: asyncio.Lock | None = None
_UNSAFE_TOOL_NAME_CHARS = re.compile(r"[^a-zA-Z0-9_-]")


def _tools_lock() -> asyncio.Lock:
    global _TOOLS_LOCK
    if _TOOLS_LOCK is None:
        _TOOLS_LOCK = asyncio.Lock()
    return _TOOLS_LOCK


def _safe_tool_name(name: str) -> str:
    safe_name = _UNSAFE_TOOL_NAME_CHARS.sub("_", name).strip("_")
    return safe_name or "rag_mcp_tool"


def _normalize_tool_names(tools: list[BaseTool]) -> list[BaseTool]:
    used_names: set[str] = set()
    for tool in tools:
        original_name = tool.name
        safe_name = _safe_tool_name(original_name)
        if safe_name in used_names:
            suffix = 2
            candidate = f"{safe_name}_{suffix}"
            while candidate in used_names:
                suffix += 1
                candidate = f"{safe_name}_{suffix}"
            safe_name = candidate

        used_names.add(safe_name)
        if safe_name == original_name:
            continue

        logger.info(
            "renaming MCP tool for LangChain compatibility original=%s safe=%s",
            original_name,
            safe_name,
        )
        tool.name = safe_name
        original_description = tool.description or ""
        tool.description = (
            f"{original_description}\nOriginal MCP tool name: {original_name}."
            if original_description
            else f"Original MCP tool name: {original_name}."
        )

    return tools


def _tool_error_message(error: ToolException) -> str:
    return (
        "RAG 도구 실행 중 오류가 발생했습니다. 이 도구 결과는 근거로 사용하지 말고, "
        f"다른 검색 도구나 이미 확인된 근거로 답변을 계속 작성하세요. 오류: {error}"
    )


def _handle_tool_errors(tools: list[BaseTool]) -> list[BaseTool]:
    for tool in tools:
        tool.handle_tool_error = _tool_error_message
        tool.handle_validation_error = (
            "RAG 도구 입력값이 올바르지 않습니다. 다른 검색 도구나 더 단순한 "
            "키워드로 다시 조회하세요."
        )
    return tools


async def _load_rag_mcp_tools() -> list[BaseTool]:
    client = MultiServerMCPClient(
        {
            "rag": {
                "transport": "http",
                "url": settings.rag_mcp_url,
            }
        }
    )
    tools = await asyncio.wait_for(
        client.get_tools(server_name="rag"),
        timeout=settings.tool_timeout_ms / 1000,
    )
    return _handle_tool_errors(_normalize_tool_names(tools))


# 현재 agent가 사용할 LangChain tool 목록 반환
async def get_tools() -> list[BaseTool]:
    global _TOOLS_CACHE
    if not settings.enable_rag_tools:
        logger.info("RAG MCP tools disabled by configuration")
        return []

    if _TOOLS_CACHE is not None:
        return _TOOLS_CACHE

    async with _tools_lock():
        if _TOOLS_CACHE is not None:
            return _TOOLS_CACHE

        tools = await _load_rag_mcp_tools()
        if not tools:
            raise RuntimeError("RAG MCP server returned no tools.")

        _TOOLS_CACHE = tools
        logger.info(
            "loaded RAG MCP tools url=%s tools=%s",
            settings.rag_mcp_url,
            [tool.name for tool in tools],
        )
        return _TOOLS_CACHE


def clear_tools_cache() -> None:
    global _TOOLS_CACHE
    _TOOLS_CACHE = None
