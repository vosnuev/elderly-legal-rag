from __future__ import annotations

from typing import Literal

from langgraph.graph import END, START, StateGraph

from pipeline.schemas import GraphIngestPhase, IngestGraphResult, ReviewAction
from pipeline.services.actual_edge_materialization_service import (
    ActualEdgeMaterializationService,
)
from pipeline.services.ingest_progress_service import IngestProgressService
from pipeline.services.preference_memory_service import PreferenceMemoryService
from pipeline.services.review_status_service import ReviewStatusService
from pipeline.state import CandidateReviewActionState
from pipeline.sub_agents.graph_candidate_revision_agent import (
    GraphCandidateRevisionAgent,
)
from query.read.inspection import read_relationship_candidate


class CandidateReviewGraph:
    """User review decision graph for pending relationship candidates."""

    def __init__(self) -> None:
        self._actual_edge_materialization_service = ActualEdgeMaterializationService()
        self._preference_memory_service = PreferenceMemoryService()
        self._review_status_service = ReviewStatusService()
        self._ingest_progress_service = IngestProgressService()
        self._graph_candidate_revision_agent = GraphCandidateRevisionAgent()
        self._graph = self._build_graph()

    def invoke(
        self,
        *,
        candidate_id: str,
        action: ReviewAction,
        reviewer: str,
        note: str | None = None,
    ) -> IngestGraphResult:
        state = self._graph.invoke(
            {
                "candidate_id": candidate_id,
                "action": action,
                "reviewer": reviewer,
                "note": note,
            }
        )
        return self._state_to_result(state)

    def _build_graph(self):
        builder = StateGraph(CandidateReviewActionState)
        builder.add_node("load_candidate_context_service", self._load_candidate_context)
        builder.add_node("actual_edge_materialization_service", self._materialize_edge)
        builder.add_node("review_status_service", self._apply_review_status)
        builder.add_node(
            "graph_candidate_revision_agent",
            self._run_graph_candidate_revision_agent,
        )
        builder.add_node("preference_memory_service", self._store_preference_note)
        builder.add_node("ingest_progress_service", self._mark_review_progress)
        builder.add_edge(START, "load_candidate_context_service")
        builder.add_conditional_edges(
            "load_candidate_context_service",
            self._route_review_action,
            {
                "yes": "actual_edge_materialization_service",
                "no": "review_status_service",
                "retry": "graph_candidate_revision_agent",
            },
        )
        builder.add_edge("actual_edge_materialization_service", "review_status_service")
        builder.add_edge("graph_candidate_revision_agent", "review_status_service")
        builder.add_edge("review_status_service", "preference_memory_service")
        builder.add_edge("preference_memory_service", "ingest_progress_service")
        builder.add_edge("ingest_progress_service", END)
        return builder.compile()

    def _load_candidate_context(
        self,
        state: CandidateReviewActionState,
    ) -> dict[str, object]:
        candidate = read_relationship_candidate(state["candidate_id"])
        return {"candidate": candidate}

    def _route_review_action(
        self,
        state: CandidateReviewActionState,
    ) -> Literal["yes", "no", "retry"]:
        return state["action"].value

    def _materialize_edge(
        self,
        state: CandidateReviewActionState,
    ) -> dict[str, object]:
        self._actual_edge_materialization_service.materialize(
            candidate_id=state["candidate_id"],
            reviewer=state["reviewer"],
        )
        return {"phase": GraphIngestPhase.COMPLETED}

    def _apply_review_status(
        self,
        state: CandidateReviewActionState,
    ) -> dict[str, object]:
        self._review_status_service.apply(
            candidate_id=state["candidate_id"],
            action=state["action"],
            reviewer=state["reviewer"],
        )
        return {"phase": GraphIngestPhase.COMPLETED}

    def _run_graph_candidate_revision_agent(
        self,
        state: CandidateReviewActionState,
    ) -> dict[str, object]:
        edge_candidate_ids = self._graph_candidate_revision_agent.run(
            original_candidate=state["candidate"],
            note=state.get("note"),
        )
        return {"edge_candidate_ids": edge_candidate_ids}

    def _store_preference_note(
        self,
        state: CandidateReviewActionState,
    ) -> dict[str, object]:
        self._preference_memory_service.store_note(
            candidate_id=state["candidate_id"],
            action=state["action"].value,
            reviewer=state["reviewer"],
            note=state.get("note"),
        )
        return {}

    def _mark_review_progress(
        self,
        state: CandidateReviewActionState,
    ) -> dict[str, object]:
        candidate_props = _candidate_properties(state)
        self._ingest_progress_service.mark(
            job_id=str(candidate_props.get("job_id") or ""),
            phase=state.get("phase", GraphIngestPhase.COMPLETED),
            document_id=None,
            chunk_count=0,
            candidate_count=len(state.get("edge_candidate_ids", [])),
        )
        return {}

    def _state_to_result(
        self,
        state: CandidateReviewActionState,
    ) -> IngestGraphResult:
        candidate_props = _candidate_properties(state)
        return IngestGraphResult(
            job_id=str(candidate_props.get("job_id") or ""),
            phase=state.get("phase", GraphIngestPhase.COMPLETED),
            candidate_count=len(state.get("edge_candidate_ids", [])),
        )


def _candidate_properties(state: CandidateReviewActionState) -> dict[str, object]:
    candidate = state.get("candidate", {})
    if not isinstance(candidate, dict):
        return {}
    properties = candidate.get("properties")
    if isinstance(properties, dict):
        return properties
    return candidate
