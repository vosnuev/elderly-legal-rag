from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch

from mcp.server.fastmcp.exceptions import ToolError

from pipeline.sub_agents.chunking_agent import ChunkingAgent
from pipeline.sub_agents.feedback_judge_agent import FeedbackJudgeAgent
from pipeline.sub_agents.graph_candidate_agent import GraphCandidateAgent
from pipeline.sub_agents.graph_candidate_revision_agent import (
    GraphCandidateRevisionAgent,
)
from tools import (
    check_document_unique_string_tool,
    write_chunk_tool,
    write_relationship_candidate_tool,
)
from api.mcp import create_external_mcp


class EndpointToolsTest(unittest.TestCase):
    def test_chunking_agent_has_explicit_chunk_tools(self) -> None:
        tools = ChunkingAgent().tools()
        tool_names = {tool.name for tool in tools}

        self.assertEqual(
            tool_names,
            {
                "check_document_unique_string_tool",
                "read_document_tool",
                "write_chunk_tool",
            },
        )
        self._assert_no_runtime_context_schema(tools)
        with patch(
            "tools.chunk_tools.get_document_raw_content",
            return_value="alpha beta alpha",
        ):
            self.assertEqual(
                check_document_unique_string_tool.invoke(
                    {"document_id": "doc-1", "text": "beta"}
                ),
                {
                    "document_id": "doc-1",
                    "is_unique": True,
                    "occurrence_count": 1,
                    "first_start_char": 6,
                    "first_end_char": 10,
                    "text_length": 4,
                },
            )

    def test_check_document_unique_string_tool_has_structured_schema(self) -> None:
        schema = check_document_unique_string_tool.args_schema.model_json_schema()

        self.assertEqual(schema["additionalProperties"], False)
        self.assertIn("document_id", schema["properties"])
        self.assertIn("text", schema["properties"])
        self.assertNotIn("job_id", schema["properties"])

    def test_graph_candidate_agent_has_explicit_candidate_tools(self) -> None:
        tools = GraphCandidateAgent().tools()
        tool_names = {tool.name for tool in tools}

        self.assertIn("memgraph_read_query", tool_names)
        self.assertIn("memgraph_text_index_search", tool_names)
        self.assertIn("memgraph_vector_search", tool_names)
        self.assertIn("memgraph_graph_traverse", tool_names)
        self.assertIn("memgraph_schema_read", tool_names)
        self.assertIn("memgraph_probe_existing_context", tool_names)
        self.assertIn("write_relationship_candidate_tool", tool_names)
        self.assertIn("get_reviewer_notes_tool", tool_names)
        self.assertNotIn("memgraph_write_query", tool_names)
        self.assertNotIn("memgraph_store_edge_candidates", tool_names)
        self._assert_no_runtime_context_schema(tools)

    def test_feedback_judge_agent_has_read_tools(self) -> None:
        tools = FeedbackJudgeAgent().tools()
        tool_names = {tool.name for tool in tools}

        self.assertEqual(
            tool_names,
            {
                "memgraph_schema_read",
                "memgraph_read_query",
                "memgraph_graph_traverse",
            },
        )
        self._assert_no_runtime_context_schema(tools)

    def test_revision_agent_has_explicit_revision_tool(self) -> None:
        tools = GraphCandidateRevisionAgent().tools()
        tool_names = {tool.name for tool in tools}

        self.assertIn("memgraph_read_query", tool_names)
        self.assertIn("memgraph_graph_traverse", tool_names)
        self.assertIn("write_candidate_revision_tool", tool_names)
        self.assertIn("get_reviewer_notes_tool", tool_names)
        self.assertNotIn("memgraph_write_query", tool_names)
        self._assert_no_runtime_context_schema(tools)

    def test_external_mcp_is_read_only_surface(self) -> None:
        tool_manager = create_external_mcp()._tool_manager
        tool_names = set(tool_manager._tools)

        self.assertIn("memgraph.read_query", tool_names)
        self.assertIn("memgraph.schema_read", tool_names)
        self.assertIn("memgraph.text_index_search", tool_names)
        self.assertNotIn("memgraph.text_search", tool_names)
        self.assertIn("memgraph.vector_search", tool_names)
        self.assertNotIn("memgraph.keyword_search", tool_names)
        self.assertNotIn("memgraph.write_query", tool_names)
        self.assertNotIn("memgraph.upsert_document_graph", tool_names)
        self.assertNotIn("write_relationship_candidate_tool", tool_names)

    def test_external_mcp_read_query_applies_read_wrapper_limit(self) -> None:
        tool_manager = create_external_mcp()._tool_manager

        with (
            patch("api.mcp.server.bounded_limit", return_value=17) as bounded_limit,
            patch("api.mcp.server.read_query", return_value={"rows": []}) as read_query,
        ):
            result = asyncio.run(
                tool_manager.call_tool(
                    "memgraph.read_query",
                    {
                        "query": "MATCH (n) RETURN n",
                        "parameters": {"name": "alpha"},
                    },
                )
            )

        self.assertEqual(result, {"rows": []})
        bounded_limit.assert_called_once_with(None)
        read_query.assert_called_once_with(
            "MATCH (n) RETURN n",
            {"name": "alpha"},
            17,
        )

    def test_external_mcp_read_query_rejects_write_cypher(self) -> None:
        tool_manager = create_external_mcp()._tool_manager

        with patch("api.mcp.server.read_query") as read_query:
            with self.assertRaisesRegex(ToolError, "read-only Cypher"):
                asyncio.run(
                    tool_manager.call_tool(
                        "memgraph.read_query",
                        {"query": "MATCH (n) SET n.name = 'blocked' RETURN n"},
                    )
                )

        read_query.assert_not_called()

    def test_write_chunk_tool_has_structured_chunk_schema(self) -> None:
        schema = write_chunk_tool.args_schema.model_json_schema()
        chunk_schema = schema["$defs"]["ChunkWriteInput"]
        chunk_fields = chunk_schema["properties"]

        self.assertEqual(schema["additionalProperties"], False)
        self.assertEqual(chunk_schema["additionalProperties"], False)
        self.assertIn("chunks", schema["properties"])
        self.assertIn("document_id", schema["properties"])
        self.assertNotIn("id", chunk_fields)
        self.assertIn("chunk_index", chunk_fields)
        self.assertIn("start_unique_string", chunk_fields)
        self.assertIn("end_unique_string", chunk_fields)
        self.assertNotIn("job_id", chunk_fields)
        self.assertNotIn("document_id", chunk_fields)

    def test_write_relationship_candidate_tool_has_structured_edge_schema(self) -> None:
        schema = write_relationship_candidate_tool.args_schema.model_json_schema()
        candidate_schema = schema["$defs"]["EdgeCandidateWriteInput"]
        candidate_fields = candidate_schema["properties"]

        self.assertEqual(schema["additionalProperties"], False)
        self.assertEqual(candidate_schema["additionalProperties"], False)
        self.assertIn("candidates", schema["properties"])
        self.assertIn("left_node", candidate_fields)
        self.assertIn("right_node", candidate_fields)
        self.assertIn("relationship_type", candidate_fields)
        self.assertIn("relationship_direction", candidate_fields)
        self.assertIn("evidence_text", candidate_fields)
        self.assertIn("evidence_node_id", candidate_fields)
        self.assertNotIn("id", candidate_fields)
        self.assertNotIn("source_chunk_id", candidate_fields)
        self.assertNotIn("status", candidate_fields)
        self.assertNotIn("version", candidate_fields)
        self.assertNotIn("job_id", candidate_fields)
        self.assertNotIn("document_id", candidate_fields)

    def _assert_no_runtime_context_schema(self, tools) -> None:  # noqa: ANN001
        forbidden = {"job_id", "task_id", "dry_run", "mock", "preview", "no_op"}
        for item in tools:
            self.assertTrue(
                forbidden.isdisjoint(set(item.args)),
                f"{item.name} exposes forbidden args: {set(item.args).intersection(forbidden)}",
            )


if __name__ == "__main__":
    unittest.main()
