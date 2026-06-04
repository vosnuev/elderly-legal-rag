from __future__ import annotations

from dataclasses import asdict
from typing import Any

from neo4j import Driver, GraphDatabase

from .config import Neo4jConfig
from .md_relations import parse_markdown_relations
from .models import LawDocument, ManualRelation
from .toon_parser import load_toon_documents


def _driver(config: Neo4jConfig) -> Driver:
    return GraphDatabase.driver(config.uri, auth=(config.user, config.password))


def _clean_props(row: dict[str, Any]) -> dict[str, Any]:
    return {key: ("" if value is None else value) for key, value in row.items()}


def _known_chunk_ids(documents: list[LawDocument]) -> set[str]:
    return {article.id for document in documents for article in document.articles}


def _write_constraints(driver: Driver, database: str) -> None:
    obsolete_statements = [
        "DROP CONSTRAINT article_id IF EXISTS",
        "DROP CONSTRAINT external_article_id IF EXISTS",
        "DROP CONSTRAINT law_id IF EXISTS",
        "DROP CONSTRAINT manual_relation_id IF EXISTS",
        "DROP CONSTRAINT term_name IF EXISTS",
    ]
    statements = [
        "CREATE CONSTRAINT document_id IF NOT EXISTS FOR (n:Document) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (n:Chunk) REQUIRE n.id IS UNIQUE",
    ]
    for statement in obsolete_statements:
        driver.execute_query(statement, database_=database)
    for statement in statements:
        driver.execute_query(statement, database_=database)


def _reset(driver: Driver, database: str) -> None:
    driver.execute_query("MATCH (n) DETACH DELETE n", database_=database)


def _document_id(law_name: str) -> str:
    return f"document/{law_name}"


def _load_documents(driver: Driver, database: str, documents: list[LawDocument]) -> None:
    rows = [
        _clean_props(
            {
                "id": _document_id(document.law.name),
                "name": document.law.name,
                "law_id": document.law.law_id,
                "kind": document.law.kind,
                "ministry": document.law.ministry,
                "effective_date": document.law.effective_date,
                "promulgation_no": document.law.promulgation_no,
                "promulgation_date": document.law.promulgation_date,
                "source_file": document.law.source_file,
                "toon_file": document.path.name,
                "chunk_count": len(document.articles),
            }
        )
        for document in documents
    ]

    driver.execute_query(
        """
        UNWIND $rows AS row
        MERGE (document:Document {id: row.id})
        SET document += row
        """,
        rows=rows,
        database_=database,
    )


def _load_chunks(driver: Driver, database: str, documents: list[LawDocument]) -> None:
    rows: list[dict[str, Any]] = []
    for document in documents:
        for article in document.articles:
            rows.append(
                _clean_props(
                    {
                        "id": article.id,
                        "document_id": _document_id(document.law.name),
                        "document_name": document.law.name,
                        "chunk_key": f"{article.ordinal:03d}_{article.article}_{article.title}".strip("_"),
                        "chunk_index": article.ordinal,
                        "article": article.article,
                        "title": article.title,
                        "content": article.content,
                        "content_length": len(article.content),
                    }
                )
            )

    driver.execute_query(
        """
        UNWIND $rows AS row
        MERGE (chunk:Chunk {id: row.id})
        SET chunk += row
        WITH chunk, row
        MATCH (document:Document {id: row.document_id})
        MERGE (document)-[rel:HAS_CHUNK]->(chunk)
        SET rel.chunk_index = row.chunk_index
        """,
        rows=rows,
        database_=database,
    )


def _load_chunk_edges(
    driver: Driver,
    database: str,
    manual_relations: list[ManualRelation],
    known_chunk_ids: set[str],
) -> dict[str, int]:
    edge_rows: list[dict[str, Any]] = []
    missing_rows: list[dict[str, Any]] = []

    for relation in manual_relations:
        row = _clean_props(asdict(relation))
        row["source_chunk_id"] = relation.source_article_id
        row["target_chunk_id"] = relation.target_article_id
        row["edge_line"] = relation.header
        row["curation_method"] = "markdown"

        if relation.source_article_id in known_chunk_ids and relation.target_article_id in known_chunk_ids:
            edge_rows.append(row)
        else:
            missing_rows.append(row)

    driver.execute_query(
        """
        UNWIND $rows AS row
        MATCH (source:Chunk {id: row.source_chunk_id})
        MATCH (target:Chunk {id: row.target_chunk_id})
        MERGE (source)-[rel:RELATED_TO {id: row.id}]->(target)
        SET rel.edge_line = row.edge_line,
            rel.category = row.category,
            rel.relation_type = row.relation_type,
            rel.summary = row.summary,
            rel.evidence = row.evidence,
            rel.source_docx = row.source_docx,
            rel.note = row.note,
            rel.curation_method = row.curation_method
        """,
        rows=edge_rows,
        database_=database,
    )

    return {
        "markdown_chunk_edges": len(edge_rows),
        "missing_markdown_chunk_edges": len(missing_rows),
    }


def populate_graph(config: Neo4jConfig, toon_dir, md_dir, reset: bool = True) -> dict[str, int]:
    documents = load_toon_documents(toon_dir)
    manual_relations = parse_markdown_relations(md_dir, documents)
    known_chunk_ids = _known_chunk_ids(documents)

    with _driver(config) as driver:
        driver.verify_connectivity()
        if reset:
            _reset(driver, config.database)
        _write_constraints(driver, config.database)
        _load_documents(driver, config.database, documents)
        _load_chunks(driver, config.database, documents)
        edge_counts = _load_chunk_edges(
            driver,
            config.database,
            manual_relations,
            known_chunk_ids,
        )

    return {
        "documents": len(documents),
        "chunks": sum(len(document.articles) for document in documents),
        **edge_counts,
    }
