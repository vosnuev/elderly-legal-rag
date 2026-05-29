from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class QueryAccess(StrEnum):
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"


class QueryValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ValidatedQuery:
    query: str
    access: QueryAccess
    warnings: tuple[str, ...] = ()


DENIED_READ_TOKENS = frozenset(
    {
        "ALTER",
        "CREATE",
        "DELETE",
        "DETACH",
        "DROP",
        "LOAD",
        "MERGE",
        "REMOVE",
        "SET",
    }
)

DENIED_WRITE_TOKENS = frozenset(
    {
        "ALTER",
        "DELETE",
        "DETACH",
        "DROP",
        "LOAD",
        "REMOVE",
        "TRUNCATE",
    }
)

READ_START_TOKENS = frozenset(
    {
        "CALL",
        "EXPLAIN",
        "MATCH",
        "OPTIONAL",
        "RETURN",
        "SHOW",
        "UNWIND",
        "WITH",
    }
)

WRITE_START_TOKENS = READ_START_TOKENS | frozenset({"CREATE", "MERGE", "SET"})
ALLOWED_EXTERNAL_CALLS = ("vector_search.",)
TOKEN_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")


def validate_read_query(query: str, *, max_rows: int) -> ValidatedQuery:
    normalized = _normalize_query(query)
    tokens = _tokens(normalized)
    warnings: list[str] = []

    _reject_empty(normalized)
    _reject_multiple_statements(normalized)
    _reject_denied_tokens(tokens, DENIED_READ_TOKENS, "read-only")
    _require_start_token(tokens, READ_START_TOKENS)
    _validate_call_allowlist(normalized, tokens)

    limited = _ensure_limit(normalized, max_rows)
    if limited != normalized:
        warnings.append(f"LIMIT {max_rows} was appended to bound the result set.")

    return ValidatedQuery(
        query=limited,
        access=QueryAccess.READ_ONLY,
        warnings=tuple(warnings),
    )


def validate_write_query(
    query: str,
    *,
    job_id: str,
    purpose: str,
) -> ValidatedQuery:
    normalized = _normalize_query(query)
    tokens = _tokens(normalized)

    _reject_empty(normalized)
    _reject_multiple_statements(normalized)
    _reject_denied_tokens(tokens, DENIED_WRITE_TOKENS, "internal write")
    _require_start_token(tokens, WRITE_START_TOKENS)

    if not job_id.strip():
        raise QueryValidationError("Internal write queries require job_id.")
    if not purpose.strip():
        raise QueryValidationError("Internal write queries require purpose.")

    return ValidatedQuery(query=normalized, access=QueryAccess.READ_WRITE)


def _normalize_query(query: str) -> str:
    return query.strip().removesuffix(";").strip()


def _tokens(query: str) -> tuple[str, ...]:
    redacted = _redact_string_literals(query)
    return tuple(token.upper() for token in TOKEN_RE.findall(redacted))


def _reject_empty(query: str) -> None:
    if not query:
        raise QueryValidationError("Query cannot be empty.")


def _reject_multiple_statements(query: str) -> None:
    if ";" in _redact_string_literals(query):
        raise QueryValidationError("Multiple Cypher statements are not allowed.")


def _reject_denied_tokens(
    tokens: tuple[str, ...],
    denied_tokens: frozenset[str],
    access_label: str,
) -> None:
    denied = sorted(set(tokens).intersection(denied_tokens))
    if denied:
        raise QueryValidationError(
            f"{access_label} query rejected because it contains denied operation(s): "
            + ", ".join(denied)
        )


def _require_start_token(
    tokens: tuple[str, ...],
    allowed_start_tokens: frozenset[str],
) -> None:
    if not tokens or tokens[0] not in allowed_start_tokens:
        allowed = ", ".join(sorted(allowed_start_tokens))
        raise QueryValidationError(f"Query must start with one of: {allowed}.")


def _validate_call_allowlist(query: str, tokens: tuple[str, ...]) -> None:
    if "CALL" not in tokens:
        return

    lowered = query.lower()
    if not any(f"call {name}" in lowered for name in ALLOWED_EXTERNAL_CALLS):
        raise QueryValidationError(
            "External CALL queries are limited to allowed read-only procedures. "
            "Use a wrapper tool or schema_read for other operations."
        )


def _ensure_limit(query: str, max_rows: int) -> str:
    tokens = _tokens(query)
    if "LIMIT" in tokens or "SHOW" in tokens:
        return query
    if not any(token in tokens for token in ("RETURN", "YIELD")):
        return query
    return f"{query} LIMIT {max_rows}"


def _redact_string_literals(query: str) -> str:
    result: list[str] = []
    quote: str | None = None
    escaped = False

    for char in query:
        if quote is None:
            if char in {"'", '"'}:
                quote = char
                result.append(" ")
            else:
                result.append(char)
            continue

        if escaped:
            escaped = False
            result.append(" ")
            continue

        if char == "\\":
            escaped = True
            result.append(" ")
            continue

        if char == quote:
            quote = None

        result.append(" ")

    return "".join(result)
