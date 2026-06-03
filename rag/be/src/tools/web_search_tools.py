# 역할: graph candidate agent가 외부 웹 근거를 보강 조회할 때 사용하는 Firecrawl search tool이다.
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from langchain.tools import tool

from settings import settings

FirecrawlSourceType = Literal["web", "news"]
FirecrawlTimeRange = Literal["any", "hour", "day", "week", "month", "year"]

_DEFAULT_SOURCE_TYPES: list[FirecrawlSourceType] = ["web"]
_MAX_DOMAIN_FILTER_COUNT = 10
_TEXT_LIMIT = 500
_TIME_RANGE_TO_TBS = {
    "hour": "qdr:h",
    "day": "qdr:d",
    "week": "qdr:w",
    "month": "qdr:m",
    "year": "qdr:y",
}


@tool
def web_search_firecrawl_tool(
    query: str,
    limit: int | None = None,
    source_types: list[FirecrawlSourceType] | None = None,
    include_markdown: bool = False,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
    location: str | None = None,
    time_range: FirecrawlTimeRange = "any",
) -> dict[str, Any]:
    """Search public web pages with Firecrawl for auxiliary relationship evidence.

    Write a concise search query yourself. Use this only when internal Memgraph
    context is not enough and public sources may help evaluate a candidate.
    Results are auxiliary links/summaries and must not be used to invent DB node ids.
    """
    normalized_query = query.strip()
    queried_at = datetime.now(UTC).isoformat()
    if not normalized_query:
        return _failure(
            query=normalized_query,
            queried_at=queried_at,
            warning="query must not be empty.",
        )

    api_key = settings.firecrawl_api_key
    if api_key is None or not api_key.get_secret_value().strip():
        return _failure(
            query=normalized_query,
            queried_at=queried_at,
            warning=(
                "RAG_FIRECRAWL_API_KEY is missing. Firecrawl web search was skipped."
            ),
        )

    safe_limit = _bounded_limit(limit)
    safe_sources = _source_types(source_types)
    include_domain_filter = _domain_filter(include_domains)
    exclude_domain_filter = _domain_filter(exclude_domains)
    if include_domain_filter and exclude_domain_filter:
        return _failure(
            query=normalized_query,
            queried_at=queried_at,
            warning="include_domains and exclude_domains cannot be used together.",
        )

    try:
        from firecrawl import Firecrawl

        client = Firecrawl(
            api_key=api_key.get_secret_value(),
            timeout=settings.firecrawl_request_timeout_ms / 1000,
        )
        response = client.search(
            normalized_query,
            sources=safe_sources,
            include_domains=include_domain_filter or None,
            exclude_domains=exclude_domain_filter or None,
            limit=safe_limit,
            tbs=_TIME_RANGE_TO_TBS.get(time_range),
            location=_optional_string(location),
            ignore_invalid_urls=True,
            timeout=settings.firecrawl_request_timeout_ms,
            scrape_options=_scrape_options() if include_markdown else None,
        )
    except Exception as exc:  # noqa: BLE001
        return _failure(
            query=normalized_query,
            queried_at=queried_at,
            warning=f"Firecrawl web search failed: {exc}",
        )

    results = _normalize_search_data(
        response,
        query=normalized_query,
        include_markdown=include_markdown,
    )
    return {
        "provider": "firecrawl",
        "success": True,
        "query": normalized_query,
        "count": len(results),
        "queried_at": queried_at,
        "results": results,
        "warnings": [],
    }


def _scrape_options() -> Any:
    from firecrawl.v2.types import ScrapeOptions

    return ScrapeOptions(
        formats=["markdown"],
        only_main_content=True,
        remove_base64_images=True,
        timeout=settings.firecrawl_request_timeout_ms,
    )


def _normalize_search_data(
    response: Any,
    *,
    query: str,
    include_markdown: bool,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for source_type in ("web", "news"):
        items = getattr(response, source_type, None) or []
        for index, item in enumerate(items, start=1):
            normalized = _normalize_item(
                item,
                query=query,
                source_type=source_type,
                position=index,
                include_markdown=include_markdown,
            )
            url = normalized.get("url")
            if not isinstance(url, str) or not url or url in seen_urls:
                continue
            seen_urls.add(url)
            rows.append(normalized)
    return rows


def _normalize_item(
    item: Any,
    *,
    query: str,
    source_type: str,
    position: int,
    include_markdown: bool,
) -> dict[str, Any]:
    row = _as_dict(item)
    metadata = _as_dict(row.get("metadata"))
    url = _first_string(
        row.get("url"),
        metadata.get("sourceURL"),
        metadata.get("url"),
    )
    title = _first_string(
        row.get("title"),
        metadata.get("title"),
        url,
        "Firecrawl result",
    )
    description = _first_string(
        row.get("description"),
        row.get("snippet"),
        metadata.get("description"),
        row.get("summary"),
        "",
    )
    result: dict[str, Any] = {
        "provider": "firecrawl",
        "source_type": source_type,
        "query": query,
        "position": _int_or(position, row.get("position")),
        "title": _truncate_text(title, _TEXT_LIMIT),
        "url": url,
        "description": _truncate_text(description, _TEXT_LIMIT),
    }
    published_at = _first_string(row.get("date"), metadata.get("publishedAt"))
    if published_at:
        result["published_at"] = published_at
    category = _first_string(row.get("category"), metadata.get("category"))
    if category:
        result["category"] = category
    markdown = _first_string(row.get("markdown"))
    if include_markdown and markdown:
        result["markdown_preview"] = _truncate_text(
            markdown,
            settings.firecrawl_search_markdown_char_limit,
        )
    return result


def _failure(*, query: str, queried_at: str, warning: str) -> dict[str, Any]:
    return {
        "provider": "firecrawl",
        "success": False,
        "query": query,
        "count": 0,
        "queried_at": queried_at,
        "results": [],
        "warnings": [warning],
    }


def _bounded_limit(limit: int | None) -> int:
    default_limit = min(
        settings.firecrawl_search_default_limit,
        settings.firecrawl_search_max_limit,
    )
    if limit is None:
        return default_limit
    return min(max(int(limit), 1), settings.firecrawl_search_max_limit)


def _source_types(
    source_types: list[FirecrawlSourceType] | None,
) -> list[FirecrawlSourceType]:
    if not source_types:
        return _DEFAULT_SOURCE_TYPES
    safe_sources: list[FirecrawlSourceType] = []
    for source_type in source_types:
        if source_type in ("web", "news") and source_type not in safe_sources:
            safe_sources.append(source_type)
    return safe_sources or _DEFAULT_SOURCE_TYPES


def _domain_filter(domains: list[str] | None) -> list[str]:
    if not domains:
        return []
    safe_domains: list[str] = []
    for domain in domains:
        normalized = domain.strip().lower()
        if normalized and normalized not in safe_domains:
            safe_domains.append(normalized)
        if len(safe_domains) >= _MAX_DOMAIN_FILTER_COUNT:
            break
    return safe_domains


def _optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        dumped = value.model_dump()
        return dumped if isinstance(dumped, dict) else {}
    return {}


def _first_string(*values: Any) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _int_or(fallback: int, value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return fallback


def _truncate_text(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return f"{value[:limit].rstrip()}... [truncated]"
