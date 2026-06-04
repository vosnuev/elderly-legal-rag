from __future__ import annotations

import asyncio
import threading
import time
import unittest
from unittest.mock import patch

from mcp.server.fastmcp.exceptions import ToolError

from pipeline.sub_agents.chunking_agent import ChunkingAgent
from pipeline.sub_agents.graph_candidate_agent import GraphCandidateAgent
from pipeline.sub_agents.graph_candidate_agent import SYSTEM_PROMPT as GRAPH_CANDIDATE_PROMPT
from pipeline.sub_agents.graph_candidate_agent import _candidate_worker_count
from pipeline.sub_agents.memory_update_agent import MemoryUpdateAgent
from pipeline.sub_agents.memory_update_agent import (
    SYSTEM_PROMPT as MEMORY_UPDATE_PROMPT,
)
from tools import (
    check_document_unique_string_tool,
    memgraph_read_query,
    read_chunk_context_tool,
    write_chunk_tool,
    write_memory_document_tool,
    write_relationship_candidate_tool,
)
from api.mcp import create_external_mcp
from settings import settings


class EndpointToolsTest(unittest.TestCase):
    def test_chunking_agent_has_explicit_chunk_tools(self) -> None:
        tools = ChunkingAgent().tools()
        tool_names = {tool.name for tool in tools}

        self.assertEqual(
            tool_names,
            {
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

    def test_read_chunk_context_tool_does_not_expose_embedding_toggle(self) -> None:
        schema = read_chunk_context_tool.args_schema.model_json_schema()

        self.assertEqual(schema["additionalProperties"], False)
        self.assertIn("chunk_id", schema["properties"])
        self.assertNotIn("include_embedding", schema["properties"])

    def test_read_chunk_context_tool_sanitizes_agent_context(self) -> None:
        with patch(
            "tools.chunk_tools.read_chunk_by_id",
            return_value={
                "id": "chunk-1",
                "text": "가" * 700,
                "summary": "summary",
                "metadata": {"large": "object"},
                "embedding": [0.1] * 3072,
            },
        ):
            result = read_chunk_context_tool.invoke({"chunk_id": "chunk-1"})

        self.assertEqual(result["id"], "chunk-1")
        self.assertLessEqual(len(result["text"]), 540)
        self.assertNotIn("metadata", result)
        self.assertNotIn("embedding", result)

    def test_graph_candidate_agent_has_explicit_candidate_tools(self) -> None:
        tools = GraphCandidateAgent().tools()
        tool_names = {tool.name for tool in tools}

        self.assertIn("memgraph_read_query", tool_names)
        self.assertIn("memgraph_text_index_search", tool_names)
        self.assertIn("memgraph_vector_search", tool_names)
        self.assertIn("memgraph_graph_traverse", tool_names)
        self.assertIn("memgraph_schema_read", tool_names)
        self.assertNotIn("read_document_tool", tool_names)
        self.assertIn("read_chunk_context_tool", tool_names)
        self.assertNotIn("read_chunk_tool", tool_names)
        self.assertNotIn("read_memory_tool", tool_names)
        self.assertIn("web_search_firecrawl_tool", tool_names)
        self.assertIn("write_relationship_candidate_tool", tool_names)
        self.assertNotIn("get_reviewer_notes_tool", tool_names)
        self.assertNotIn("write_memory_document_tool", tool_names)
        self.assertNotIn("memgraph_write_query", tool_names)
        self.assertNotIn("memgraph_store_edge_candidates", tool_names)
        self._assert_no_runtime_context_schema(tools)

    def test_graph_candidate_prompts_forbid_unknown_tool_names(self) -> None:
        for prompt in (GRAPH_CANDIDATE_PROMPT, MEMORY_UPDATE_PROMPT):
            self.assertIn("commentary", prompt)
            self.assertIn("제공된 tool 이름만 호출", prompt)

    def test_graph_candidate_prompt_forbids_original_document_context(self) -> None:
        tool_names = {tool.name for tool in GraphCandidateAgent().tools()}

        self.assertIn("Document.raw_content", GRAPH_CANDIDATE_PROMPT)
        self.assertIn("document_id를 시작점", GRAPH_CANDIDATE_PROMPT)
        self.assertIn("memgraph_read_query", GRAPH_CANDIDATE_PROMPT)
        self.assertIn("web_search_firecrawl_tool", GRAPH_CANDIDATE_PROMPT)
        self.assertIn("Agent Memory Context", GRAPH_CANDIDATE_PROMPT)
        self.assertNotIn("MCP_ASSIGNED_MEMGRAPH_TOOLS", GRAPH_CANDIDATE_PROMPT)
        self.assertNotIn("get_reviewer_notes_tool", GRAPH_CANDIDATE_PROMPT)
        self.assertIn("memgraph_query", GRAPH_CANDIDATE_PROMPT)
        self.assertNotIn("read_document_tool", tool_names)

    def test_graph_candidate_agent_runs_chunk_agents_concurrently(self) -> None:
        agent = GraphCandidateAgent()
        active_count = 0
        max_active_count = 0
        lock = threading.Lock()
        calls: list[str] = []

        def fake_run_for_chunk(
            *,
            job_id: str,
            document_id: str,
            chunk_id: str,
            memory_context: dict[str, object],
        ) -> None:
            nonlocal active_count, max_active_count
            _ = (job_id, document_id, memory_context)
            with lock:
                active_count += 1
                max_active_count = max(max_active_count, active_count)
            time.sleep(0.03)
            with lock:
                calls.append(chunk_id)
                active_count -= 1

        with (
            patch.object(settings, "graph_candidate_worker_count", 2),
            patch(
                "pipeline.sub_agents.graph_candidate_agent._stored_candidate_ids",
                side_effect=[["old-candidate"], ["old-candidate", "new-candidate"]],
            ),
            patch(
                "pipeline.sub_agents.graph_candidate_agent._memory_context",
                return_value={"content": "prefer narrow candidates"},
            ),
            patch.object(agent, "_run_for_chunk", side_effect=fake_run_for_chunk),
        ):
            result = agent.run(
                job_id="job-1",
                document_id="doc-1",
                chunk_ids=["chunk-1", "chunk-2", "chunk-3"],
            )

        self.assertEqual(result, ["new-candidate"])
        self.assertCountEqual(calls, ["chunk-1", "chunk-2", "chunk-3"])
        self.assertEqual(max_active_count, 2)

    def test_graph_candidate_agent_keeps_written_candidates_after_chunk_error(self) -> None:
        agent = GraphCandidateAgent()

        def fake_run_for_chunk(
            *,
            job_id: str,
            document_id: str,
            chunk_id: str,
            memory_context: dict[str, object],
        ) -> None:
            _ = (job_id, document_id, memory_context)
            if chunk_id == "chunk-2":
                raise RuntimeError("provider rejected wrong tool name")

        with (
            patch.object(settings, "graph_candidate_worker_count", 3),
            patch(
                "pipeline.sub_agents.graph_candidate_agent._stored_candidate_ids",
                side_effect=[["old-candidate"], ["old-candidate", "new-candidate"]],
            ),
            patch(
                "pipeline.sub_agents.graph_candidate_agent._memory_context",
                return_value={"content": "prefer narrow candidates"},
            ),
            patch.object(agent, "_run_for_chunk", side_effect=fake_run_for_chunk),
        ):
            result = agent.run(
                job_id="job-1",
                document_id="doc-1",
                chunk_ids=["chunk-1", "chunk-2", "chunk-3"],
            )

        self.assertEqual(result, ["new-candidate"])

    def test_graph_candidate_agent_raises_when_all_chunk_errors_write_nothing(self) -> None:
        agent = GraphCandidateAgent()

        with (
            patch.object(settings, "graph_candidate_worker_count", 2),
            patch(
                "pipeline.sub_agents.graph_candidate_agent._stored_candidate_ids",
                side_effect=[[], []],
            ),
            patch(
                "pipeline.sub_agents.graph_candidate_agent._memory_context",
                return_value={"content": "prefer narrow candidates"},
            ),
            patch.object(
                agent,
                "_run_for_chunk",
                side_effect=RuntimeError("provider rejected wrong tool name"),
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "provider rejected"):
                agent.run(
                    job_id="job-1",
                    document_id="doc-1",
                    chunk_ids=["chunk-1", "chunk-2"],
                )

    def test_graph_candidate_worker_count_is_bounded_by_chunk_count(self) -> None:
        with patch.object(settings, "graph_candidate_worker_count", 5):
            self.assertEqual(_candidate_worker_count(2), 2)
            self.assertEqual(_candidate_worker_count(0), 1)

    def test_memory_update_agent_has_explicit_memory_write_tool(self) -> None:
        tools = MemoryUpdateAgent().tools()
        tool_names = {tool.name for tool in tools}

        self.assertIn("memgraph_read_query", tool_names)
        self.assertIn("memgraph_schema_read", tool_names)
        self.assertIn("memgraph_text_index_search", tool_names)
        self.assertIn("memgraph_vector_search", tool_names)
        self.assertIn("memgraph_graph_traverse", tool_names)
        self.assertIn("read_chunk_context_tool", tool_names)
        self.assertIn("write_memory_document_tool", tool_names)
        self.assertNotIn("read_document_tool", tool_names)
        self.assertNotIn("write_relationship_candidate_tool", tool_names)
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

    def test_external_mcp_read_query_sanitizes_context_heavy_fields(self) -> None:
        tool_manager = create_external_mcp()._tool_manager
        raw_result = {
            "columns": ["document"],
            "rows": [
                {
                    "document": {
                        "type": "node",
                        "labels": ["Document"],
                        "element_id": "doc-element-1",
                        "properties": {
                            "id": "doc-1",
                            "title": "근로기준법",
                            "raw_content": "원문" * 1000,
                            "embedding": [0.1] * 3072,
                            "metadata": {"large": "object"},
                        },
                    }
                }
            ],
            "row_count": 1,
            "elapsed_ms": 1.2,
            "query": "MATCH (document:Document) RETURN document",
            "counters": {"contains_updates": False},
        }

        with patch("api.mcp.server.read_query", return_value=raw_result):
            result = asyncio.run(
                tool_manager.call_tool(
                    "memgraph.read_query",
                    {"query": "MATCH (document:Document) RETURN document"},
                )
            )

        self.assertTrue(result["sanitized"])
        self.assertNotIn("query", result)
        self.assertNotIn("counters", result)
        properties = result["rows"][0]["document"]["properties"]
        self.assertEqual(properties["id"], "doc-1")
        self.assertNotIn("raw_content", properties)
        self.assertNotIn("embedding", properties)
        self.assertNotIn("metadata", properties)

    def test_external_mcp_read_query_logs_invocation_summary(self) -> None:
        tool_manager = create_external_mcp()._tool_manager

        with (
            patch("api.mcp.server._logger") as logger,
            patch(
                "api.mcp.server.read_query",
                return_value={
                    "columns": ["id"],
                    "rows": [{"id": "chunk-1"}],
                    "row_count": 1,
                },
            ),
        ):
            result = asyncio.run(
                tool_manager.call_tool(
                    "memgraph.read_query",
                    {
                        "query": "MATCH (chunk:Chunk) RETURN chunk.id AS id",
                        "parameters": {"limit": 1},
                    },
                )
            )

        self.assertEqual(result["row_count"], 1)
        logger.bind.assert_called_once()
        log_context = logger.bind.call_args.kwargs
        self.assertEqual(log_context["tool_name"], "memgraph.read_query")
        self.assertEqual(
            log_context["input_summary"],
            {
                "query_preview": "MATCH (chunk:Chunk) RETURN chunk.id AS id",
                "has_parameters": True,
                "parameter_keys": ["limit"],
                "max_rows": None,
            },
        )
        invocation_logger = logger.bind.return_value
        invocation_logger.info.assert_any_call("MCP tool invocation started")
        completion_context = invocation_logger.bind.call_args.kwargs
        self.assertEqual(completion_context["result_summary"]["row_count"], 1)
        self.assertEqual(completion_context["result_summary"]["returned_row_count"], 1)
        invocation_logger.bind.return_value.info.assert_called_once_with(
            "MCP tool invocation completed"
        )

    def test_external_mcp_read_query_rejects_write_cypher(self) -> None:
        tool_manager = create_external_mcp()._tool_manager

        with (
            patch("api.mcp.server._logger"),
            patch("api.mcp.server.read_query") as read_query,
        ):
            with self.assertRaisesRegex(ToolError, "read-only Cypher"):
                asyncio.run(
                    tool_manager.call_tool(
                        "memgraph.read_query",
                        {"query": "MATCH (n) SET n.name = 'blocked' RETURN n"},
                    )
                )

        read_query.assert_not_called()

    def test_agent_memgraph_read_query_sanitizes_context_heavy_fields(self) -> None:
        raw_result = {
            "columns": ["chunk"],
            "rows": [
                {
                    "chunk": {
                        "type": "node",
                        "labels": ["Chunk"],
                        "element_id": "1",
                        "properties": {
                            "id": "chunk-1",
                            "text": "가" * 700,
                            "summary": "summary",
                            "embedding": [0.1] * 3072,
                            "raw_content": "원문" * 1000,
                            "metadata": {"large": "object"},
                        },
                    }
                }
            ],
            "row_count": 1,
            "elapsed_ms": 1.2,
            "query": "MATCH (chunk:Chunk) RETURN chunk",
            "counters": {"contains_updates": False},
        }

        with patch(
            "tools.memgraph_read_tools.read_query",
            return_value=raw_result,
        ) as read_query:
            result = memgraph_read_query.invoke(
                {
                    "query": "MATCH (chunk:Chunk) RETURN chunk",
                    "max_rows": 100,
                }
            )

        read_query.assert_called_once_with(
            "MATCH (chunk:Chunk) RETURN chunk",
            None,
            20,
        )
        self.assertTrue(result["sanitized"])
        self.assertNotIn("query", result)
        self.assertNotIn("counters", result)
        properties = result["rows"][0]["chunk"]["properties"]
        self.assertEqual(properties["id"], "chunk-1")
        self.assertLessEqual(len(properties["text"]), 540)
        self.assertNotIn("embedding", properties)
        self.assertNotIn("raw_content", properties)
        self.assertNotIn("metadata", properties)
        self.assertEqual(
            set(properties["_omitted_properties"]),
            {"embedding", "raw_content", "metadata"},
        )

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
        self.assertIn("chunk_name", chunk_fields)
        self.assertIn("chunk_description", chunk_fields)
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

    def test_write_relationship_candidate_tool_uses_chunk_job_provenance(self) -> None:
        with (
            patch(
                "tools.candidate_tools.read_node_by_id",
                return_value={
                    "id": "chunk-1",
                    "metadata": {},
                    "last_ingest_job_id": "job-1",
                },
            ),
            patch(
                "tools.candidate_tools.write_relationship_candidates",
                return_value={"rows": [{"stored_count": 1}]},
            ) as write_candidates,
        ):
            write_relationship_candidate_tool.invoke(
                {
                    "candidates": [
                        {
                            "left_node": "chunk-1",
                            "right_node": "chunk-2",
                            "relationship_type": "RELATED_TO",
                            "relationship_direction": "left_to_right",
                            "evidence_text": "evidence",
                            "rationale": "rationale",
                            "evidence_node_id": "chunk-1",
                        }
                    ]
                }
            )

        written = write_candidates.call_args.args[0][0]
        self.assertEqual(written["job_id"], "job-1")

    def test_write_memory_document_tool_schema_replaces_single_memory_document(self) -> None:
        schema = write_memory_document_tool.args_schema.model_json_schema()

        self.assertEqual(schema["additionalProperties"], False)
        self.assertIn("content", schema["properties"])
        self.assertIn("scope", schema["properties"])
        self.assertIn("title", schema["properties"])
        self.assertIn("update_summary", schema["properties"])
        self.assertIn("evidence_review_note_ids", schema["properties"])
        self.assertIn("evidence_candidate_ids", schema["properties"])
        self.assertNotIn("memory_kind", schema["properties"])
        self.assertNotIn("job_id", schema["properties"])

    def _assert_no_runtime_context_schema(self, tools) -> None:  # noqa: ANN001
        forbidden = {"job_id", "task_id", "dry_run", "mock", "preview", "no_op"}
        for item in tools:
            self.assertTrue(
                forbidden.isdisjoint(set(item.args)),
                f"{item.name} exposes forbidden args: {set(item.args).intersection(forbidden)}",
            )


if __name__ == "__main__":
    unittest.main()
