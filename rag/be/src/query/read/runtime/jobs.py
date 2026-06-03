from __future__ import annotations

from typing import Any

from external.memgraph import get_memgraph_bolt_client
from query.schema import RelationshipCandidateStatus


def read_ingest_job(job_id: str) -> dict[str, Any]:
    return get_memgraph_bolt_client().execute_read(
        """
        MATCH (job:IngestJob {id: $job_id})
        RETURN job
        LIMIT 1
        """,
        {"job_id": job_id},
    )


def list_ingest_job_progress(*, limit: int = 50) -> dict[str, Any]:
    return get_memgraph_bolt_client().execute_read(
        """
        MATCH (job:IngestJob)
        OPTIONAL MATCH (candidate:RelationshipCandidate {job_id: job.job_id})
        WITH job,
             [candidate IN collect(DISTINCT candidate) WHERE candidate IS NOT NULL] AS candidates
        OPTIONAL MATCH (direct_document:Document {id: job.document_id})
        OPTIONAL MATCH (candidate_document:Document)-[:HAS_CHUNK]->(candidate_chunk:Chunk)
        WHERE candidate_chunk.id IN [candidate IN candidates | candidate.left_node]
           OR candidate_chunk.id IN [candidate IN candidates | candidate.right_node]
           OR candidate_chunk.id IN [candidate IN candidates | candidate.evidence_node_id]
           OR candidate_chunk.id IN [candidate IN candidates | candidate.source_chunk_id]
           OR candidate_chunk.id IN [candidate IN candidates | candidate.target_chunk_id]
        WITH job,
             direct_document,
             candidates,
             collect(DISTINCT candidate_document) AS candidate_documents
        WITH job,
             coalesce(direct_document, head(candidate_documents)) AS document,
             candidates
        RETURN job,
               document,
               size(candidates) AS candidate_count,
               size([
                   candidate IN candidates
                   WHERE coalesce(candidate.status, "pending_review") = "pending_review"
               ]) AS pending_review_count
        ORDER BY job.updated_at DESC
        LIMIT $limit
        """,
        {"limit": limit},
    )


def summarize_job_progress(job_id: str) -> dict[str, Any]:
    return get_memgraph_bolt_client().execute_read(
        """
        MATCH (job:IngestJob {id: $job_id})
        OPTIONAL MATCH (candidate:RelationshipCandidate {job_id: $job_id})
        WITH job, [candidate IN collect(DISTINCT candidate) WHERE candidate IS NOT NULL] AS candidates
        OPTIONAL MATCH (direct_document:Document {id: job.document_id})
        OPTIONAL MATCH (candidate_document:Document)-[:HAS_CHUNK]->(candidate_chunk:Chunk)
        WHERE candidate_chunk.id IN [candidate IN candidates | candidate.left_node]
           OR candidate_chunk.id IN [candidate IN candidates | candidate.right_node]
           OR candidate_chunk.id IN [candidate IN candidates | candidate.evidence_node_id]
           OR candidate_chunk.id IN [candidate IN candidates | candidate.source_chunk_id]
           OR candidate_chunk.id IN [candidate IN candidates | candidate.target_chunk_id]
        WITH job,
             direct_document,
             candidates,
             collect(DISTINCT candidate_document) AS candidate_documents
        WITH job,
             candidates,
             CASE
                 WHEN direct_document IS NULL THEN candidate_documents
                 ELSE [direct_document] + candidate_documents
             END AS raw_documents
        UNWIND CASE WHEN size(raw_documents) = 0 THEN [NULL] ELSE raw_documents END AS document
        WITH job, candidates, collect(DISTINCT document) AS documents
        RETURN job,
               documents,
               size(documents) AS document_count,
               size(candidates) AS candidate_count,
               size([candidate IN candidates WHERE coalesce(candidate.status, "pending_review") = "pending_review"]) AS pending_review_count
        """,
        {"job_id": job_id},
    )


def summarize_candidate_review_progress(job_id: str) -> dict[str, Any]:
    return get_memgraph_bolt_client().execute_read(
        """
        OPTIONAL MATCH (candidate:RelationshipCandidate {job_id: $job_id})
        WITH [candidate IN collect(candidate) WHERE candidate IS NOT NULL] AS candidates
        RETURN size(candidates) AS candidate_count,
               size([
                   candidate IN candidates
                   WHERE coalesce(candidate.status, $pending_review_status) = $pending_review_status
               ]) AS pending_review_count
        """,
        {
            "job_id": job_id,
            "pending_review_status": RelationshipCandidateStatus.PENDING_REVIEW.value,
        },
    )
