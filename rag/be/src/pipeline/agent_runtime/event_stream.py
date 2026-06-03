# 역할: LangChain/LangGraph agent 실행 중 발생한 stream event를 observability로 전달한다.
from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from langchain_core.runnables import Runnable
from observability.consume.service import observer
from pydantic import BaseModel

_NO_OUTPUT = object()
_MAX_EVENT_TEXT_CHARS = 500
_MAX_PREVIEW_CHARS = 240
_MAX_EVENT_ITEMS = 8


class AgentEventStreamEvent(BaseModel):
    """Agent 실행 중 관측된 단일 stream event.

    hidden reasoning이 아니라 LangChain/LangGraph가 외부로 노출한 messages/tools/values
    같은 runtime event payload만 담는다.
    """

    channel: str
    payload: Any


@dataclass
class AgentEventStreamRun:
    """Agent 실행 결과와 관측용 event 목록을 함께 돌려주는 내부 DTO."""

    output: object
    events: list[AgentEventStreamEvent] = field(default_factory=list)


class AgentEventStreamLogger:
    """Agent stream_events(version="v3")를 읽어 process log와 Redis에 publish한다.

    이 클래스는 UI용 formatting을 소유하지 않는다. Redis에는 raw-ish event payload를
    넣고, 화면에서 어떻게 보여줄지는 FE가 결정한다.
    """

    def __init__(
        self,
        logger: Any,
        *,
        agent_name: str = "agent",
        agent_context: dict[str, Any] | None = None,
    ) -> None:
        self._logger = logger
        self._agent_name = agent_name
        self._agent_context = {
            key: str(value)
            for key, value in (agent_context or {}).items()
            if value is not None
        }

    def run(
        self,
        *,
        agent: Runnable,
        agent_input: dict[str, Any],
        config: dict[str, Any],
    ) -> object:
        return self.run_with_events(
            agent=agent,
            agent_input=agent_input,
            config=config,
        ).output

    def run_with_events(
        self,
        *,
        agent: Runnable,
        agent_input: dict[str, Any],
        config: dict[str, Any],
    ) -> AgentEventStreamRun:
        try:
            stream = agent.stream_events(
                agent_input,
                config=config,
                version="v3",
            )
        except (AttributeError, NotImplementedError):
            self._logger.warning(
                "agent stream_events unavailable; falling back to invoke"
            )
            return AgentEventStreamRun(output=agent.invoke(agent_input, config=config))

        events: list[AgentEventStreamEvent] = []
        latest_output: object = _NO_OUTPUT
        try:
            for raw_event in stream:
                output_candidate = _raw_output_candidate(raw_event)
                if output_candidate is not _NO_OUTPUT:
                    latest_output = output_candidate
                event = _raw_event_stream_event(raw_event)
                if event is None or _skip_observability_event(event):
                    continue
                events.append(event)
                self._logger.bind(**event.model_dump()).info(
                    "agent event stream event"
                )
                self._publish(event)
        except TypeError:
            latest_output = _NO_OUTPUT
            for channel, payload in self._projection_events(stream):
                output_candidate = _projection_output_candidate(channel, payload)
                if output_candidate is not _NO_OUTPUT:
                    latest_output = output_candidate
                event = AgentEventStreamEvent(
                    channel=channel,
                    payload=_observable_payload(channel, payload),
                )
                if _skip_observability_event(event):
                    continue
                events.append(event)
                self._logger.bind(**event.model_dump()).info(
                    "agent event stream event"
                )
                self._publish(event)

        return AgentEventStreamRun(
            output=_final_stream_output(stream, latest_output),
            events=events,
        )

    def _projection_events(self, stream: Any) -> Iterable[tuple[str, Any]]:
        for channel, payload in stream.interleave(*_stream_channel_names(stream)):
            yield channel, payload

    def _publish(self, event: AgentEventStreamEvent) -> None:
        # Redis channel name stays agent_transcript for FE/backward compatibility.
        # The module/class names use "event_stream" to avoid implying hidden
        # chain-of-thought capture.
        observer.agent_from_thread(
            job_id=self._agent_context.get("job_id"),
            task_id=self._agent_context.get("task_id"),
            kind=self._agent_context.get("kind"),
            agent_name=self._agent_name,
            stage="agent_stream",
            log=_agent_event_log(event),
            token=_agent_event_token(event),
            tool_usage=_agent_event_tool_usage(event),
            data={
                **self._agent_context,
                "streamChannel": event.channel,
                "payload": event.payload,
            },
        )


def _stream_channel_names(stream: Any) -> list[str]:
    extensions = getattr(stream, "extensions", None)
    if isinstance(extensions, dict) and extensions:
        return list(extensions)
    return [
        name
        for name in (
            "messages",
            "tool_calls",
            "values",
            "updates",
            "lifecycle",
            "subgraphs",
        )
        if getattr(stream, name, None) is not None
    ]


def _raw_event_stream_event(raw_event: Any) -> AgentEventStreamEvent | None:
    if not isinstance(raw_event, dict):
        return None
    channel = str(raw_event.get("method") or raw_event.get("event") or "event")
    params = raw_event.get("params")
    payload = params if isinstance(params, dict) else raw_event
    return AgentEventStreamEvent(
        channel=channel,
        payload=_observable_payload(channel, payload),
    )


def _skip_observability_event(event: AgentEventStreamEvent) -> bool:
    """Drop noisy streaming fragments after they have served output tracking.

    LangGraph emits a `content-block-delta` for every growing tool-call argument
    string. For large chunk writes this can flood Redis and process logs with
    repeated partial JSON. We keep message/tool start and finish events, and
    only drop the repetitive tool-call delta fragments.
    """
    if event.channel != "messages" or not isinstance(event.payload, dict):
        return False
    tool_call = event.payload.get("tool_call")
    return (
        event.payload.get("event") == "content-block-delta"
        and isinstance(tool_call, dict)
        and tool_call.get("phase") == "delta"
    )


def _observable_payload(channel: str, payload: Any) -> Any:
    if channel == "values":
        return _sanitize_values_payload(payload)
    if channel == "messages":
        return _sanitize_messages_payload(payload)
    if channel == "tools":
        return _sanitize_tools_payload(payload)
    return _loggable_payload(
        payload,
        max_text=_MAX_EVENT_TEXT_CHARS,
        max_items=_MAX_EVENT_ITEMS,
    )


def _sanitize_values_payload(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return _loggable_payload(
            payload,
            max_text=_MAX_EVENT_TEXT_CHARS,
            max_items=_MAX_EVENT_ITEMS,
        )
    data = payload.get("data")
    if not isinstance(data, dict):
        return _copy_event_envelope(payload)

    messages = data.get("messages")
    structured_response = data.get("structured_response")
    result: dict[str, Any] = _copy_event_envelope(payload)
    if isinstance(messages, list):
        result["message_count"] = len(messages)
        result["recent_messages"] = [
            _summarize_chat_message(message)
            for message in messages[-3:]
        ]
    if structured_response is not None:
        result["structured_response"] = _summarize_structured_response(
            structured_response
        )
    interrupts = payload.get("interrupts")
    if isinstance(interrupts, list):
        result["interrupt_count"] = len(interrupts)
    return result


def _sanitize_messages_payload(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return _loggable_payload(
            payload,
            max_text=_MAX_EVENT_TEXT_CHARS,
            max_items=_MAX_EVENT_ITEMS,
        )
    data = payload.get("data")
    result = _copy_event_envelope(payload)
    if isinstance(data, (list, tuple)) and data:
        event_payload = data[0]
        metadata = data[1] if len(data) > 1 else None
        if isinstance(event_payload, dict):
            result.update(_summarize_message_stream_event(event_payload))
        if isinstance(metadata, dict):
            result["metadata"] = _summarize_stream_metadata(metadata)
        return result
    if isinstance(data, dict):
        result.update(_summarize_message_stream_event(data))
        return result
    return _loggable_payload(
        payload,
        max_text=_MAX_EVENT_TEXT_CHARS,
        max_items=_MAX_EVENT_ITEMS,
    )


def _sanitize_tools_payload(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return _loggable_payload(
            payload,
            max_text=_MAX_EVENT_TEXT_CHARS,
            max_items=_MAX_EVENT_ITEMS,
        )
    data = payload.get("data")
    result = _copy_event_envelope(payload)
    if not isinstance(data, dict):
        return result

    sanitized_data: dict[str, Any] = {
        "event": data.get("event"),
        "tool_call_id": data.get("tool_call_id"),
        "tool_name": data.get("tool_name"),
    }
    if "input" in data:
        sanitized_data["input"] = _summarize_tool_arguments(data.get("input"))
    if "output" in data:
        sanitized_data["output"] = _summarize_tool_output(data.get("output"))
    if "message" in data:
        sanitized_data["message"] = _text_summary(data.get("message"))
    if "error" in data:
        sanitized_data["error"] = _text_summary(data.get("error"))
    result["data"] = {
        key: value
        for key, value in sanitized_data.items()
        if value is not None
    }
    return result


def _copy_event_envelope(payload: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in ("namespace", "timestamp"):
        if key in payload:
            result[key] = _loggable_payload(
                payload[key],
                max_text=_MAX_EVENT_TEXT_CHARS,
                max_items=_MAX_EVENT_ITEMS,
            )
    return result


def _summarize_message_stream_event(event_payload: dict[str, Any]) -> dict[str, Any]:
    event_name = event_payload.get("event")
    result: dict[str, Any] = {"event": event_name}
    if "role" in event_payload:
        result["role"] = event_payload.get("role")
    if "id" in event_payload:
        result["id"] = event_payload.get("id")
    if "usage" in event_payload:
        result["usage"] = _loggable_payload(
            event_payload.get("usage"),
            max_text=_MAX_EVENT_TEXT_CHARS,
            max_items=_MAX_EVENT_ITEMS,
        )
    metadata = event_payload.get("metadata")
    if isinstance(metadata, dict):
        result["metadata"] = _summarize_stream_metadata(metadata)

    for key in ("content", "delta"):
        value = event_payload.get(key)
        if isinstance(value, dict):
            result.update(_summarize_content_block(value, event_name=event_name))
        elif value is not None:
            result[key] = _summarize_content(value)
    return result


def _summarize_content_block(
    block: dict[str, Any],
    *,
    event_name: Any,
) -> dict[str, Any]:
    block_type = block.get("type")
    if block_type == "text-delta":
        return {"text": _truncate_text(str(block.get("text") or ""))}
    if block_type == "block-delta":
        fields = block.get("fields")
        if isinstance(fields, dict):
            return _summarize_content_block(fields, event_name=event_name)
    if block_type in {"tool_call", "tool_call_chunk"}:
        phase = "delta" if event_name == "content-block-delta" else "complete"
        return {
            "tool_call": {
                "phase": phase,
                "type": block_type,
                "id": block.get("id"),
                "name": block.get("name"),
                "args": _summarize_tool_arguments(block.get("args")),
            }
        }
    if block_type == "text":
        return {"text": _truncate_text(str(block.get("text") or ""))}
    return {
        "content": _loggable_payload(
            block,
            max_text=_MAX_EVENT_TEXT_CHARS,
            max_items=_MAX_EVENT_ITEMS,
        )
    }


def _summarize_stream_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    keep_keys = (
        "provider",
        "model_provider",
        "model_name",
        "finish_reason",
        "ls_model_name",
        "ls_provider",
        "ls_model_type",
        "langgraph_node",
        "langgraph_step",
        "run_id",
    )
    return {
        key: _loggable_payload(
            metadata.get(key),
            max_text=_MAX_EVENT_TEXT_CHARS,
            max_items=_MAX_EVENT_ITEMS,
        )
        for key in keep_keys
        if key in metadata
    }


def _summarize_chat_message(message: Any) -> dict[str, Any]:
    if hasattr(message, "model_dump"):
        message = message.model_dump()
    if not isinstance(message, dict):
        return {"value": _text_summary(message)}

    result: dict[str, Any] = {
        key: message.get(key)
        for key in ("type", "name", "id", "status", "tool_call_id")
        if message.get(key) is not None
    }
    response_metadata = message.get("response_metadata")
    if isinstance(response_metadata, dict):
        result["response_metadata"] = _summarize_stream_metadata(response_metadata)
    usage_metadata = message.get("usage_metadata")
    if isinstance(usage_metadata, dict):
        result["usage_metadata"] = _loggable_payload(
            usage_metadata,
            max_text=_MAX_EVENT_TEXT_CHARS,
            max_items=_MAX_EVENT_ITEMS,
        )

    content = message.get("content")
    if content is not None:
        result["content"] = _summarize_content(content)

    tool_calls = message.get("tool_calls")
    if isinstance(tool_calls, list) and tool_calls:
        result["tool_calls"] = [
            _summarize_tool_call(tool_call)
            for tool_call in tool_calls[:_MAX_EVENT_ITEMS]
        ]
        result["tool_call_count"] = len(tool_calls)

    invalid_tool_calls = message.get("invalid_tool_calls")
    if isinstance(invalid_tool_calls, list) and invalid_tool_calls:
        result["invalid_tool_call_count"] = len(invalid_tool_calls)
        result["invalid_tool_calls"] = [
            _summarize_tool_call(tool_call)
            for tool_call in invalid_tool_calls[:_MAX_EVENT_ITEMS]
        ]
    return result


def _summarize_content(content: Any) -> Any:
    if isinstance(content, str):
        parsed = _try_parse_json(content)
        if parsed is not None:
            return _summarize_tool_output(parsed)
        return _text_summary(content)
    if isinstance(content, list):
        return {
            "type": "blocks",
            "count": len(content),
            "items": [
                _summarize_content(block)
                for block in content[:_MAX_EVENT_ITEMS]
            ],
        }
    if isinstance(content, dict):
        block_summary = _summarize_content_block(
            content,
            event_name=content.get("event"),
        )
        return block_summary.get("content", block_summary)
    return _loggable_payload(
        content,
        max_text=_MAX_EVENT_TEXT_CHARS,
        max_items=_MAX_EVENT_ITEMS,
    )


def _summarize_tool_call(tool_call: Any) -> dict[str, Any]:
    if hasattr(tool_call, "model_dump"):
        tool_call = tool_call.model_dump()
    if not isinstance(tool_call, dict):
        return {"value": _text_summary(tool_call)}
    result = {
        key: tool_call.get(key)
        for key in ("name", "id", "type", "error")
        if tool_call.get(key) is not None
    }
    if "args" in tool_call:
        result["args"] = _summarize_tool_arguments(tool_call.get("args"))
    return result


def _summarize_tool_arguments(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return _summarize_tool_arguments(value.model_dump())
    if isinstance(value, str):
        parsed = _try_parse_json(value)
        if parsed is not None:
            return _summarize_tool_arguments(parsed)
        return {
            "type": "string",
            "chars": len(value),
            "preview": _truncate_text(value, _MAX_PREVIEW_CHARS),
        }
    if isinstance(value, dict):
        if "chunks" in value and isinstance(value["chunks"], list):
            chunks = value["chunks"]
            return {
                "type": "chunk_write_args",
                "document_id": value.get("document_id"),
                "chunk_count": len(chunks),
                "chunk_indexes": [
                    chunk.get("chunk_index")
                    for chunk in chunks[:_MAX_EVENT_ITEMS]
                    if isinstance(chunk, dict)
                ],
                # Tool argument observability must stay bounded, but developers
                # still need to inspect whether the agent made sensible chunk
                # boundaries. Keep a short per-chunk preview instead of only
                # exposing aggregate counts.
                "chunk_previews": [
                    _summarize_chunk_write_item(chunk)
                    for chunk in chunks[:_MAX_EVENT_ITEMS]
                    if isinstance(chunk, dict)
                ],
                "omitted_chunk_count": max(len(chunks) - _MAX_EVENT_ITEMS, 0),
                "text_total_chars": sum(
                    len(str(chunk.get("text") or ""))
                    for chunk in chunks
                    if isinstance(chunk, dict)
                ),
            }
        summarized: dict[str, Any] = {}
        for key, item in list(value.items())[:_MAX_EVENT_ITEMS]:
            if key in {"raw_content", "text", "content", "query"}:
                summarized[key] = _text_summary(item)
            else:
                summarized[key] = _summarize_tool_arguments(item)
        if len(value) > _MAX_EVENT_ITEMS:
            summarized["_omitted_keys"] = len(value) - _MAX_EVENT_ITEMS
        return summarized
    if isinstance(value, list):
        return {
            "type": "list",
            "count": len(value),
            "items": [
                _summarize_tool_arguments(item)
                for item in value[:_MAX_EVENT_ITEMS]
            ],
        }
    return _loggable_payload(
        value,
        max_text=_MAX_EVENT_TEXT_CHARS,
        max_items=_MAX_EVENT_ITEMS,
    )


def _summarize_chunk_write_item(chunk: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "chunk_index": chunk.get("chunk_index"),
        "chunk_name": _text_summary(chunk.get("chunk_name"), include_full=True),
        "chunk_description": _text_summary(
            chunk.get("chunk_description"),
            include_full=True,
        ),
        "text": _text_summary(chunk.get("text"), include_full=True),
    }
    for key in (
        "summary",
        "boundary_reason",
        "start_unique_string",
        "end_unique_string",
    ):
        if key in chunk:
            result[key] = _text_summary(chunk.get(key), include_full=True)
    if "tags" in chunk:
        result["tags"] = _summarize_tool_arguments(chunk.get("tags"))
    if "metadata" in chunk:
        result["metadata"] = _summarize_tool_arguments(chunk.get("metadata"))
    return result


def _summarize_tool_output(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return _summarize_tool_output(value.model_dump())
    if isinstance(value, dict) and isinstance(value.get("content"), str):
        parsed = _try_parse_json(value["content"])
        if parsed is not None:
            return _summarize_tool_output(parsed)
        return {
            "type": "tool_content",
            "content": _text_summary(value["content"]),
            "status": value.get("status"),
        }
    if isinstance(value, dict):
        if "raw_content" in value:
            return {
                "type": "document",
                "document_id": value.get("document_id"),
                "raw_content_chars": len(str(value.get("raw_content") or "")),
            }
        if "rows" in value and isinstance(value["rows"], list):
            return {
                "type": "query_result",
                "columns": value.get("columns"),
                "row_count": value.get("row_count", len(value["rows"])),
                "returned_row_count": value.get("returned_row_count"),
                "sanitized": value.get("sanitized"),
            }
        if "chunk_ids" in value:
            chunk_ids = value.get("chunk_ids")
            return {
                "type": "chunk_write_result",
                "chunk_count": len(chunk_ids) if isinstance(chunk_ids, list) else None,
                "chunk_ids": chunk_ids[:_MAX_EVENT_ITEMS]
                if isinstance(chunk_ids, list)
                else chunk_ids,
            }
        summarized: dict[str, Any] = {}
        for key, item in list(value.items())[:_MAX_EVENT_ITEMS]:
            summarized[key] = _summarize_tool_arguments(item)
        if len(value) > _MAX_EVENT_ITEMS:
            summarized["_omitted_keys"] = len(value) - _MAX_EVENT_ITEMS
        return summarized
    return _summarize_tool_arguments(value)


def _summarize_structured_response(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        value = value.model_dump()
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if isinstance(item, list):
                result[key] = {
                    "count": len(item),
                    "items": item[:_MAX_EVENT_ITEMS],
                }
            else:
                result[key] = _summarize_tool_arguments(item)
        return result
    return _summarize_tool_arguments(value)


def _text_summary(value: Any, *, include_full: bool = False) -> dict[str, Any]:
    text = "" if value is None else str(value)
    result = {
        "type": "text",
        "chars": len(text),
        "preview": _truncate_text(text, _MAX_PREVIEW_CHARS),
    }
    if len(text) > _MAX_PREVIEW_CHARS:
        result["truncated_chars"] = len(text) - _MAX_PREVIEW_CHARS
    if include_full:
        result["full"] = text
    return result


def _truncate_text(value: str, max_chars: int = _MAX_EVENT_TEXT_CHARS) -> str:
    return value if len(value) <= max_chars else f"{value[:max_chars]}..."


def _try_parse_json(value: str) -> Any | None:
    stripped = value.strip()
    if not stripped or stripped[0] not in "[{":
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return None


def _raw_output_candidate(raw_event: Any) -> object:
    if not isinstance(raw_event, dict):
        return _NO_OUTPUT
    channel = str(raw_event.get("method") or raw_event.get("event") or "")
    if channel != "values":
        return _NO_OUTPUT
    params = raw_event.get("params")
    if not isinstance(params, dict) or "data" not in params:
        return _NO_OUTPUT
    return params["data"]


def _projection_output_candidate(channel: str, payload: Any) -> object:
    if channel != "values":
        return _NO_OUTPUT
    return payload


def _final_stream_output(stream: Any, latest_output: object) -> object:
    stream_output = getattr(stream, "output", None)
    if _has_structured_response(latest_output):
        # Some LangGraph stream implementations expose the final values event but
        # do not populate stream.output. Prefer the final structured response when
        # it was observed directly from the event stream.
        return latest_output
    if stream_output is not None:
        return stream_output
    if latest_output is not _NO_OUTPUT:
        return latest_output
    return stream_output


def _has_structured_response(value: object) -> bool:
    return isinstance(value, dict) and value.get("structured_response") is not None


_SENSITIVE_EVENT_KEYS = {
    "reasoning",
    "reasoning_content",
    "reasoningContent",
    "thinking",
    "thought",
    "chain_of_thought",
    "chainOfThought",
}


def _loggable_payload(
    value: Any,
    *,
    max_text: int = 1500,
    max_items: int = 12,
) -> Any:
    if value is None:
        return None
    if isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, str):
        return value if len(value) <= max_text else f"{value[:max_text]}..."
    if isinstance(value, bytes):
        return f"<bytes len={len(value)}>"
    if isinstance(value, dict):
        return {
            str(key): _loggable_payload(
                item,
                max_text=max_text,
                max_items=max_items,
            )
            for key, item in list(value.items())[:max_items]
            if str(key) not in _SENSITIVE_EVENT_KEYS
        }
    if isinstance(value, tuple):
        return [
            _loggable_payload(item, max_text=max_text, max_items=max_items)
            for item in value[:max_items]
        ]
    if isinstance(value, list):
        return [
            _loggable_payload(item, max_text=max_text, max_items=max_items)
            for item in value[:max_items]
        ]
    if hasattr(value, "model_dump"):
        return _loggable_payload(
            value.model_dump(),
            max_text=max_text,
            max_items=max_items,
        )
    if isinstance(value, Iterable):
        return repr(value)
    return repr(value)


def _agent_event_log(event: AgentEventStreamEvent) -> str:
    tool_usage = _agent_event_tool_usage(event)
    if tool_usage:
        tool_name = tool_usage.get("tool_name") or tool_usage.get("name") or "tool"
        tool_event = tool_usage.get("event")
        if tool_event:
            return f"{event.channel}: {tool_name} {tool_event}"
        return f"{event.channel}: {tool_name}"
    token = _agent_event_token(event)
    if token:
        return f"{event.channel}: model token"
    if event.channel == "messages" and isinstance(event.payload, dict):
        event_name = event.payload.get("event")
        if event_name:
            return f"{event.channel}: {event_name}"
    if event.channel == "values" and isinstance(event.payload, dict):
        message_count = event.payload.get("message_count")
        structured_response = event.payload.get("structured_response")
        if isinstance(structured_response, dict):
            return f"{event.channel}: structured response"
        if isinstance(message_count, int):
            return f"{event.channel}: {message_count} messages"
    return f"{event.channel}: agent event"


def _agent_event_token(event: AgentEventStreamEvent) -> str | None:
    if event.channel != "messages":
        return None
    text = _visible_text(event.payload)
    return text or None


def _agent_event_tool_usage(event: AgentEventStreamEvent) -> dict[str, Any] | None:
    payload = event.payload
    if isinstance(payload, dict):
        data = payload.get("data")
        if event.channel == "tools" and isinstance(data, dict):
            return {
                "event": data.get("event"),
                "tool_call_id": data.get("tool_call_id"),
                "tool_name": data.get("tool_name"),
                "input": data.get("input"),
                "output": data.get("output"),
                "error": data.get("message") or data.get("error"),
            }
        for key in ("tool_calls", "tool_call_chunks", "toolCalls", "toolCallChunks"):
            value = payload.get(key)
            if value:
                return {"channel": event.channel, key: value}
        if event.channel == "tool_calls":
            return payload
    if event.channel == "tool_calls":
        return {"channel": event.channel, "payload": payload}
    return None


def _visible_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        data = value.get("data")
        if isinstance(data, (list, tuple)) and data:
            return _visible_text(data[0])
        if isinstance(data, dict):
            return _visible_text(data)
        delta = value.get("delta")
        if isinstance(delta, dict):
            if delta.get("type") == "text-delta":
                return str(delta.get("text") or "")
            if delta.get("type") == "block-delta":
                fields = delta.get("fields")
                if isinstance(fields, dict) and fields.get("type") == "text":
                    return str(fields.get("text") or "")
        if isinstance(value.get("text"), str):
            return value["text"]
        if isinstance(value.get("content"), str):
            return value["content"]
        blocks = value.get("content_blocks") or value.get("contentBlocks")
        if isinstance(blocks, list):
            return " ".join(_visible_text(block) for block in blocks).strip()
        return ""
    if isinstance(value, list):
        return " ".join(_visible_text(item) for item in value).strip()
    return ""
