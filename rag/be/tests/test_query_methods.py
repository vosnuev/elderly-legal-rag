from __future__ import annotations

import json
import unittest
from typing import Any
from unittest.mock import patch

from query.read.core import read_query, schema_read
from query.read.discovery import text_search, text_search_edges, vector_search_edges
from query.read.inspection import (
    get_document_record,
    list_candidates_for_job,
    list_chunks_for_document,
)
from query.read.runtime import list_pending_review_candidates
from pydantic import ValidationError

from query.schema import (
    AgentMemoryNode,
    RelationshipCandidateNode,
    RelationshipCandidateStatus,
    ReviewNoteNode,
)
from query.write.candidates import write_relationship_candidates
from query.write.chunks import write_chunks_for_document
from query.write.core import write_query
from query.write.documents import register_document
from query.write.reviews import store_review_note


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
        if normalized_query not in self.responses and "*" in self.responses:
            return self.responses["*"]
        return self.responses[normalized_query]

    def execute_autocommit_read(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized_query = " ".join(query.split())
        self.calls.append(("autocommit_read", normalized_query, parameters))
        if normalized_query not in self.responses and "*" in self.responses:
            return self.responses["*"]
        return self.responses[normalized_query]

    def execute_write(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized_query = " ".join(query.split())
        self.calls.append(("write", normalized_query, parameters))
        if normalized_query not in self.responses and "*" in self.responses:
            return self.responses["*"]
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

        with patch("query.read.core.cypher.get_memgraph_bolt_client", return_value=client):
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

        with patch("query.read.core.schema.get_memgraph_bolt_client", return_value=client):
            result = schema_read()

        self.assertEqual(client.calls, [("autocommit_read", "SHOW SCHEMA INFO", None)])
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

        with patch("query.read.inspection.nodes.get_memgraph_bolt_client", return_value=client):
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

        with patch("query.read.discovery.text.get_memgraph_bolt_client", return_value=client):
            text_search("Rules2024", top_k=7)

        _, query, parameters = client.calls[0]
        self.assertIn("text_search.search($index_name, $search_query, $limit)", query)
        self.assertNotIn(" LIMIT ", f" {query} ")
        self.assertEqual(parameters["limit"], 7)

    def test_edge_text_search_uses_memgraph_edge_procedure(self) -> None:
        client = FakeMemgraphClient({"*": {"rows": []}})

        with patch("query.read.discovery.text.get_memgraph_bolt_client", return_value=client):
            text_search_edges("Rules2024", top_k=4, index_name="edge_idx")

        _, query, parameters = client.calls[0]
        self.assertIn("text_search.search_edges($index_name, $search_query, $limit)", query)
        self.assertEqual(parameters["index_name"], "edge_idx")
        self.assertEqual(parameters["limit"], 4)

    def test_edge_vector_search_uses_memgraph_edge_procedure(self) -> None:
        client = FakeMemgraphClient({"*": {"rows": []}})

        with patch("query.read.discovery.vector.get_memgraph_bolt_client", return_value=client):
            vector_search_edges("edge_vector_idx", [0.1, 0.2], top_k=3)

        _, query, parameters = client.calls[0]
        self.assertIn("vector_search.search_edges($index_name, $limit, $embedding)", query)
        self.assertEqual(parameters["index_name"], "edge_vector_idx")
        self.assertEqual(parameters["limit"], 3)

    def test_inspection_lists_chunks_for_document_by_relationship(self) -> None:
        client = FakeMemgraphClient({"*": {"rows": []}})

        with patch("query.read.inspection.chunks.get_memgraph_bolt_client", return_value=client):
            list_chunks_for_document("doc-1", limit=9)

        _, query, parameters = client.calls[0]
        self.assertIn("MATCH (:Document {id: $document_id})-[:HAS_CHUNK]->(chunk:Chunk)", query)
        self.assertEqual(parameters["document_id"], "doc-1")
        self.assertEqual(parameters["limit"], 9)

    def test_inspection_lists_candidates_for_job_without_runtime_dto(self) -> None:
        client = FakeMemgraphClient({"*": {"rows": []}})

        with patch(
            "query.read.inspection.candidates.get_memgraph_bolt_client",
            return_value=client,
        ):
            list_candidates_for_job("job-1", status="pending_review", limit=11)

        _, query, parameters = client.calls[0]
        self.assertIn("MATCH (candidate:RelationshipCandidate {job_id: $job_id})", query)
        self.assertIn("candidate.status = $status", query)
        self.assertEqual(parameters["job_id"], "job-1")
        self.assertEqual(parameters["status"], "pending_review")
        self.assertEqual(parameters["limit"], 11)

    def test_runtime_pending_review_candidates_returns_candidate_projection(self) -> None:
        client = FakeMemgraphClient({"*": {"rows": []}})

        with patch(
            "query.read.runtime.review_queue.get_memgraph_bolt_client",
            return_value=client,
        ):
            list_pending_review_candidates(document_id="doc-1", job_id="job-1", limit=12)

        _, query, parameters = client.calls[0]
        self.assertIn("coalesce(candidate.status, \"pending_review\") = \"pending_review\"", query)
        self.assertIn("source_node: coalesce(candidate.source_node, candidate.left_node)", query)
        self.assertIn("target_node: coalesce(candidate.target_node, candidate.right_node)", query)
        self.assertEqual(parameters["document_id"], "doc-1")
        self.assertEqual(parameters["job_id"], "job-1")
        self.assertEqual(parameters["limit"], 12)


class QueryWriteMethodsTest(unittest.TestCase):
    def test_raw_write_executes_agent_query_without_task_metadata(self) -> None:
        client = FakeMemgraphClient(
            {
                "CREATE (chunk:Chunk {id: $id}) RETURN chunk": {
                    "rows": [{"chunk": {"id": "chunk-1"}}],
                }
            }
        )

        with patch("query.write.core.cypher.get_memgraph_bolt_client", return_value=client):
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

    def test_document_registration_validates_document_schema(self) -> None:
        client = FakeMemgraphClient(
            {
                "MERGE (document:Document {id: $document_id}) ON CREATE SET document.created_at = localDateTime() SET document += $document, document.updated_at = localDateTime() RETURN document.id AS document_id": {
                    "rows": [{"document_id": "doc-1"}],
                }
            }
        )

        document = {
            "id": "doc-1",
            "entry_number": 1,
            "document_version": 1,
            "content_hash": "hash",
            "raw_content": "original text",
            "file_name": "sample.txt",
            "source_type": "txt",
            "metadata": {},
        }
        with patch("query.write.core.cypher.get_memgraph_bolt_client", return_value=client):
            register_document(document)

        _, query, parameters = client.calls[0]
        self.assertIn("MERGE (document:Document {id: $document_id})", query)
        self.assertNotIn("IngestJob", query)
        self.assertEqual(parameters["document_id"], "doc-1")
        self.assertEqual(parameters["document"]["raw_content"], "original text")

    def test_chunk_write_generates_ids_and_validates_storage_schema(self) -> None:
        client = FakeMemgraphClient(
            {
                "*": {
                    "rows": [
                        {
                            "stored_count": 1,
                            "chunk_ids": ["generated-chunk"],
                        }
                    ]
                }
            }
        )

        with patch("query.write.core.cypher.get_memgraph_bolt_client", return_value=client):
            write_chunks_for_document(
                document_id="doc-1",
                job_id="job-1",
                chunks=[
                    {
                        "chunk_index": 1,
                        "text": "제1조 목적",
                        "start_unique_string": "제1조",
                        "end_unique_string": "목적",
                    }
                ],
            )

        _, query, parameters = client.calls[0]
        chunk = parameters["chunks"][0]
        self.assertIn("MERGE (d)-[:HAS_CHUNK]->(c)", query)
        self.assertEqual(chunk["document_id"], "doc-1")
        self.assertEqual(chunk["embedding_status"], "pending")
        self.assertTrue(chunk["id"])

    def test_relationship_candidate_write_uses_review_artifact_links(self) -> None:
        client = FakeMemgraphClient(
            {
                "*": {
                    "rows": [
                        {
                            "stored_count": 1,
                            "edge_candidate_ids": ["candidate-1"],
                        }
                    ]
                }
            }
        )

        with patch("query.write.core.cypher.get_memgraph_bolt_client", return_value=client):
            write_relationship_candidates(
                [
                    {
                        "job_id": "job-1",
                        "left_node": "chunk-1",
                        "right_node": "law-1",
                        "relationship_type": "REFERENCES",
                        "relationship_direction": "left_to_right",
                        "evidence_node_id": "chunk-1",
                        "evidence_text": "제1조 목적",
                        "rationale": "법령 조문 근거",
                    }
                ]
            )

        _, query, parameters = client.calls[0]
        candidate = parameters["candidates"][0]
        self.assertIn("EVIDENCES_RELATIONSHIP_CANDIDATE", query)
        self.assertIn("CANDIDATE_LEFT", query)
        self.assertIn("CANDIDATE_RIGHT", query)
        self.assertEqual(candidate["status"], "pending_review")
        self.assertTrue(candidate["id"])

    def test_relationship_candidate_write_allows_optional_evidence_node(self) -> None:
        client = FakeMemgraphClient(
            {
                "*": {
                    "rows": [
                        {
                            "stored_count": 1,
                            "edge_candidate_ids": ["candidate-1"],
                        }
                    ]
                }
            }
        )

        with patch("query.write.core.cypher.get_memgraph_bolt_client", return_value=client):
            write_relationship_candidates(
                [
                    {
                        "job_id": "job-1",
                        "left_node": "law-1",
                        "right_node": "policy-1",
                        "relationship_type": "PROVIDES_LEGAL_BASIS_FOR",
                        "relationship_direction": "left_to_right",
                        "evidence_text": "다른 문서에서 두 노드의 관계를 설명함",
                        "rationale": "제3 문서 근거가 없는 직접 endpoint 관계",
                    }
                ]
            )

        _, query, parameters = client.calls[0]
        candidate = parameters["candidates"][0]
        self.assertIn("OPTIONAL MATCH (evidence {id: candidate.evidence_node_id})", query)
        self.assertIsNone(candidate["evidence_node_id"])
        self.assertEqual(candidate["left_node"], "law-1")
        self.assertEqual(candidate["right_node"], "policy-1")

    def test_relationship_candidate_status_rejects_unknown_values(self) -> None:
        with self.assertRaises(ValidationError):
            RelationshipCandidateNode(
                id="candidate-1",
                job_id="job-1",
                left_node="law-1",
                right_node="policy-1",
                relationship_type="REFERENCES",
                evidence_text="sample",
                rationale="sample",
                status="unknown",
            )

    def test_relationship_candidate_status_uses_enum_values(self) -> None:
        candidate = RelationshipCandidateNode(
            id="candidate-1",
            job_id="job-1",
            left_node="law-1",
            right_node="policy-1",
            relationship_type="REFERENCES",
            evidence_text="sample",
            rationale="sample",
            status=RelationshipCandidateStatus.APPROVED,
        )

        self.assertEqual(candidate.model_dump(mode="json")["status"], "approved")

    def test_review_note_write_uses_relationship_candidate_id(self) -> None:
        client = FakeMemgraphClient({"*": {"rows": [{"note": {"id": "note-1"}}]}})

        with patch("query.write.core.cypher.get_memgraph_bolt_client", return_value=client):
            store_review_note(
                candidate_id="candidate-1",
                action="yes",
                reviewer="tester",
                note="근거가 명확함",
            )

        _, query, parameters = client.calls[0]
        self.assertIn("HAS_REVIEW_NOTE", query)
        self.assertEqual(parameters["note"]["relationship_candidate_id"], "candidate-1")


class QuerySchemaContractsTest(unittest.TestCase):
    def test_review_note_belongs_to_relationship_candidate(self) -> None:
        note = ReviewNoteNode(
            id="note-1",
            relationship_candidate_id="candidate-1",
            action="yes",
            reviewer="tester",
            note="이 관계는 조례 근거가 명확함",
        )

        self.assertEqual(note.relationship_candidate_id, "candidate-1")

    def test_agent_memory_is_evidence_backed_artifact(self) -> None:
        memory = AgentMemoryNode(
            id="memory-1",
            content="사용자는 지역 scope가 명확하지 않은 관계 candidate를 거절하는 경향이 있다.",
            evidence_review_note_ids=["note-1"],
            evidence_relationship_candidate_ids=["candidate-1"],
        )

        self.assertEqual(memory.memory_kind, "review_preference")
        self.assertEqual(memory.author_agent, "memory_update_agent")
        self.assertEqual(memory.evidence_review_note_ids, ["note-1"])


if __name__ == "__main__":
    unittest.main()
