from __future__ import annotations

import argparse
from functools import lru_cache
from typing import Any

from fastmcp import FastMCP
from neo4j import GraphDatabase

from .config import load_config
from .readonly_cypher import ReadOnlyCypherError, run_read_query


mcp = FastMCP(name="RAG Red Team Neo4j")


@lru_cache(maxsize=1)
def _driver():
    config = load_config()
    return GraphDatabase.driver(config.uri, auth=(config.user, config.password))


def _database() -> str:
    return load_config().database


@mcp.tool
def graph_schema() -> dict[str, Any]:
    """Return graph label counts, relationship counts, and example read queries."""
    driver = _driver()
    label_counts = run_read_query(
        driver,
        _database(),
        """
        MATCH (n)
        UNWIND labels(n) AS label
        RETURN label, count(*) AS count
        ORDER BY label
        """,
        max_rows=100,
    )
    relationship_counts = run_read_query(
        driver,
        _database(),
        """
        MATCH ()-[r]->()
        RETURN type(r) AS type, count(*) AS count
        ORDER BY type
        """,
        max_rows=100,
    )
    return {
        "labels": label_counts["rows"],
        "relationships": relationship_counts["rows"],
        "example_queries": [
            "MATCH p=(d:Document)-[:HAS_CHUNK]->(c:Chunk) RETURN p LIMIT 50",
            "MATCH p=(a:Chunk)-[:RELATED_TO]->(b:Chunk) RETURN p LIMIT 200",
            "MATCH (a:Chunk)-[r:RELATED_TO]->(b:Chunk) RETURN a.document_name, a.chunk_key, r.relation_type, coalesce(r.curation_method, 'markdown'), b.chunk_key LIMIT 10",
        ],
    }


@mcp.tool
def run_cypher(
    query: str,
    parameters: dict[str, Any] | None = None,
    max_rows: int = 100,
) -> dict[str, Any]:
    """Run a read-only Cypher query against the manual RAG red-team Neo4j graph."""
    try:
        return run_read_query(
            _driver(),
            _database(),
            query=query,
            parameters=parameters,
            max_rows=max_rows,
        )
    except ReadOnlyCypherError as exc:
        return {"error": str(exc), "read_only": True}


@mcp.tool
def search_chunks(
    keyword: str,
    document_name: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Search chunk titles and content with a plain substring match."""
    query = """
    MATCH (chunk:Chunk)
    WHERE ($document_name IS NULL OR chunk.document_name = $document_name)
      AND (
        chunk.content CONTAINS $keyword
        OR chunk.title CONTAINS $keyword
        OR chunk.article CONTAINS $keyword
      )
    RETURN chunk.id AS id,
           chunk.document_name AS document_name,
           chunk.chunk_key AS chunk_key,
           chunk.article AS article_no,
           chunk.title AS title,
           left(chunk.content, 500) AS preview
    ORDER BY chunk.document_name, chunk.chunk_index
    LIMIT $limit
    """
    return run_read_query(
        _driver(),
        _database(),
        query=query,
        parameters={
            "keyword": keyword,
            "document_name": document_name,
            "limit": max(1, min(limit, 100)),
        },
        max_rows=limit,
    )


@mcp.tool
def manual_relations(
    chunk_id: str | None = None,
    document_name: str | None = None,
    cross_document_only: bool = False,
    limit: int = 25,
) -> dict[str, Any]:
    """List human-authored chunk-to-chunk edges from the Markdown design files."""
    query = """
    MATCH (source:Chunk)-[rel:RELATED_TO]->(target:Chunk)
    WHERE ($chunk_id IS NULL OR source.id = $chunk_id OR target.id = $chunk_id)
      AND ($document_name IS NULL OR source.document_name = $document_name)
      AND ($cross_document_only = false OR source.document_name <> target.document_name)
    RETURN source.id AS source_id,
           source.document_name AS source_document,
           source.chunk_key AS source_chunk,
           source.article AS source_article,
           source.title AS source_title,
           rel.relation_type AS relation_type,
           rel.category AS category,
           rel.summary AS summary,
           rel.edge_line AS edge_line,
           coalesce(rel.curation_method, 'markdown') AS curation_method,
           target.id AS target_id,
           target.document_name AS target_document,
           target.chunk_key AS target_chunk,
           target.article AS target_article,
           target.title AS target_title,
           rel.source_docx AS source_docx
    ORDER BY source.document_name, target.document_name, source.chunk_index, target.chunk_index
    LIMIT $limit
    """
    return run_read_query(
        _driver(),
        _database(),
        query=query,
        parameters={
            "chunk_id": chunk_id,
            "document_name": document_name,
            "cross_document_only": cross_document_only,
            "limit": max(1, min(limit, 100)),
        },
        max_rows=limit,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the RAG red-team MCP server.")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9001)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.transport == "http":
        mcp.run(transport="http", host=args.host, port=args.port)
        return
    mcp.run()


if __name__ == "__main__":
    main()
