from __future__ import annotations

import os
import unittest
from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

from external.memgraph import get_memgraph_bolt_client
from query.read.core import read_query
from query.schema import DocumentNode
from query.write import (
    register_document,
    write_chunks_for_document,
    write_relationship_candidates,
)


@unittest.skipUnless(
    os.getenv("RAG_TEST_MEMGRAPH") == "1",
    "Set RAG_TEST_MEMGRAPH=1 to run live Memgraph integration checks.",
)
class LiveMemgraphQueryTest(unittest.TestCase):
    def test_query_layer_writes_and_reads_schema_aware_graph(self) -> None:
        suffix = uuid4().hex[:8]
        document_id = f"live-test-doc-{suffix}"
        job_id = f"live-test-job-{suffix}"
        raw_content = "live memgraph test document"

        get_memgraph_bolt_client().verify_connectivity()

        register_document(
            DocumentNode(
                id=document_id,
                entry_number=0,
                document_version=1,
                content_hash=sha256(raw_content.encode("utf-8")).hexdigest(),
                raw_content=raw_content,
                file_name="live-test.txt",
                source_type="txt",
                metadata={
                    "registered_at": datetime.now(UTC).isoformat(),
                    "last_ingest_job_id": job_id,
                },
            )
        )
        chunk_result = write_chunks_for_document(
            document_id=document_id,
            job_id=job_id,
            chunks=[
                {
                    "chunk_index": 1,
                    "text": "live memgraph test chunk",
                    "start_unique_string": "live",
                    "end_unique_string": "chunk",
                }
            ],
        )
        chunk_id = chunk_result["rows"][0]["chunk_ids"][0]
        candidate_result = write_relationship_candidates(
            [
                {
                    "job_id": job_id,
                    "left_node": chunk_id,
                    "right_node": document_id,
                    "relationship_type": "REFERENCES",
                    "relationship_direction": "left_to_right",
                    "evidence_node_id": chunk_id,
                    "evidence_text": "live memgraph test chunk",
                    "rationale": "live integration check",
                }
            ]
        )
        candidate_id = candidate_result["rows"][0]["edge_candidate_ids"][0]

        read_result = read_query(
            """
            MATCH (document:Document {id: $document_id})-[:HAS_CHUNK]->(chunk:Chunk)
            MATCH (chunk)-[:EVIDENCES_RELATIONSHIP_CANDIDATE]->(candidate:RelationshipCandidate)
            RETURN document.id AS document_id,
                   chunk.id AS chunk_id,
                   candidate.id AS candidate_id,
                   candidate.status AS status
            """,
            {"document_id": document_id},
            max_rows=10,
        )

        self.assertEqual(read_result["row_count"], 1)
        row = read_result["rows"][0]
        self.assertEqual(row["document_id"], document_id)
        self.assertEqual(row["chunk_id"], chunk_id)
        self.assertEqual(row["candidate_id"], candidate_id)
        self.assertEqual(row["status"], "pending_review")


if __name__ == "__main__":
    unittest.main()
