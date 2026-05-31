from __future__ import annotations

from typing import Literal

from langgraph.graph import END, START, StateGraph

from pipeline.schemas import GraphIngestPhase, IngestGraphResult, RegisteredDocument
from pipeline.services.embedding_dispatch_service import EmbeddingDispatchService
from pipeline.services.ingest_progress_service import IngestProgressService
from pipeline.state import GraphIngestState
from pipeline.sub_agents.chunking_agent import ChunkingAgent
from pipeline.sub_agents.feedback_judge_agent import FeedbackJudgeAgent
from pipeline.sub_agents.graph_candidate_agent import GraphCandidateAgent
from query.read import get_document_record


class DocumentConstructionGraph:
    """Document -> chunk -> embedding -> candidate -> review-pending graph."""

    def __init__(self) -> None:
        self._embedding_dispatch_service = EmbeddingDispatchService()
        self._ingest_progress_service = IngestProgressService()
        self._chunking_agent = ChunkingAgent()
        self._graph_candidate_agent = GraphCandidateAgent()
        self._feedback_judge_agent = FeedbackJudgeAgent()
        self._graph = self._build_graph()

    def invoke(
        self,
        *,
        job_id: str,
        document_id: str,
    ) -> IngestGraphResult:
        state = self._graph.invoke(
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

    def _build_graph(self):
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

    def _load_document(self, state: GraphIngestState) -> dict[str, object]:
        record = get_document_record(state["document_id"])
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
