from __future__ import annotations

import unittest
from unittest.mock import patch

from pipeline.graphs.candidate_review_graph import CandidateReviewGraph
from pipeline.graphs.document_construction_graph import DocumentConstructionGraph
from pipeline.schemas import (
    GraphIngestPhase,
    ReviewAction,
)


class FakeChunkingAgent:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def run(self, *, job_id, document_id):  # noqa: ANN001, ANN201
        self.events.append(f"chunk:{job_id}:{document_id}")
        return ["chunk-1"]


class FakeEmbeddingDispatchNodeService:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def dispatch(self, *, job_id, chunk_ids):  # noqa: ANN001, ANN201
        self.events.append(f"embed:{job_id}:{len(chunk_ids)}")
        return chunk_ids


class FakeGraphCandidateAgent:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.call_count = 0

    def run(self, *, job_id, document_id, chunk_ids):  # noqa: ANN001, ANN201
        self.call_count += 1
        self.events.append(f"candidate:{job_id}:{self.call_count}")
        return [f"candidate-{self.call_count}"]


class FakeNoCandidateAgent(FakeGraphCandidateAgent):
    def run(self, *, job_id, document_id, chunk_ids):  # noqa: ANN001, ANN201
        self.call_count += 1
        self.events.append(f"candidate:{job_id}:{self.call_count}")
        return []


class FakeActualEdgeMaterializationNodeService:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def materialize(self, *, candidate_id, reviewer):  # noqa: ANN001, ANN201
        self.events.append(f"materialize:{candidate_id}:{reviewer}")


class FakeReviewStatusNodeService:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def apply(self, *, candidate_id, action, reviewer):  # noqa: ANN001, ANN201
        self.events.append(f"status:{candidate_id}:{action.value}:{reviewer}")


class FakeReviewNoteNodeService:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def store_note(self, *, candidate_id, action, reviewer, note):  # noqa: ANN001, ANN201
        self.events.append(f"review-note:{candidate_id}:{action}:{reviewer}:{note or ''}")
        if not note:
            return {"stored": False}
        return {
            "rows": [
                {
                    "note": {
                        "id": f"note-{candidate_id}",
                        "relationship_candidate_id": candidate_id,
                        "action": action,
                        "reviewer": reviewer,
                        "note": note,
                    }
                }
            ]
        }


class FakeMemoryNodeService:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def append_from_review_note(self, *, review_note):  # noqa: ANN001, ANN201
        if not review_note:
            self.events.append("memory:none")
            return {"stored": False}
        self.events.append(f"memory:{review_note['id']}")
        return {"rows": [{"memory_id": "memory-1"}]}


class FakeRevisionAgent:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def run(self, *, original_candidate, note):  # noqa: ANN001, ANN201
        props = original_candidate.get("properties", original_candidate)
        self.events.append(f"revise:{props['id']}:{note or ''}")
        return ["candidate-2"]


class DocumentConstructionGraphTest(unittest.TestCase):
    def test_document_construction_reaches_pending_review(self) -> None:
        events: list[str] = []
        graph = DocumentConstructionGraph()
        graph._chunking_agent = FakeChunkingAgent(events)
        graph._embedding_dispatch_node_service = FakeEmbeddingDispatchNodeService(events)
        graph._graph_candidate_agent = FakeGraphCandidateAgent(events)

        with patch(
            "pipeline.graphs.document_construction_graph.get_document_record",
            return_value=_document_record(),
        ):
            result = graph.invoke(job_id="job-1", document_id="doc-1")

        self.assertEqual(result.phase, GraphIngestPhase.PENDING_REVIEW)
        self.assertEqual(result.document_id, "doc-1")
        self.assertEqual(result.chunk_count, 1)
        self.assertEqual(result.candidate_count, 1)
        self.assertEqual(result.pending_review_count, 1)
        self.assertEqual(
            events,
            [
                "chunk:job-1:doc-1",
                "embed:job-1:1",
                "candidate:job-1:1",
            ],
        )

    def test_document_construction_completes_when_no_candidates_are_created(self) -> None:
        events: list[str] = []
        candidate_agent = FakeNoCandidateAgent(events)
        graph = DocumentConstructionGraph()
        graph._chunking_agent = FakeChunkingAgent(events)
        graph._embedding_dispatch_node_service = FakeEmbeddingDispatchNodeService(events)
        graph._graph_candidate_agent = candidate_agent

        with patch(
            "pipeline.graphs.document_construction_graph.get_document_record",
            return_value=_document_record(),
        ):
            result = graph.invoke(job_id="job-1", document_id="doc-1")

        self.assertEqual(candidate_agent.call_count, 1)
        self.assertEqual(result.phase, GraphIngestPhase.COMPLETED)


class CandidateReviewGraphTest(unittest.TestCase):
    def test_yes_review_materializes_edge_and_records_preference(self) -> None:
        events: list[str] = []
        graph = CandidateReviewGraph()
        graph._actual_edge_materialization_node_service = (
            FakeActualEdgeMaterializationNodeService(events)
        )
        graph._review_status_node_service = FakeReviewStatusNodeService(events)
        graph._review_note_node_service = FakeReviewNoteNodeService(events)
        graph._memory_node_service = FakeMemoryNodeService(events)
        graph._graph_candidate_revision_agent = FakeRevisionAgent(events)

        with patch(
            "pipeline.graphs.candidate_review_graph.read_relationship_candidate",
            return_value=_candidate_record(),
        ):
            result = graph.invoke(
                candidate_id="candidate-1",
                action=ReviewAction.YES,
                reviewer="tester",
                note="approved",
            )

        self.assertEqual(result.job_id, "job-1")
        self.assertEqual(result.phase, GraphIngestPhase.COMPLETED)
        self.assertEqual(
            events,
            [
                "materialize:candidate-1:tester",
                "status:candidate-1:yes:tester",
                "review-note:candidate-1:yes:tester:approved",
                "memory:note-candidate-1",
            ],
        )

    def test_retry_review_runs_revision_agent_without_materialization(self) -> None:
        events: list[str] = []
        graph = CandidateReviewGraph()
        graph._actual_edge_materialization_node_service = (
            FakeActualEdgeMaterializationNodeService(events)
        )
        graph._review_status_node_service = FakeReviewStatusNodeService(events)
        graph._review_note_node_service = FakeReviewNoteNodeService(events)
        graph._memory_node_service = FakeMemoryNodeService(events)
        graph._graph_candidate_revision_agent = FakeRevisionAgent(events)

        with patch(
            "pipeline.graphs.candidate_review_graph.read_relationship_candidate",
            return_value=_candidate_record(),
        ):
            result = graph.invoke(
                candidate_id="candidate-1",
                action=ReviewAction.RETRY,
                reviewer="tester",
                note="target should be broader",
            )

        self.assertEqual(result.job_id, "job-1")
        self.assertEqual(result.phase, GraphIngestPhase.COMPLETED)
        self.assertEqual(result.candidate_count, 1)
        self.assertNotIn("materialize:candidate-1:tester", events)
        self.assertEqual(events[0], "revise:candidate-1:target should be broader")


def _document_record() -> dict[str, object]:
    return {
        "id": "doc-1",
        "entry_number": 1,
        "document_version": 1,
        "content_hash": "hash",
        "raw_content": "sample ordinance text",
        "file_name": "sample.txt",
        "source_type": "txt",
        "metadata": {},
    }


def _candidate_record() -> dict[str, object]:
    return {
        "id": "candidate-1",
        "job_id": "job-1",
        "left_node": "chunk-1",
        "right_node": "law-1",
        "relationship_type": "SUPPORTS",
        "relationship_direction": "left_to_right",
        "evidence_node_id": "chunk-1",
        "evidence_text": "sample ordinance text",
        "rationale": "test candidate",
        "status": "pending_review",
        "version": 1,
    }


if __name__ == "__main__":
    unittest.main()
