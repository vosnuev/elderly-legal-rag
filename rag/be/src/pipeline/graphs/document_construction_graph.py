from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from pipeline.schemas import GraphIngestPhase, IngestGraphResult
from pipeline.services.embedding_dispatch_service import EmbeddingDispatchService
from pipeline.services.ingest_progress_service import IngestProgressService
from pipeline.state import GraphIngestState
from pipeline.sub_agents.chunking_agent import ChunkingAgent
from pipeline.sub_agents.feedback_judge_agent import FeedbackJudgeAgent
from pipeline.sub_agents.graph_candidate_agent import GraphCandidateAgent
from query.read.inspection import get_document_record
from query.schema import DocumentNode


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
        builder.add_edge("feedback_judge_agent", "ingest_progress_service")
        builder.add_edge("ingest_progress_service", END)
        return builder.compile()

    def _load_document(self, state: GraphIngestState) -> dict[str, object]:
        record = get_document_record(state["document_id"])
        DocumentNode.model_validate(record)
        return {"phase": GraphIngestPhase.DOCUMENT_REGISTERED}

    def _run_chunking_agent(self, state: GraphIngestState) -> dict[str, object]:
        chunk_ids = self._chunking_agent.run(
            job_id=state["job_id"],
            document_id=state["document_id"],
        )
        return {"chunk_ids": chunk_ids, "phase": GraphIngestPhase.CHUNKED}

    def _dispatch_embeddings(self, state: GraphIngestState) -> dict[str, object]:
        chunk_ids = self._embedding_dispatch_service.dispatch(
            job_id=state["job_id"],
            chunk_ids=state.get("chunk_ids", []),
        )
        return {
            "chunk_ids": chunk_ids,
            "phase": GraphIngestPhase.EMBEDDING_DISPATCHED,
        }

    def _run_graph_candidate_agent(self, state: GraphIngestState) -> dict[str, object]:
        edge_candidate_ids = self._graph_candidate_agent.run(
            job_id=state["job_id"],
            document_id=state["document_id"],
            chunk_ids=state.get("chunk_ids", []),
        )
        return {
            "edge_candidate_ids": edge_candidate_ids,
            "phase": GraphIngestPhase.CANDIDATES_GENERATED,
        }

    def _run_feedback_judge_agent(self, state: GraphIngestState) -> dict[str, object]:
        feedback = self._feedback_judge_agent.run(
            job_id=state["job_id"],
            document_id=state["document_id"],
            chunk_ids=state.get("chunk_ids", []),
            edge_candidate_ids=state.get("edge_candidate_ids", []),
        )
        if feedback.incomplete:
            phase = GraphIngestPhase.NEEDS_RETRY
        elif not feedback.ready_for_review:
            phase = GraphIngestPhase.NEEDS_RETRY
        else:
            phase = (
                GraphIngestPhase.PENDING_REVIEW
                if state.get("edge_candidate_ids")
                else GraphIngestPhase.COMPLETED
            )
        return {"phase": phase}

    def _mark_ingest_progress(self, state: GraphIngestState) -> dict[str, object]:
        phase = state.get("phase", GraphIngestPhase.COMPLETED)
        result = self._ingest_progress_service.mark(
            job_id=state["job_id"],
            phase=phase,
            document_id=state["document_id"],
            chunk_count=len(state.get("chunk_ids", [])),
            candidate_count=len(state.get("edge_candidate_ids", [])),
            warnings=[],
            errors=[],
        )
        return {"phase": result.phase}

    def _state_to_result(self, state: GraphIngestState) -> IngestGraphResult:
        return IngestGraphResult(
            job_id=state["job_id"],
            phase=state.get("phase", GraphIngestPhase.COMPLETED),
            document_id=state["document_id"],
            chunk_count=len(state.get("chunk_ids", [])),
            candidate_count=len(state.get("edge_candidate_ids", [])),
            pending_review_count=(
                len(state.get("edge_candidate_ids", []))
                if state.get("phase") is GraphIngestPhase.PENDING_REVIEW
                else 0
            ),
            warnings=[],
            errors=[],
        )
