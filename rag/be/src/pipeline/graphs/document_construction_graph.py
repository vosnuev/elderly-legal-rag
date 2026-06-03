from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from observability.consume.service import observer
from pipeline.schemas import GraphIngestPhase, IngestGraphResult
from pipeline.node_services.document_construction.embedding_dispatch_node_service import (
    EmbeddingDispatchNodeService,
)
from pipeline.state import GraphIngestState
from pipeline.sub_agents.chunking_agent import ChunkingAgent
from pipeline.sub_agents.graph_candidate_agent import GraphCandidateAgent
from query.read.inspection import get_document_record
from query.schema import DocumentNode


class DocumentConstructionGraph:
    """Document -> chunk -> embedding -> candidate -> review-pending graph."""

    def __init__(self) -> None:
        self._embedding_dispatch_node_service = EmbeddingDispatchNodeService()
        self._chunking_agent = ChunkingAgent()
        self._graph_candidate_agent = GraphCandidateAgent()
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

        # nodes
        builder = StateGraph(GraphIngestState)
        builder.add_node("document_load_node_service", self._load_document)
        builder.add_node("chunking_agent", self._run_chunking_agent)
        builder.add_node("embedding_dispatch_node_service", self._dispatch_embeddings)
        builder.add_node("graph_candidate_agent", self._run_graph_candidate_agent)

        # edges ( linear )
        builder.add_edge(START, "document_load_node_service")
        builder.add_edge("document_load_node_service", "chunking_agent")
        builder.add_edge("chunking_agent", "embedding_dispatch_node_service")
        builder.add_edge("embedding_dispatch_node_service", "graph_candidate_agent")
        builder.add_edge("graph_candidate_agent", END)
        return builder.compile()

    def _load_document(self, state: GraphIngestState) -> dict[str, object]:
        _publish_node_service_event(
            service_name="document_load_node_service",
            event="node.started",
            stage="document_constructed",
            edge="doc_to_queue",
            log="document_load_node_service started.",
            data={"document_id": state["document_id"]},
        )
        try:
            record = get_document_record(state["document_id"])
            DocumentNode.model_validate(record)
        except Exception as exc:  # noqa: BLE001
            _publish_node_service_event(
                service_name="document_load_node_service",
                event="node.failed",
                stage="document_constructed",
                edge="doc_to_queue",
                log=str(exc),
                data={"document_id": state["document_id"]},
            )
            raise
        _publish_node_service_event(
            service_name="document_load_node_service",
            event="node.finished",
            stage="document_constructed",
            edge="queue_to_chunk",
            log="document_load_node_service finished.",
            data={"document_id": state["document_id"]},
        )
        return {"phase": GraphIngestPhase.DOCUMENT_REGISTERED}

    def _run_chunking_agent(self, state: GraphIngestState) -> dict[str, object]:
        chunk_ids = self._chunking_agent.run(
            job_id=state["job_id"],
            document_id=state["document_id"],
        )
        return {"chunk_ids": chunk_ids, "phase": GraphIngestPhase.CHUNKED}

    def _dispatch_embeddings(self, state: GraphIngestState) -> dict[str, object]:
        input_chunk_ids = state.get("chunk_ids", [])
        _publish_node_service_event(
            service_name="embedding_dispatch_node_service",
            event="node.started",
            stage="embedding_dispatch",
            edge="chunk_to_embed",
            log="embedding_dispatch_node_service started.",
            data={
                "chunk_count": len(input_chunk_ids),
                "document_id": state["document_id"],
            },
        )
        try:
            chunk_ids = self._embedding_dispatch_node_service.dispatch(
                job_id=state["job_id"],
                chunk_ids=input_chunk_ids,
            )
        except Exception as exc:  # noqa: BLE001
            _publish_node_service_event(
                service_name="embedding_dispatch_node_service",
                event="node.failed",
                stage="embedding_dispatch",
                edge="chunk_to_embed",
                log=str(exc),
                data={
                    "chunk_count": len(input_chunk_ids),
                    "document_id": state["document_id"],
                },
            )
            raise
        _publish_node_service_event(
            service_name="embedding_dispatch_node_service",
            event="node.finished",
            stage="embedding_dispatch",
            edge="embed_to_candidate",
            log="embedding_dispatch_node_service finished.",
            data={
                "chunk_count": len(chunk_ids),
                "document_id": state["document_id"],
            },
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
        phase = (
            GraphIngestPhase.PENDING_REVIEW
            if edge_candidate_ids
            else GraphIngestPhase.COMPLETED
        )
        return {
            "edge_candidate_ids": edge_candidate_ids,
            "phase": phase,
        }

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


def _publish_node_service_event(
    *,
    service_name: str,
    event: str,
    stage: str,
    edge: str,
    log: str,
    data: dict[str, object] | None = None,
) -> None:
    observer.service_from_thread(
        service_name=service_name,
        stage=stage,
        edge=edge,
        log=log,
        data={"event": event, **(data or {})},
    )
