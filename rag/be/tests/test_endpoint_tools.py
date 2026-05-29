from __future__ import annotations

import unittest

from agents.graph_ingest.tools import get_graph_ingest_tools
from api.mcp import create_external_mcp


class FakeQueryService:
    def read_query(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN201
        return {}

    def write_query(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN201
        return {}

    def vector_search(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN201
        return {}

    def keyword_search(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN201
        return {}

    def graph_traverse(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN201
        return {}

    def schema_read(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN201
        return {}

    def upsert_document_graph(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN201
        return {}

    def store_edge_candidates(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN201
        return {}

    def probe_existing_context(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN201
        return {}

    def review_edge_candidate(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN201
        return {}


class EndpointToolsTest(unittest.TestCase):
    def test_internal_langchain_tools_include_read_and_write_tools(self) -> None:
        tool_names = {tool.name for tool in get_graph_ingest_tools(FakeQueryService())}

        self.assertIn("memgraph_read_query", tool_names)
        self.assertIn("memgraph_write_query", tool_names)
        self.assertIn("memgraph_upsert_document_graph", tool_names)
        self.assertIn("memgraph_probe_existing_context", tool_names)

    def test_external_mcp_is_read_only_surface(self) -> None:
        tool_manager = create_external_mcp(FakeQueryService())._tool_manager
        tool_names = set(tool_manager._tools)

        self.assertIn("memgraph.read_query", tool_names)
        self.assertIn("memgraph.schema_read", tool_names)
        self.assertNotIn("memgraph.write_query", tool_names)
        self.assertNotIn("memgraph.upsert_document_graph", tool_names)


if __name__ == "__main__":
    unittest.main()
