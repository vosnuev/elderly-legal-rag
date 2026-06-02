# 역할: LangChain agent에게 반환되는 tool output에서 context를 터뜨리는 DB payload를 제거한다.
from __future__ import annotations

from typing import Any

AGENT_RESULT_MAX_ROWS = 20
AGENT_TEXT_FIELD_LIMIT = 500
AGENT_LIST_FIELD_LIMIT = 20

_DROP_PROPERTY_KEYS = {
    "embedding",
    "raw_content",
    "metadata",
}

_TEXT_PROPERTY_KEYS = {
    "text",
    "content",
    "evidence_text",
    "rationale",
    "summary",
    "reason",
    "description",
}


def sanitize_agent_tool_output(value: Any) -> Any:
    """Return an agent-safe projection of Memgraph query output.

    query/read functions keep returning full DB records for internal code paths.
    Agent-facing tools must not pass raw documents, embedding vectors, or full
    path node properties back into LangGraph message state.
    """

    if _looks_like_query_result(value):
        rows = value.get("rows", [])
        safe_rows = [
            _sanitize_value(row)
            for row in rows[:AGENT_RESULT_MAX_ROWS]
        ]
        result = {
            "columns": value.get("columns", []),
            "rows": safe_rows,
            "row_count": value.get("row_count", len(rows)),
            "returned_row_count": len(safe_rows),
            "elapsed_ms": value.get("elapsed_ms"),
            "sanitized": True,
        }
        omitted = ["query", "counters"]
        if len(rows) > AGENT_RESULT_MAX_ROWS:
            result["truncated_rows"] = len(rows) - AGENT_RESULT_MAX_ROWS
        result["omitted_runtime_fields"] = omitted
        return result
    return _sanitize_value(value)


def _looks_like_query_result(value: Any) -> bool:
    return isinstance(value, dict) and "rows" in value and "columns" in value


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, dict):
        value_type = value.get("type")
        if value_type == "node":
            return _sanitize_node(value)
        if value_type == "relationship":
            return _sanitize_relationship(value)
        if value_type == "path":
            return _sanitize_path(value)
        return _sanitize_dict(value)
    if isinstance(value, list):
        if _looks_like_embedding(value):
            return {
                "omitted": "numeric_vector",
                "length": len(value),
            }
        return [
            _sanitize_value(item)
            for item in value[:AGENT_LIST_FIELD_LIMIT]
        ]
    if isinstance(value, str):
        return _truncate_text(value, AGENT_TEXT_FIELD_LIMIT)
    return value


def _sanitize_node(node: dict[str, Any]) -> dict[str, Any]:
    labels = node.get("labels") or []
    properties = node.get("properties")
    safe_properties = _sanitize_properties(
        properties if isinstance(properties, dict) else {}
    )
    return {
        "type": "node",
        "element_id": node.get("element_id"),
        "labels": labels,
        "properties": safe_properties,
    }


def _sanitize_relationship(relationship: dict[str, Any]) -> dict[str, Any]:
    properties = relationship.get("properties")
    return {
        "type": "relationship",
        "element_id": relationship.get("element_id"),
        "relationship_type": relationship.get("relationship_type"),
        "start_node_id": relationship.get("start_node_id"),
        "end_node_id": relationship.get("end_node_id"),
        "properties": _sanitize_properties(
            properties if isinstance(properties, dict) else {}
        ),
    }


def _sanitize_path(path: dict[str, Any]) -> dict[str, Any]:
    nodes = path.get("nodes")
    relationships = path.get("relationships")
    return {
        "type": "path",
        "nodes": [
            _sanitize_node(node)
            for node in (nodes if isinstance(nodes, list) else [])[:AGENT_LIST_FIELD_LIMIT]
            if isinstance(node, dict)
        ],
        "relationships": [
            _sanitize_relationship(relationship)
            for relationship in (
                relationships if isinstance(relationships, list) else []
            )[:AGENT_LIST_FIELD_LIMIT]
            if isinstance(relationship, dict)
        ],
    }


def _sanitize_dict(value: dict[str, Any]) -> dict[str, Any]:
    return {
        str(key): _sanitize_property(str(key), item)
        for key, item in value.items()
        if str(key) not in _DROP_PROPERTY_KEYS
    }


def _sanitize_properties(properties: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    omitted: dict[str, str] = {}
    for key, value in properties.items():
        if key in _DROP_PROPERTY_KEYS:
            omitted[key] = _omission_reason(value)
            continue
        safe[key] = _sanitize_property(key, value)
    if omitted:
        safe["_omitted_properties"] = omitted
    return safe


def _sanitize_property(key: str, value: Any) -> Any:
    if key in _DROP_PROPERTY_KEYS:
        return {
            "omitted": _omission_reason(value),
        }
    if isinstance(value, str):
        limit = AGENT_TEXT_FIELD_LIMIT if key in _TEXT_PROPERTY_KEYS else 200
        return _truncate_text(value, limit)
    if isinstance(value, list) and _looks_like_embedding(value):
        return {
            "omitted": "numeric_vector",
            "length": len(value),
        }
    return _sanitize_value(value)


def _looks_like_embedding(value: list[Any]) -> bool:
    return len(value) > AGENT_LIST_FIELD_LIMIT and all(
        isinstance(item, (int, float))
        for item in value[:AGENT_LIST_FIELD_LIMIT]
    )


def _truncate_text(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return f"{value[:limit]}...<truncated chars={len(value) - limit}>"


def _omission_reason(value: Any) -> str:
    if isinstance(value, list) and _looks_like_embedding(value):
        return f"numeric_vector length={len(value)}"
    if isinstance(value, str):
        return f"text length={len(value)}"
    if isinstance(value, dict):
        return "metadata_object"
    return type(value).__name__
