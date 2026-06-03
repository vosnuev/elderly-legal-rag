from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from pipeline.sub_agents.chunking_agent import (
    SYSTEM_PROMPT,
    ChunkingAgent,
    ChunkingAgentOutput,
    _agent_input,
)
from settings import settings


class FakeEventStream:
    def __init__(self, events: list[tuple[str, object]], output: dict) -> None:
        self.events = events
        self.output = output
        self.extensions = {
            "messages": object(),
            "values": object(),
            "lifecycle": object(),
        }

    def interleave(self, *names):  # noqa: ANN001, ANN201
        requested = set(names)
        for event in self.events:
            if event[0] in requested:
                yield event


class FakeStreamingAgent:
    def __init__(self, result: dict) -> None:
        self.result = result
        self.stream_events_calls: list[dict] = []

    def stream_events(self, agent_input, config=None, version=None):  # noqa: ANN001, ANN201
        self.stream_events_calls.append(
            {
                "agent_input": agent_input,
                "config": config,
                "version": version,
            }
        )
        return FakeEventStream(
            events=[
                ("lifecycle", {"event": "start"}),
                ("messages", {"content_blocks": [{"type": "text", "text": "stored"}]}),
                ("values", self.result),
            ],
            output=self.result,
        )


class FakeFailingStreamingAgent:
    def __init__(self, exc: Exception) -> None:
        self.exc = exc
        self.stream_events_calls: list[dict] = []

    def stream_events(self, agent_input, config=None, version=None):  # noqa: ANN001, ANN201
        self.stream_events_calls.append(
            {
                "agent_input": agent_input,
                "config": config,
                "version": version,
            }
        )
        raise self.exc


class TestableChunkingAgent(ChunkingAgent):
    def __init__(
        self,
        fake_agent: FakeStreamingAgent | list[FakeStreamingAgent],
    ) -> None:
        super().__init__()
        self._fake_agents = (
            fake_agent
            if isinstance(fake_agent, list)
            else [fake_agent]
        )
        self.create_agent_calls: list[dict] = []

    def create_agent(  # noqa: ANN001, ANN201
        self,
        tools=None,
        *,
        use_default_provider: bool = True,
    ):
        self.create_agent_calls.append(
            {"tools": tools, "use_default_provider": use_default_provider}
        )
        return self._fake_agents.pop(0)


class ChunkingAgentRunTest(unittest.TestCase):
    def test_prompt_forbids_unknown_tool_names(self) -> None:
        user_content = _agent_input("doc-1")["messages"][0]["content"]

        self.assertIn("commentary", SYSTEM_PROMPT)
        self.assertIn("provided tool names", user_content)
        self.assertIn("Never call commentary", user_content)

    def test_prompt_sets_long_document_chunking_criteria(self) -> None:
        user_content = _agent_input("doc-1")["messages"][0]["content"]

        self.assertIn("10,000자를 넘으면 최소 8개 chunk", SYSTEM_PROMPT)
        self.assertIn("800~2,200자", SYSTEM_PROMPT)
        self.assertIn("3,000자를 넘기지 않는다", SYSTEM_PROMPT)
        self.assertIn("조문단위", SYSTEM_PROMPT)
        self.assertIn("chunk_name", SYSTEM_PROMPT)
        self.assertIn("chunk_description", SYSTEM_PROMPT)
        self.assertIn("review queue", SYSTEM_PROMPT)
        self.assertIn("at least 8 chunks", user_content)
        self.assertIn("Target 800 to 2200", user_content)
        self.assertIn("must not store the entire document as one chunk", user_content)
        self.assertIn("chunk_name", user_content)
        self.assertIn("chunk_description", user_content)
        self.assertIn("multiple times in small batches", user_content)
        self.assertIn("chunk_index=1", user_content)
        self.assertIn("write_chunk_tool은 여러 번 호출할 수 있다", SYSTEM_PROMPT)

    def test_tools_exclude_boundary_verification_tool(self) -> None:
        tool_names = [tool.name for tool in ChunkingAgent().tools()]

        self.assertEqual(tool_names, ["read_document_tool", "write_chunk_tool"])

    def test_run_returns_chunk_ids_from_structured_response(self) -> None:
        fake_agent = FakeStreamingAgent(
            {
                "structured_response": ChunkingAgentOutput(
                    chunk_ids=["chunk-1", "chunk-2"]
                )
            }
        )
        agent = TestableChunkingAgent(fake_agent)

        with patch(
            "pipeline.sub_agents.chunking_agent.list_chunks_for_document",
            side_effect=AssertionError(
                "DB guard should not run when structured response has chunk ids."
            ),
        ):
            result = agent.run(job_id="job-1", document_id="doc-1")

        self.assertEqual(result, ["chunk-1", "chunk-2"])
        self.assertEqual(
            fake_agent.stream_events_calls[0]["config"],
            {"recursion_limit": settings.chunking_agent_tool_budget},
        )
        self.assertEqual(fake_agent.stream_events_calls[0]["version"], "v3")

    def test_run_with_events_returns_agent_events(self) -> None:
        fake_agent = FakeStreamingAgent(
            {
                "structured_response": ChunkingAgentOutput(
                    chunk_ids=["chunk-1"]
                )
            }
        )
        agent = TestableChunkingAgent(fake_agent)

        result = agent.run_with_events(job_id="job-1", document_id="doc-1")

        self.assertEqual(result.chunk_ids, ["chunk-1"])
        self.assertEqual(
            [event.channel for event in result.agent_events],
            ["lifecycle", "messages", "values"],
        )
        self.assertEqual(
            result.agent_events[1].payload,
            {"content_blocks": [{"type": "text", "text": "stored"}]},
        )

    def test_run_uses_document_chunk_guard_when_agent_result_misses_ids(self) -> None:
        fake_agent = FakeStreamingAgent({})
        agent = TestableChunkingAgent(fake_agent)

        with patch(
            "pipeline.sub_agents.chunking_agent.list_chunks_for_document",
            return_value={
                "rows": [
                    {
                        "chunk": {
                            "properties": {
                                "id": "chunk-current",
                                "last_ingest_job_id": "job-1",
                            }
                        }
                    },
                    {
                        "chunk": {
                            "properties": {
                                "id": "chunk-old",
                                "last_ingest_job_id": "job-0",
                            }
                        }
                    },
                ]
            },
        ):
            result = agent.run(job_id="job-1", document_id="doc-1")

        self.assertEqual(result, ["chunk-current"])

    def test_run_retries_without_provider_when_preferred_route_writes_no_chunks(
        self,
    ) -> None:
        fake_settings = SimpleNamespace(
            chunking_agent_tool_budget=settings.chunking_agent_tool_budget,
            graph_llm_provider="cerebras",
            graph_llm_retry_without_provider=True,
            graph_llm_request_timeout_seconds=60,
            graph_llm_stream_chunk_timeout_seconds=60,
            graph_llm_max_retries=2,
        )
        fake_agents = [FakeStreamingAgent({}), FakeStreamingAgent({})]
        agent = TestableChunkingAgent(fake_agents)

        with (
            patch("pipeline.sub_agents.chunking_agent.settings", fake_settings),
            patch(
                "pipeline.sub_agents.chunking_agent.list_chunks_for_document",
                side_effect=[
                    {"rows": []},
                    {
                        "rows": [
                            {
                                "chunk": {
                                    "properties": {
                                        "id": "chunk-retried",
                                        "last_ingest_job_id": "job-1",
                                    }
                                }
                            }
                        ]
                    },
                ],
            ),
        ):
            result = agent.run_with_events(job_id="job-1", document_id="doc-1")

        self.assertEqual(result.chunk_ids, ["chunk-retried"])
        self.assertEqual(
            [
                call["use_default_provider"]
                for call in agent.create_agent_calls
            ],
            [True, False],
        )
        self.assertEqual(len(result.agent_events), 6)

    def test_run_retries_without_provider_when_stream_times_out(self) -> None:
        fake_settings = SimpleNamespace(
            chunking_agent_tool_budget=settings.chunking_agent_tool_budget,
            graph_llm_provider="groq",
            graph_llm_retry_without_provider=True,
            graph_llm_request_timeout_seconds=60,
            graph_llm_stream_chunk_timeout_seconds=60,
            graph_llm_max_retries=2,
        )
        first_agent = FakeFailingStreamingAgent(TimeoutError("stream stalled"))
        second_agent = FakeStreamingAgent({})
        agent = TestableChunkingAgent([first_agent, second_agent])

        with (
            patch("pipeline.sub_agents.chunking_agent.settings", fake_settings),
            patch(
                "pipeline.sub_agents.chunking_agent.list_chunks_for_document",
                side_effect=[
                    {"rows": []},
                    {
                        "rows": [
                            {
                                "chunk": {
                                    "properties": {
                                        "id": "chunk-after-timeout",
                                        "last_ingest_job_id": "job-1",
                                    }
                                }
                            }
                        ]
                    },
                ],
            ),
        ):
            result = agent.run_with_events(job_id="job-1", document_id="doc-1")

        self.assertEqual(result.chunk_ids, ["chunk-after-timeout"])
        self.assertEqual(
            [
                call["use_default_provider"]
                for call in agent.create_agent_calls
            ],
            [True, False],
        )
        self.assertEqual(len(first_agent.stream_events_calls), 1)
        self.assertEqual(len(second_agent.stream_events_calls), 1)


if __name__ == "__main__":
    unittest.main()
