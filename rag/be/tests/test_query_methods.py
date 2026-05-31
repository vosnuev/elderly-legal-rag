from __future__ import annotations

import json
import unittest
from typing import Any
from unittest.mock import patch

from query.read.document import get_document_record
from query.read.raw import read_query
from query.read.schema import schema_read
from query.read.text_search import text_search
from query.write.cypher import write_query
from query.write.document_registration import register_document


class FakeMemgraphClient:
    def __init__(self, responses: dict[str, dict[str, Any]]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, str, dict[str, Any] | None]] = []

    def execute_read(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized_query = " ".join(query.split())
        self.calls.append(("read", normalized_query, parameters))
        return self.responses[normalized_query]

    def execute_write(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized_query = " ".join(query.split())
        self.calls.append(("write", normalized_query, parameters))
        return self.responses[normalized_query]


class QueryReadMethodsTest(unittest.TestCase):
    def test_raw_read_executes_agent_query_without_limit_when_not_requested(self) -> None:
        client = FakeMemgraphClient(
            {
                "MATCH (n) RETURN n": {
                    "rows": [],
                }
            }
        )

        with patch("query.read.raw.get_memgraph_bolt_client", return_value=client):
            read_query("MATCH (n) RETURN n")

        self.assertEqual(client.calls, [("read", "MATCH (n) RETURN n", None)])

    def test_schema_read_uses_memgraph_schema_info(self) -> None:
        schema = {
            "nodes": [{"labels": ["Document"], "count": 1, "properties": []}],
            "edges": [{"type": "HAS_CHUNK", "count": 1, "properties": []}],
            "node_indexes": [{"type": "label_text", "labels": ["Document"]}],
            "edge_indexes": [],
            "node_constraints": [],
            "enums": [],
        }
        client = FakeMemgraphClient(
            {
                "SHOW SCHEMA INFO": {
                    "columns": ["schema"],
                    "rows": [{"schema": json.dumps(schema)}],
                    "row_count": 1,
                }
            }
        )

        with patch("query.read.schema.get_memgraph_bolt_client", return_value=client):
            result = schema_read()

        self.assertEqual(client.calls, [("read", "SHOW SCHEMA INFO", None)])
        self.assertEqual(result["source"], "SHOW SCHEMA INFO")
        self.assertEqual(result["schema"], schema)
        self.assertEqual(result["nodes"], schema["nodes"])
        self.assertEqual(result["edges"], schema["edges"])

    def test_document_read_uses_unique_document_id(self) -> None:
        client = FakeMemgraphClient(
            {
                "MATCH (node:Document {id: $node_id}) RETURN node LIMIT 1": {
                    "rows": [
                        {
                            "node": {
                                "type": "node",
                                "labels": ["Document"],
                                "properties": {
                                    "id": "doc-1",
                                    "raw_content": "original text",
                                },
                            }
                        }
                    ]
                }
            }
        )

        with patch("query.read.document.get_memgraph_bolt_client", return_value=client):
            result = get_document_record("doc-1")

        self.assertEqual(result["id"], "doc-1")
        self.assertEqual(result["raw_content"], "original text")
        _, _, parameters = client.calls[0]
        self.assertEqual(parameters, {"node_id": "doc-1"})

    def test_text_search_passes_limit_to_memgraph_procedure(self) -> None:
        client = FakeMemgraphClient(
            {
                "CALL text_search.search($index_name, $search_query, $limit) YIELD node, score RETURN labels(node) AS labels, node AS node, score ORDER BY score DESC": {
                    "rows": []
                }
            }
        )

        with patch("query.read.text_search.get_memgraph_bolt_client", return_value=client):
            text_search("Rules2024", top_k=7)

        _, query, parameters = client.calls[0]
        self.assertIn("text_search.search($index_name, $search_query, $limit)", query)
        self.assertNotIn(" LIMIT ", f" {query} ")
        self.assertEqual(parameters["limit"], 7)


class QueryWriteMethodsTest(unittest.TestCase):
    def test_raw_write_executes_agent_query_without_task_metadata(self) -> None:
        client = FakeMemgraphClient(
            {
                "CREATE (chunk:Chunk {id: $id}) RETURN chunk": {
                    "rows": [{"chunk": {"id": "chunk-1"}}],
                }
            }
        )

        with patch("query.write.cypher.get_memgraph_bolt_client", return_value=client):
            result = write_query(
                "CREATE (chunk:Chunk {id: $id}) RETURN chunk",
                {"id": "chunk-1"},
            )

        self.assertEqual(result["access"], "write")
        self.assertEqual(
            client.calls,
            [
                (
                    "write",
                    "CREATE (chunk:Chunk {id: $id}) RETURN chunk",
                    {"id": "chunk-1"},
                )
            ],
        )

    def test_document_registration_is_the_only_fixed_write_method(self) -> None:
        client = FakeMemgraphClient(
            {
                "MERGE (document:Document {id: $document_id}) ON CREATE SET document.created_at = localDateTime() SET document += $document, document.updated_at = localDateTime() RETURN document.id AS document_id": {
                    "rows": [{"document_id": "doc-1"}],
                }
            }
        )

        with patch(
            "query.write.document_registration.get_memgraph_bolt_client",
            return_value=client,
        ):
            register_document({"id": "doc-1", "raw_content": "original text"})

        _, query, parameters = client.calls[0]
        self.assertIn("MERGE (document:Document {id: $document_id})", query)
        self.assertNotIn("IngestJob", query)
        self.assertEqual(parameters["document_id"], "doc-1")
        self.assertEqual(parameters["document"]["raw_content"], "original text")


if __name__ == "__main__":
    unittest.main()
