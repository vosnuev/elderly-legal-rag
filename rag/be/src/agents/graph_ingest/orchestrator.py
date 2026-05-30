from __future__ import annotations

from typing import Literal

from langgraph.graph import END, START, StateGraph

from agents.graph_ingest.schemas import (
    GraphIngestPhase,
    IngestGraphResult,
    RegisteredDocument,
    ReviewAction,
)
from agents.graph_ingest.services.actual_edge_materialization_service import (
    ActualEdgeMaterializationService,
)
from agents.graph_ingest.services.embedding_dispatch_service import EmbeddingDispatchService
from agents.graph_ingest.services.preference_memory_service import PreferenceMemoryService
from agents.graph_ingest.services.review_status_service import ReviewStatusService
from agents.graph_ingest.state import CandidateReviewActionState, GraphIngestState
from agents.graph_ingest.sub_agents.chunking_agent import ChunkingAgent
from agents.graph_ingest.sub_agents.feedback_judge_agent import FeedbackJudgeAgent
from agents.graph_ingest.sub_agents.graph_candidate_agent import GraphCandidateAgent
from agents.graph_ingest.sub_agents.graph_candidate_revision_agent import (
    GraphCandidateRevisionAgent,
)
from ingest_tasks.progress_service import IngestProgressService
from logger import bind_logger
from query.service import MemgraphQueryService, get_memgraph_query_service


class GraphIngestOrchestrator:
    def __init__(self, query_service: MemgraphQueryService | None = None) -> None:
        self._query_service = query_service or get_memgraph_query_service()
        self._embedding_dispatch_service = EmbeddingDispatchService(self._query_service)
        self._actual_edge_materialization_service = ActualEdgeMaterializationService(
            self._query_service
        )
        self._preference_memory_service = PreferenceMemoryService(self._query_service)
        self._review_status_service = ReviewStatusService(self._query_service)
        self._ingest_progress_service = IngestProgressService(self._query_service)
        self._chunking_agent = ChunkingAgent()
        self._graph_candidate_agent = GraphCandidateAgent()
        self._feedback_judge_agent = FeedbackJudgeAgent()
        self._graph_candidate_revision_agent = GraphCandidateRevisionAgent()
        self._logger = bind_logger(component="graph_ingest_orchestrator")
        self._construction_graph = self._build_construction_graph()
        self._review_graph = self._build_review_graph()

    def start_construction(
        self,
        *,
        job_id: str,
        document_id: str,
    ) -> IngestGraphResult:
        try:
            self._logger.bind(
                job_id=job_id,
                document_id=document_id,
            ).info("graph construction invoked")
            state = self._construction_graph.invoke(
                {
                    "job_id": job_id,
                    "document_id": document_id,
                    "phase": GraphIngestPhase.GRAPH_ADD_STARTED,
                    "retry_count": 0,
                    "warnings": [],
                    "errors": [],
                }
            )
            return self._state_to_result(state)
        except Exception as exc:  # noqa: BLE001
            self._logger.bind(
                job_id=job_id,
                document_id=document_id,
            ).exception("graph construction failed")
            return self._ingest_progress_service.mark(
                job_id=job_id,
                phase=GraphIngestPhase.FAILED,
                document_id=document_id,
                chunk_count=0,
                candidate_count=0,
                errors=[str(exc)],
            )

    def resume_review(
        self,
        *,
        candidate_id: str,
        action: ReviewAction,
        reviewer: str,
        note: str | None = None,
    ) -> IngestGraphResult:
        try:
            self._logger.bind(
                candidate_id=candidate_id,
                action=action.value,
                reviewer=reviewer,
            ).info("candidate review action invoked")
            state = self._review_graph.invoke(
                {
                    "candidate_id": candidate_id,
                    "action": action,
                    "reviewer": reviewer,
                    "note": note,
                    "warnings": [],
                    "errors": [],
                }
            )
            return IngestGraphResult(
                job_id=str(
                    state.get("candidate", {})
                    .get("properties", state.get("candidate", {}))
                    .get("job_id", "")
                ),
                phase=state.get("phase", GraphIngestPhase.COMPLETED),
                candidate_count=len(state.get("candidates", [])),
                warnings=state.get("warnings", []),
                errors=state.get("errors", []),
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.bind(
                candidate_id=candidate_id,
                action=action.value,
                reviewer=reviewer,
            ).exception("candidate review action failed")
            return IngestGraphResult(
                job_id="",
                phase=GraphIngestPhase.FAILED,
                errors=[str(exc)],
            )

    def _build_construction_graph(self):
        builder = StateGraph(GraphIngestState)
        builder.add_node("document_load_service", self._load_document)
        builder.add_node("chunking_agent", self._run_chunking_agent)
        builder.add_node("embedding_dispatch_service", self._dispatch_embeddings)
        builder.add_node("graph_candidate_agent", self._run_graph_candidate_agent)
        builder.add_node("feedback_judge_agent", self._run_feedback_judge_agent)
        builder.add_node("ingest_progress_service", self._mark_ingest_progress)
        builder.add_edge(START, "document_load_service")
        builder.add_edge("document_load_service", "chunking_agent")
        builder.add_edge("chunking_agent", "embedding_dispatch_service")
        builder.add_edge("embedding_dispatch_service", "graph_candidate_agent")
        builder.add_edge("graph_candidate_agent", "feedback_judge_agent")
        builder.add_conditional_edges(
            "feedback_judge_agent",
            self._route_after_feedback,
            {
                "retry": "graph_candidate_agent",
                "finish": "ingest_progress_service",
            },
        )
        builder.add_edge("ingest_progress_service", END)
        return builder.compile()

    def _build_review_graph(self):
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

    def _load_document(self, state: GraphIngestState) -> dict[str, object]:
        record = self._query_service.get_document_record(state["document_id"])
        document = RegisteredDocument.model_validate(record)
        return {"document": document, "phase": GraphIngestPhase.DOCUMENT_REGISTERED}

    def _run_chunking_agent(self, state: GraphIngestState) -> dict[str, object]:
        chunks = self._chunking_agent.run(
            job_id=state["job_id"],
            document=state["document"],
        )
        return {"chunks": chunks, "phase": GraphIngestPhase.CHUNKED}

    def _dispatch_embeddings(self, state: GraphIngestState) -> dict[str, object]:
        chunks = self._embedding_dispatch_service.dispatch(
            job_id=state["job_id"],
            chunks=state.get("chunks", []),
        )
        return {
            "chunks": chunks,
            "phase": GraphIngestPhase.EMBEDDING_DISPATCHED,
            "warnings": list(state.get("warnings", [])),
        }

    def _run_graph_candidate_agent(self, state: GraphIngestState) -> dict[str, object]:
        candidates = self._graph_candidate_agent.run(
            job_id=state["job_id"],
            chunks=state.get("chunks", []),
        )
        return {
            "candidates": candidates,
            "phase": GraphIngestPhase.CANDIDATES_GENERATED,
        }

    def _run_feedback_judge_agent(self, state: GraphIngestState) -> dict[str, object]:
        feedback = self._feedback_judge_agent.run(
            job_id=state["job_id"],
            chunks=state.get("chunks", []),
            candidates=state.get("candidates", []),
        )
        retry_count = state.get("retry_count", 0)
        update: dict[str, object] = {"feedback": feedback}
        if feedback.incomplete:
            update["retry_count"] = retry_count + 1
            if retry_count >= 1:
                update["phase"] = GraphIngestPhase.NEEDS_RETRY
        elif not feedback.ready_for_review:
            update["phase"] = GraphIngestPhase.NEEDS_RETRY
        else:
            update["phase"] = (
                GraphIngestPhase.PENDING_REVIEW
                if state.get("candidates")
                else GraphIngestPhase.COMPLETED
            )
        return update

    def _route_after_feedback(
        self,
        state: GraphIngestState,
    ) -> Literal["retry", "finish"]:
        feedback = state.get("feedback")
        retry_count = state.get("retry_count", 0)
        if feedback and feedback.incomplete and retry_count <= 1:
            return "retry"
        return "finish"

    def _mark_ingest_progress(self, state: GraphIngestState) -> dict[str, object]:
        phase = state.get("phase", GraphIngestPhase.COMPLETED)
        result = self._ingest_progress_service.mark(
            job_id=state["job_id"],
            phase=phase,
            document_id=state.get("document").id if state.get("document") else None,
            chunk_count=len(state.get("chunks", [])),
            candidate_count=len(state.get("candidates", [])),
            warnings=state.get("warnings", []),
            errors=state.get("errors", []),
        )
        return {"phase": result.phase}

    def _load_candidate_context(
        self,
        state: CandidateReviewActionState,
    ) -> dict[str, object]:
        candidate = self._query_service.get_edge_candidate(state["candidate_id"])
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
        candidates = self._graph_candidate_revision_agent.run(
            original_candidate=state["candidate"],
            note=state.get("note"),
        )
        return {"candidates": candidates}

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
        candidate_props = state.get("candidate", {}).get(
            "properties",
            state.get("candidate", {}),
        )
        self._ingest_progress_service.mark(
            job_id=str(candidate_props.get("job_id") or ""),
            phase=state.get("phase", GraphIngestPhase.COMPLETED),
            document_id=None,
            chunk_count=0,
            candidate_count=len(state.get("candidates", [])),
            warnings=state.get("warnings", []),
            errors=state.get("errors", []),
        )
        return {}

    def _state_to_result(self, state: GraphIngestState) -> IngestGraphResult:
        return IngestGraphResult(
            job_id=state["job_id"],
            phase=state.get("phase", GraphIngestPhase.COMPLETED),
            document_id=state.get("document").id if state.get("document") else None,
            chunk_count=len(state.get("chunks", [])),
            candidate_count=len(state.get("candidates", [])),
            pending_review_count=(
                len(state.get("candidates", []))
                if state.get("phase") is GraphIngestPhase.PENDING_REVIEW
                else 0
            ),
            warnings=state.get("warnings", []),
            errors=state.get("errors", []),
        )
