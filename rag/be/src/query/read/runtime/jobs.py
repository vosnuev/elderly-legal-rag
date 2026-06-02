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


def summarize_job_progress(job_id: str) -> dict[str, Any]:
    return get_memgraph_bolt_client().execute_read(
        """
        MATCH (job:IngestJob {id: $job_id})
        OPTIONAL MATCH (document:Document {id: job.document_id})
        WITH job, collect(DISTINCT document) AS documents
        OPTIONAL MATCH (candidate:RelationshipCandidate {job_id: $job_id})
        WITH job, documents, collect(DISTINCT candidate) AS candidates
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
