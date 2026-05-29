from __future__ import annotations

from langchain_core.tools import BaseTool

from agents.graph_ingest.tools import get_graph_ingest_tools
from query.service import MemgraphQueryService


class GraphIngestAgent:
    def __init__(self, service: MemgraphQueryService | None = None) -> None:
        self._tools = get_graph_ingest_tools(service)

    @property
    def tools(self) -> list[BaseTool]:
        return self._tools

    def tool_names(self) -> list[str]:
        return [tool.name for tool in self._tools]
