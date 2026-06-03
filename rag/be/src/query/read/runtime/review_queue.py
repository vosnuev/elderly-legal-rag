from __future__ import annotations

from typing import Any, Literal

from external.memgraph import get_memgraph_bolt_client
from query.utils import bounded_limit


ReviewCandidateStatusFilter = Literal["pending", "finished", "all"]


def list_pending_review_candidates(
    document_id: str | None = None,
    job_id: str | None = None,
    limit: int = 50,
    status_filter: ReviewCandidateStatusFilter = "pending",
) -> dict[str, Any]:
    return get_memgraph_bolt_client().execute_read(
        """
        MATCH (candidate:RelationshipCandidate)
        WHERE (
            $status_filter = "all"
            OR (
                $status_filter = "pending"
                AND coalesce(candidate.status, "pending_review") = "pending_review"
            )
            OR (
                $status_filter = "finished"
                AND coalesce(candidate.status, "pending_review") <> "pending_review"
            )
        )
          AND ($job_id IS NULL OR candidate.job_id = $job_id)
        OPTIONAL MATCH (evidence)-[:EVIDENCES_RELATIONSHIP_CANDIDATE]->(candidate)
        WHERE $document_id IS NULL
          OR evidence.id = $document_id
          OR evidence.document_id = $document_id
          OR candidate.evidence_node_id = $document_id
          OR candidate.left_node = $document_id
          OR candidate.right_node = $document_id
        WITH DISTINCT candidate
        OPTIONAL MATCH (source_chunk:Chunk)
        WHERE source_chunk.id = coalesce(
            candidate.source_chunk_id,
            candidate.evidence_node_id,
            candidate.left_node
        )
        OPTIONAL MATCH (target_chunk:Chunk)
        WHERE target_chunk.id = coalesce(
            candidate.target_chunk_id,
            candidate.right_node
        )
        OPTIONAL MATCH (evidence_chunk:Chunk)
        WHERE evidence_chunk.id = candidate.evidence_node_id
        OPTIONAL MATCH (candidate)-[:HAS_REVIEW_NOTE]->(review_note:ReviewNote)
        WITH candidate, source_chunk, target_chunk, evidence_chunk, review_note
        ORDER BY candidate.version ASC, candidate.id ASC
        RETURN candidate {
            .*,
            source_node: coalesce(candidate.source_node, candidate.left_node),
            target_node: coalesce(candidate.target_node, candidate.right_node),
            source_chunk_id: coalesce(candidate.source_chunk_id, candidate.evidence_node_id),
            source_chunk_name: coalesce(source_chunk.chunk_name, evidence_chunk.chunk_name),
            source_chunk_description: coalesce(source_chunk.chunk_description, evidence_chunk.chunk_description),
            source_chunk_summary: coalesce(source_chunk.summary, evidence_chunk.summary),
            source_chunk_text: coalesce(source_chunk.text, evidence_chunk.text),
            source_chunk_index: coalesce(source_chunk.chunk_index, evidence_chunk.chunk_index),
            source_chunk_label: coalesce(
                source_chunk.chunk_name,
                evidence_chunk.chunk_name,
                source_chunk.summary,
                evidence_chunk.summary,
                CASE
                    WHEN source_chunk.chunk_index IS NULL AND evidence_chunk.chunk_index IS NULL THEN NULL
                    ELSE "Chunk #" + toString(coalesce(source_chunk.chunk_index, evidence_chunk.chunk_index))
                END,
                candidate.source_chunk_id,
                candidate.evidence_node_id
            ),
            target_chunk_id: target_chunk.id,
            target_chunk_name: target_chunk.chunk_name,
            target_chunk_description: target_chunk.chunk_description,
            target_chunk_summary: target_chunk.summary,
            target_chunk_text: target_chunk.text,
            target_chunk_index: target_chunk.chunk_index,
            target_chunk_label: coalesce(
                target_chunk.chunk_name,
                target_chunk.summary,
                CASE
                    WHEN target_chunk.chunk_index IS NULL THEN NULL
                    ELSE "Chunk #" + toString(target_chunk.chunk_index)
                END,
                candidate.target_chunk_id,
                candidate.right_node
            ),
            evidence_chunk_name: evidence_chunk.chunk_name,
            evidence_chunk_description: evidence_chunk.chunk_description,
            evidence_chunk_summary: evidence_chunk.summary,
            evidence_chunk_index: evidence_chunk.chunk_index,
            review_note: review_note.note,
            review_action: review_note.action,
            reviewer: coalesce(candidate.reviewed_by, review_note.reviewer),
            reviewed_at: CASE
                WHEN candidate.reviewed_at IS NULL THEN NULL
                ELSE toString(candidate.reviewed_at)
            END
        } AS candidate
        LIMIT $limit
        """,
        {
            "document_id": document_id,
            "job_id": job_id,
            "limit": bounded_limit(limit),
            "status_filter": status_filter,
        },
    )


def summarize_document_review_queue(document_id: str) -> dict[str, Any]:
    return get_memgraph_bolt_client().execute_read(
        """
        MATCH (document:Document {id: $document_id})
        OPTIONAL MATCH (document)-[:HAS_CHUNK]->(chunk:Chunk)
        WITH document, collect(DISTINCT chunk) AS chunks
        OPTIONAL MATCH (candidate:RelationshipCandidate)
        WHERE candidate.evidence_node_id IN [chunk IN chunks | chunk.id]
           OR candidate.left_node IN [chunk IN chunks | chunk.id]
           OR candidate.right_node IN [chunk IN chunks | chunk.id]
           OR candidate.evidence_node_id = document.id
           OR candidate.left_node = document.id
           OR candidate.right_node = document.id
        WITH document, chunks, collect(DISTINCT candidate) AS candidates
        RETURN document,
               size(chunks) AS chunk_count,
               size(candidates) AS candidate_count,
               size([candidate IN candidates WHERE coalesce(candidate.status, "pending_review") = "pending_review"]) AS pending_review_count,
               [candidate IN candidates | candidate.id] AS candidate_ids
        """,
        {"document_id": document_id},
    )
