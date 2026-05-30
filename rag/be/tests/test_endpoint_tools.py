from __future__ import annotations

import unittest

from agents.graph_ingest.schemas import RegisteredDocument
from agents.graph_ingest.sub_agents.chunking_agent import ChunkingAgent
from agents.graph_ingest.sub_agents.feedback_judge_agent import FeedbackJudgeAgent
from agents.graph_ingest.sub_agents.graph_candidate_agent import GraphCandidateAgent
from agents.graph_ingest.sub_agents.graph_candidate_revision_agent import (
    GraphCandidateRevisionAgent,
)
from api.mcp import create_external_mcp
from tools import AgentToolContext, bind_agent_tool_context, count_occurrences_tool


class FakeQueryService:
    def read_query(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN201
        return {}

    def vector_search(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN201
        return {}

    def text_search(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN201
        return {}

    def graph_traverse(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN201
        return {}

    def schema_read(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN201
        return {}

    def store_chunks(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN201
        return {}

    def store_edge_candidates(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN201
        return {}

    def probe_existing_context(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN201
        return {}

    def find_review_notes(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN201
        return {}

    def get_ingest_progress(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN201
        return {}

    def get_document_raw_content(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN201
        return "alpha beta alpha"


class EndpointToolsTest(unittest.TestCase):
    def test_chunking_agent_has_context_bound_chunk_tools(self) -> None:
        document = RegisteredDocument(
            id="doc-1",
            entry_number=1,
            content_hash="hash",
            raw_content="alpha beta alpha",
            file_name="sample.txt",
            source_type="txt",
        )
        tools = ChunkingAgent().tools()
        tool_names = {tool.name for tool in tools}

        self.assertEqual(tool_names, {"count_occurrences_tool", "write_chunk_tool"})
        self._assert_no_runtime_context_schema(tools)
        context = AgentToolContext(
            job_id="job-1",
            document_id=document.id,
            agent_name="chunking_agent",
            operation_scope="chunking",
        )
        with bind_agent_tool_context(context, raw_content=document.raw_content):
            self.assertEqual(count_occurrences_tool.invoke({"text": "alpha"}), 2)

    def test_graph_candidate_agent_has_context_bound_candidate_tools(self) -> None:
        tools = GraphCandidateAgent().tools()
        tool_names = {tool.name for tool in tools}

        self.assertIn("memgraph_read_query", tool_names)
        self.assertIn("memgraph_text_search", tool_names)
        self.assertIn("memgraph_vector_search", tool_names)
        self.assertIn("memgraph_graph_traverse", tool_names)
        self.assertIn("memgraph_schema_read", tool_names)
        self.assertIn("memgraph_probe_existing_context", tool_names)
        self.assertIn("write_relationship_candidate_tool", tool_names)
        self.assertIn("get_reviewer_notes_tool", tool_names)
        self.assertNotIn("memgraph_write_query", tool_names)
        self.assertNotIn("memgraph_store_edge_candidates", tool_names)
        self._assert_no_runtime_context_schema(tools)

    def test_feedback_judge_agent_has_bound_ingest_state_tool(self) -> None:
        tools = FeedbackJudgeAgent().tools()
        tool_names = {tool.name for tool in tools}

        self.assertEqual(
            tool_names,
            {"memgraph_schema_read", "memgraph_read_query", "get_ingest_state_tool"},
        )
        self._assert_no_runtime_context_schema(tools)

    def test_revision_agent_has_context_bound_revision_tool(self) -> None:
        tools = GraphCandidateRevisionAgent().tools()
        tool_names = {tool.name for tool in tools}

        self.assertIn("memgraph_read_query", tool_names)
        self.assertIn("memgraph_graph_traverse", tool_names)
        self.assertIn("write_candidate_revision_tool", tool_names)
        self.assertIn("get_reviewer_notes_tool", tool_names)
        self.assertNotIn("memgraph_write_query", tool_names)
        self._assert_no_runtime_context_schema(tools)

    def test_external_mcp_is_read_only_surface(self) -> None:
        tool_manager = create_external_mcp(FakeQueryService())._tool_manager
        tool_names = set(tool_manager._tools)

        self.assertIn("memgraph.read_query", tool_names)
        self.assertIn("memgraph.schema_read", tool_names)
        self.assertIn("memgraph.text_search", tool_names)
        self.assertIn("memgraph.vector_search", tool_names)
        self.assertNotIn("memgraph.keyword_search", tool_names)
        self.assertNotIn("memgraph.write_query", tool_names)
        self.assertNotIn("memgraph.upsert_document_graph", tool_names)
        self.assertNotIn("write_relationship_candidate_tool", tool_names)

    def _assert_no_runtime_context_schema(self, tools) -> None:  # noqa: ANN001
        forbidden = {"job_id", "task_id", "dry_run", "mock", "preview", "no_op"}
        for item in tools:
            self.assertTrue(
                forbidden.isdisjoint(set(item.args)),
                f"{item.name} exposes forbidden args: {set(item.args).intersection(forbidden)}",
            )


if __name__ == "__main__":
    unittest.main()
