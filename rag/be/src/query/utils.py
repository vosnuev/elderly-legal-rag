from __future__ import annotations

import json
from typing import Any

from settings import settings


def bounded_limit(value: int | None) -> int:
    if value is None:
        return settings.query_max_rows
    return max(1, min(value, settings.query_max_rows))


def safe_identifier(value: str) -> str:
    if not value or not value.replace("_", "").isalnum() or value[0].isdigit():
        raise ValueError(f"Unsafe Cypher identifier: {value}")
    return value


def graph_properties(data: dict[str, Any]) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    for key, value in data.items():
        if value is None:
            properties[key] = None
        elif isinstance(value, (str, int, float, bool)):
            properties[key] = value
        elif isinstance(value, list) and all(
            isinstance(item, (str, int, float, bool)) for item in value
        ):
            properties[key] = value
        else:
            properties[key] = json.dumps(value, ensure_ascii=False, default=str)
    return properties


def node_properties(node: dict[str, Any]) -> dict[str, Any]:
    properties = node.get("properties", node)
    if not isinstance(properties, dict):
        raise ValueError("Expected node properties.")

    normalized = dict(properties)
    for key in ("metadata",):
        value = normalized.get(key)
        if isinstance(value, str):
            try:
                loaded = json.loads(value)
            except json.JSONDecodeError:
                continue
            if isinstance(loaded, dict):
                normalized[key] = loaded
    return normalized
