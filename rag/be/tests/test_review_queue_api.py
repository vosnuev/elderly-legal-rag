from __future__ import annotations

import asyncio
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from api.ingest.review import decide_edge_candidates_for_job, list_edge_candidates
from knowledge_runtime.schemas import (
    ReviewCandidateListResponse,
    ReviewJobDecision,
    ReviewJobDecisionRequest,
)
from knowledge_runtime.service.reviews import ReviewWorkService


class ReviewQueueApiTest(unittest.TestCase):
    def test_edge_candidate_route_passes_job_and_document_filters(self) -> None:
        with patch("api.ingest.review.knowledge_runtime") as runtime:
            runtime.reviews.list_pending.return_value = ReviewCandidateListResponse()

            result = list_edge_candidates(
                limit=7,
                job_id="job-1",
                document_id="doc-1",
                status="finished",
            )

        self.assertEqual(result.rows, [])
        runtime.reviews.list_pending.assert_called_once_with(
            limit=7,
            job_id="job-1",
            document_id="doc-1",
            status_filter="finished",
        )

    def test_review_service_passes_filters_to_query_layer(self) -> None:
        service = ReviewWorkService(submitter=object(), projector=object())

        with patch(
            "knowledge_runtime.service.reviews.list_pending_review_candidates",
            return_value={"rows": []},
        ) as list_pending:
            result = service.list_pending(
                limit=7,
                job_id="job-1",
                document_id="doc-1",
                status_filter="all",
            )

        self.assertEqual(result.rows, [])
        list_pending.assert_called_once_with(
            limit=7,
            job_id="job-1",
            document_id="doc-1",
            status_filter="all",
        )

    def test_review_service_returns_typed_candidate_rows(self) -> None:
        service = ReviewWorkService(submitter=object(), projector=object())

        with patch(
            "knowledge_runtime.service.reviews.list_pending_review_candidates",
            return_value={
                "columns": ["candidate"],
                "rows": [
                    {
                        "candidate": {
                            "id": "candidate-1",
                            "job_id": "job-1",
                            "left_node": "chunk-1",
                            "right_node": "chunk-2",
                            "relationship_type": "RELATED_TO",
                            "source_chunk_name": "제1조 목적",
                            "source_chunk_description": "문서 목적 조항을 담은 청크",
                            "source_chunk_text": "제1조 원문 청크",
                            "source_chunk_label": "제1조 목적",
                            "target_chunk_id": "chunk-2",
                            "target_chunk_name": "제2조 정의",
                            "target_chunk_description": "문서 정의 조항을 담은 청크",
                            "target_chunk_text": "제2조 원문 청크",
                            "evidence_text": "근거 문장",
                            "rationale": "후보 생성 이유",
                        }
                    }
                ],
                "row_count": 1,
                "elapsed_ms": 1.5,
            },
        ):
            result = service.list_pending(limit=7)

        self.assertEqual(result.row_count, 1)
        self.assertEqual(result.rows[0].candidate.id, "candidate-1")
        self.assertEqual(result.rows[0].candidate.source_chunk_name, "제1조 목적")
        self.assertEqual(
            result.rows[0].candidate.source_chunk_description,
            "문서 목적 조항을 담은 청크",
        )
        self.assertEqual(result.rows[0].candidate.source_chunk_text, "제1조 원문 청크")
        self.assertEqual(result.rows[0].candidate.source_chunk_label, "제1조 목적")
        self.assertEqual(result.rows[0].candidate.target_chunk_id, "chunk-2")
        self.assertEqual(result.rows[0].candidate.target_chunk_text, "제2조 원문 청크")
        self.assertEqual(result.rows[0].candidate.status, "pending_review")

    def test_job_decision_route_delegates_to_runtime_review_service(self) -> None:
        request = ReviewJobDecisionRequest(
            reviewer="tester",
            decisions=[
                ReviewJobDecision(candidate_id="candidate-1", action="yes", note="ok")
            ],
        )
        with patch("api.ingest.review.knowledge_runtime") as runtime:
            runtime.reviews.decide_job = AsyncMock(return_value=SimpleNamespace(job_id="job-1"))

            response = asyncio.run(decide_edge_candidates_for_job("job-1", request))

        self.assertEqual(response.job_id, "job-1")
        runtime.reviews.decide_job.assert_called_once_with(
            job_id="job-1",
            request=request,
        )

    def test_review_service_submits_job_level_decisions(self) -> None:
        submitter = FakeReviewSubmitter()
        projector = FakeProjector()
        service = ReviewWorkService(submitter=submitter, projector=projector)

        with patch(
            "knowledge_runtime.service.reviews.read_relationship_candidate",
            side_effect=[
                {"id": "candidate-1", "job_id": "job-1", "status": "pending_review"},
                {"id": "candidate-2", "job_id": "job-1", "status": "pending_review"},
            ],
        ):
            result = asyncio.run(
                service.decide_job(
                    job_id="job-1",
                    request=ReviewJobDecisionRequest(
                        reviewer="tester",
                        decisions=[
                            ReviewJobDecision(
                                candidate_id="candidate-1",
                                action="yes",
                                note="approved",
                            ),
                            ReviewJobDecision(
                                candidate_id="candidate-2",
                                action="no",
                                note="too broad",
                            ),
                        ],
                    ),
                )
            )

        self.assertEqual(result.job_id, "job-1")
        self.assertEqual(
            submitter.batch_calls,
            [
                {
                    "job_id": "job-1",
                    "reviewer": "tester",
                    "decisions": [
                        {
                            "candidate_id": "candidate-1",
                            "action": "yes",
                            "note": "approved",
                        },
                        {
                            "candidate_id": "candidate-2",
                            "action": "no",
                            "note": "too broad",
                        },
                    ],
                }
            ],
        )


class FakeReviewSubmitter:
    def __init__(self) -> None:
        self.batch_calls: list[dict[str, object]] = []

    async def submit_review_batch(
        self,
        *,
        job_id: str,
        reviewer: str,
        decisions: list[dict[str, object]],
    ):  # noqa: ANN201
        self.batch_calls.append(
            {
                "job_id": job_id,
                "reviewer": reviewer,
                "decisions": decisions,
            }
        )
        return SimpleNamespace(accepted=True)


class FakeProjector:
    def status(self, job_id: str):  # noqa: ANN201
        return SimpleNamespace(job_id=job_id)


if __name__ == "__main__":
    unittest.main()
