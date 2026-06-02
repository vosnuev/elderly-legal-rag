from __future__ import annotations

import unittest
from unittest.mock import patch

from api.ingest.review import list_edge_candidates
from knowledge_runtime.service.reviews import ReviewWorkService


class ReviewQueueApiTest(unittest.TestCase):
    def test_edge_candidate_route_passes_job_and_document_filters(self) -> None:
        with patch("api.ingest.review.knowledge_runtime") as runtime:
            runtime.reviews.list_pending.return_value = {"rows": []}

            result = list_edge_candidates(limit=7, job_id="job-1", document_id="doc-1")

        self.assertEqual(result, {"rows": []})
        runtime.reviews.list_pending.assert_called_once_with(
            limit=7,
            job_id="job-1",
            document_id="doc-1",
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
            )

        self.assertEqual(result, {"rows": []})
        list_pending.assert_called_once_with(
            limit=7,
            job_id="job-1",
            document_id="doc-1",
        )


if __name__ == "__main__":
    unittest.main()
