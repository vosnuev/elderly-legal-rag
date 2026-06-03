from __future__ import annotations

import json
import unittest
from dataclasses import dataclass
from unittest.mock import patch

from pipeline.agent_runtime.event_stream import AgentEventStreamLogger


class FakeEventStream:
    def __init__(self, *, output: object | None = None) -> None:
        self.extensions = {
            "messages": object(),
            "tool_calls": object(),
            "values": object(),
        }
        self.values_output = {"structured_response": {"chunk_ids": ["chunk-1"]}}
        self.output = self.values_output if output is None else output

    def interleave(self, *names):  # noqa: ANN001, ANN201
        requested = set(names)
        for event in [
            ("messages", {"content_blocks": [{"type": "text", "text": "토큰"}]}),
            ("tool_calls", {"tool_name": "write_chunk_tool", "input": {"x": 1}}),
            ("values", self.values_output),
        ]:
            if event[0] in requested:
                yield event


class FakeRawEventStream:
    def __init__(self, *, output: object | None = None) -> None:
        self.values_output = {"structured_response": {"chunk_ids": ["chunk-raw"]}}
        self.output = self.values_output if output is None else output

    def __iter__(self):  # noqa: ANN204
        yield {
            "method": "messages",
            "params": {
                "data": (
                    {
                        "event": "content-block-delta",
                        "delta": {"type": "text-delta", "text": "raw token"},
                    },
                    {"langgraph_node": "model"},
                )
            },
        }
        yield {
            "method": "tools",
            "params": {
                "data": {
                    "event": "tool-started",
                    "tool_call_id": "tool-1",
                    "tool_name": "write_chunk_tool",
                    "input": {"x": 1},
                }
            },
        }
        yield {
            "method": "values",
            "params": {"data": self.values_output},
        }


class FakeNoisyRawEventStream:
    def __init__(self) -> None:
        self.output = {}

    def __iter__(self):  # noqa: ANN204
        huge_args = "{" + "\"chunks\":[" + ("x" * 5_000)
        yield {
            "method": "messages",
            "params": {
                "data": (
                    {"event": "message-start", "role": "ai", "id": "message-1"},
                    {"ls_model_name": "openai/gpt-oss-120b"},
                )
            },
        }
        yield {
            "method": "messages",
            "params": {
                "data": (
                    {
                        "event": "content-block-delta",
                        "delta": {
                            "type": "block-delta",
                            "fields": {
                                "type": "tool_call_chunk",
                                "id": "tool-1",
                                "name": "write_chunk_tool",
                                "args": huge_args,
                            },
                        },
                    },
                    {"ls_model_name": "openai/gpt-oss-120b"},
                )
            },
        }
        yield {
            "method": "messages",
            "params": {
                "data": (
                    {
                        "event": "content-block-finish",
                        "content": {
                            "type": "tool_call",
                            "id": "tool-1",
                            "name": "write_chunk_tool",
                            "args": {
                                "document_id": "doc-1",
                                "chunks": [
                                    {
                                        "chunk_index": 1,
                                        "chunk_name": "제1조 목적",
                                        "chunk_description": "목적 조항",
                                        "text": "a" * 2_000,
                                    },
                                    {
                                        "chunk_index": 2,
                                        "chunk_name": "제2조 정의",
                                        "chunk_description": "정의 조항",
                                        "text": "b" * 3_000,
                                    },
                                ],
                            },
                        },
                    },
                    {"ls_model_name": "openai/gpt-oss-120b"},
                )
            },
        }
        yield {
            "method": "tools",
            "params": {
                "data": {
                    "event": "tool-finished",
                    "tool_call_id": "tool-2",
                    "tool_name": "read_document_tool",
                    "output": {
                        "content": json.dumps(
                            {
                                "document_id": "doc-1",
                                "raw_content": ("z" * 5_000) + "UNSAFE_TAIL",
                            }
                        )
                    },
                }
            },
        }
        yield {
            "method": "tools",
            "params": {
                "data": {
                    "event": "tool-finished",
                    "tool_call_id": "tool-3",
                    "tool_name": "read_document_tool",
                    "output": FakeToolMessage(
                        {
                            "content": json.dumps(
                                {
                                    "document_id": "doc-2",
                                    "raw_content": ("y" * 4_000) + "MODEL_DUMP_TAIL",
                                }
                            ),
                            "status": "success",
                        }
                    ),
                }
            },
        }
        yield {
            "method": "values",
            "params": {
                "data": {
                    "messages": [
                        {
                            "type": "tool",
                            "content": ("v" * 5_000) + "UNSAFE_TAIL",
                        },
                        {
                            "type": "ai",
                            "tool_calls": [
                                {
                                    "name": "write_chunk_tool",
                                    "args": {
                                        "chunks": [
                                            {"chunk_index": 1, "text": "c" * 5_000}
                                        ]
                                    },
                                }
                            ],
                        },
                    ]
                }
            },
        }


@dataclass
class FakeToolMessage:
    payload: dict[str, object]

    def model_dump(self):  # noqa: ANN201
        return self.payload


class FakeAgent:
    def __init__(self, *, stream_output: object | None = None) -> None:
        self._stream_output = stream_output

    def stream_events(self, agent_input, config=None, version=None):  # noqa: ANN001, ANN201
        return FakeEventStream(output=self._stream_output)


class FakeRawAgent:
    def __init__(self, *, stream_output: object | None = None) -> None:
        self._stream_output = stream_output

    def stream_events(self, agent_input, config=None, version=None):  # noqa: ANN001, ANN201
        return FakeRawEventStream(output=self._stream_output)


class FakeNoisyRawAgent:
    def stream_events(self, agent_input, config=None, version=None):  # noqa: ANN001, ANN201
        return FakeNoisyRawEventStream()


class FakeLogger:
    def bind(self, **kwargs):  # noqa: ANN003, ANN201
        return self

    def info(self, message: str) -> None:
        _ = message

    def warning(self, message: str) -> None:
        _ = message


class FakeObserver:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def agent_from_thread(self, **kwargs):  # noqa: ANN003, ANN201
        self.events.append(kwargs)
        return "event-id"


class AgentEventStreamLoggerTest(unittest.TestCase):
    def test_stream_events_are_published_to_observability(self) -> None:
        fake_observer = FakeObserver()

        with patch("pipeline.agent_runtime.event_stream.observer", fake_observer):
            result = AgentEventStreamLogger(
                FakeLogger(),
                agent_name="chunking_agent",
                agent_context={"job_id": "job-1", "document_id": "doc-1"},
            ).run_with_events(
                agent=FakeAgent(),
                agent_input={"messages": []},
                config={},
            )

        self.assertEqual(result.output, {"structured_response": {"chunk_ids": ["chunk-1"]}})
        self.assertEqual([event.channel for event in result.events], ["messages", "tool_calls", "values"])
        self.assertEqual(len(fake_observer.events), 3)
        self.assertEqual(fake_observer.events[0]["job_id"], "job-1")
        self.assertEqual(fake_observer.events[0]["agent_name"], "chunking_agent")
        self.assertEqual(fake_observer.events[0]["token"], "토큰")
        self.assertEqual(fake_observer.events[0]["data"]["document_id"], "doc-1")
        self.assertEqual(
            fake_observer.events[1]["tool_usage"],
            {"tool_name": "write_chunk_tool", "input": {"x": 1}},
        )

    def test_raw_protocol_events_are_published_to_observability(self) -> None:
        fake_observer = FakeObserver()

        with patch("pipeline.agent_runtime.event_stream.observer", fake_observer):
            result = AgentEventStreamLogger(
                FakeLogger(),
                agent_name="chunking_agent",
            ).run_with_events(
                agent=FakeRawAgent(),
                agent_input={"messages": []},
                config={},
            )

        self.assertEqual(result.output, {"structured_response": {"chunk_ids": ["chunk-raw"]}})
        self.assertEqual([event.channel for event in result.events], ["messages", "tools", "values"])
        self.assertEqual(fake_observer.events[0]["token"], "raw token")
        self.assertEqual(fake_observer.events[1]["tool_usage"]["tool_name"], "write_chunk_tool")
        self.assertEqual(fake_observer.events[1]["tool_usage"]["event"], "tool-started")

    def test_projection_values_event_is_used_when_stream_output_is_empty(self) -> None:
        fake_observer = FakeObserver()

        with patch("pipeline.agent_runtime.event_stream.observer", fake_observer):
            result = AgentEventStreamLogger(
                FakeLogger(),
                agent_name="chunking_agent",
            ).run_with_events(
                agent=FakeAgent(stream_output={}),
                agent_input={"messages": []},
                config={},
            )

        self.assertEqual(result.output, {"structured_response": {"chunk_ids": ["chunk-1"]}})

    def test_raw_values_event_is_used_when_stream_output_is_empty(self) -> None:
        fake_observer = FakeObserver()

        with patch("pipeline.agent_runtime.event_stream.observer", fake_observer):
            result = AgentEventStreamLogger(
                FakeLogger(),
                agent_name="chunking_agent",
            ).run_with_events(
                agent=FakeRawAgent(stream_output={}),
                agent_input={"messages": []},
                config={},
            )

        self.assertEqual(result.output, {"structured_response": {"chunk_ids": ["chunk-raw"]}})

    def test_noisy_tool_payloads_are_summarized_before_publish(self) -> None:
        fake_observer = FakeObserver()

        with patch("pipeline.agent_runtime.event_stream.observer", fake_observer):
            result = AgentEventStreamLogger(
                FakeLogger(),
                agent_name="chunking_agent",
            ).run_with_events(
                agent=FakeNoisyRawAgent(),
                agent_input={"messages": []},
                config={},
            )

        self.assertEqual(
            [event.channel for event in result.events],
            ["messages", "messages", "tools", "tools", "values"],
        )
        finish_payload = result.events[1].payload
        chunk_args = finish_payload["tool_call"]["args"]
        self.assertEqual(chunk_args["type"], "chunk_write_args")
        self.assertEqual(chunk_args["document_id"], "doc-1")
        self.assertEqual(chunk_args["chunk_count"], 2)
        self.assertEqual(chunk_args["chunk_indexes"], [1, 2])
        self.assertEqual(chunk_args["text_total_chars"], 5_000)
        self.assertEqual(chunk_args["omitted_chunk_count"], 0)
        self.assertEqual(len(chunk_args["chunk_previews"]), 2)
        self.assertEqual(
            chunk_args["chunk_previews"][0]["chunk_name"]["full"],
            "제1조 목적",
        )
        self.assertEqual(
            chunk_args["chunk_previews"][0]["chunk_description"]["full"],
            "목적 조항",
        )
        self.assertEqual(chunk_args["chunk_previews"][0]["text"]["chars"], 2_000)
        self.assertEqual(chunk_args["chunk_previews"][0]["text"]["full"], "a" * 2_000)
        self.assertEqual(chunk_args["chunk_previews"][1]["text"]["chars"], 3_000)
        self.assertEqual(chunk_args["chunk_previews"][1]["text"]["full"], "b" * 3_000)
        tool_output = result.events[2].payload["data"]["output"]
        self.assertEqual(tool_output["type"], "document")
        self.assertEqual(tool_output["raw_content_chars"], 5_011)
        model_dump_output = result.events[3].payload["data"]["output"]
        self.assertEqual(model_dump_output["type"], "document")
        self.assertEqual(model_dump_output["document_id"], "doc-2")
        self.assertEqual(model_dump_output["raw_content_chars"], 4_015)
        values_payload_text = str(result.events[4].payload)
        self.assertIn("message_count", values_payload_text)
        self.assertNotIn("UNSAFE_TAIL", values_payload_text)
        self.assertNotIn("MODEL_DUMP_TAIL", values_payload_text)
        self.assertEqual(len(fake_observer.events), 5)


if __name__ == "__main__":
    unittest.main()
