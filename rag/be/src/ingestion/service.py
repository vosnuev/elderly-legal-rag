from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from ingestion.dispatcher import IngestionDispatcher
from ingestion.document_service import DocumentIngestService
from ingestion.job_store import (
    IngestJobStore,
    apply_graph_ingest_result,
    create_missing_job_response,
    failed_ingest_response,
)
from ingestion.schemas import (
    SUPPORTED_INPUT_SUFFIXES,
    CreateDocumentIngestJobRequest,
    FileIngestStatusResponse,
    IngestStage,
    IngestStageResult,
    RagDocument,
    RagIngestRequest,
    ReviewDecisionRequest,
    SearchRequest,
    SearchResponse,
    SearchResult,
    StageStatus,
)
from pipeline.schemas import IngestGraphResult
from logger import bind_logger
from query.read.runtime import (
    list_documents,
    list_pending_review_candidates,
    search_documents,
)
from settings import settings


class IngestionService:
    def __init__(
        self,
        store: IngestJobStore | None = None,
        document_service: DocumentIngestService | None = None,
        dispatcher: IngestionDispatcher | None = None,
    ) -> None:
        self._store = store or IngestJobStore()
        self._document_service = document_service or DocumentIngestService()
        self._dispatcher = dispatcher or IngestionDispatcher()
        self._logger = bind_logger(component="ingestion_service")

    def dependency_summary(self) -> dict[str, object]:
        return {
            "runtime": "Memgraph Agentic GraphRAG Backend",
            "settings": "pydantic-settings",
            "ingestion": "ingestion",
            "memgraph_uri": settings.memgraph_uri,
            "external_mcp_endpoint": (
                f"http://{settings.mcp_host}:{settings.mcp_port}{settings.external_mcp_path}"
            ),
            "supported_files": sorted(SUPPORTED_INPUT_SUFFIXES),
        }

    def ingest_backend_file(self, request: RagIngestRequest) -> FileIngestStatusResponse:
        source_path = Path(request.stored_path)
        stages = [
            IngestStageResult(
                stage=IngestStage.UPLOADED,
                status=StageStatus.SUCCESS,
                message="Received backend upload file path.",
                path=str(source_path),
            )
        ]

        if not source_path.exists() or not source_path.is_file():
            return self._store.save(
                failed_ingest_response(
                    job_id=request.job_id,
                    file_name=request.file_name,
                    stages=stages,
                    message="Backend upload file path does not exist.",
                )
            )

        suffix = source_path.suffix.lower()
        if suffix not in SUPPORTED_INPUT_SUFFIXES:
            return self._store.save(
                failed_ingest_response(
                    job_id=request.job_id,
                    file_name=request.file_name,
                    stages=stages,
                    message=f"Unsupported input suffix: {suffix or 'none'}",
                )
            )

        raw_content = source_path.read_text(encoding="utf-8")
        stages.append(
            IngestStageResult(
                stage=IngestStage.VALIDATED,
                status=StageStatus.SUCCESS,
                message="File path and suffix validation completed.",
            )
        )
        return self._create_job_from_content(
            job_id=request.job_id,
            file_name=request.file_name,
            raw_content=raw_content,
            content_type=request.content_type,
            source_path=str(source_path),
            stages=stages,
        )

    def create_text_job(
        self,
        request: CreateDocumentIngestJobRequest,
    ) -> FileIngestStatusResponse:
        return self._create_job_from_content(
            job_id=str(uuid4()),
            file_name=request.file_name,
            raw_content=request.content,
            content_type=request.content_type,
            source_path=None,
            stages=[
                IngestStageResult(
                    stage=IngestStage.UPLOADED,
                    status=StageStatus.SUCCESS,
                    message="Received text document payload.",
                )
            ],
        )

    def get_status(self, job_id: str) -> FileIngestStatusResponse:
        return self._store.get(job_id) or create_missing_job_response(job_id)

    def start_graph_add(self, job_id: str) -> FileIngestStatusResponse:
        job = self._store.get(job_id)
        if job is None:
            return create_missing_job_response(job_id)
        if not job.document_id:
            return self._store.save(
                failed_ingest_response(
                    job_id=job.job_id,
                    file_name=job.file_name,
                    stages=list(job.stages),
                    message="No document_id was stored for this ingest job.",
                )
            )

        result = self._dispatcher.start(job)
        return apply_graph_ingest_result(job, result, self._store)

    def list_documents(self) -> list[RagDocument]:
        result = list_documents(limit=settings.query_max_rows)
        return [_document_from_record(row["document"]) for row in result["rows"]]

    def search(self, request: SearchRequest) -> SearchResponse:
        result = search_documents(request.query, request.top_k)
        return SearchResponse(
            query=request.query,
            results=[
                _search_result_from_record(row["document"], score=float(row.get("score") or 1.0))
                for row in result["rows"]
            ],
        )

    def list_pending_edge_candidates(self, limit: int = 50) -> dict[str, object]:
        return list_pending_review_candidates(limit=limit)

    def decide_edge_candidate(
        self,
        *,
        candidate_id: str,
        request: ReviewDecisionRequest,
    ) -> IngestGraphResult:
        return self._dispatcher.apply_review_decision(
            candidate_id=candidate_id,
            action=request.action,
            reviewer=request.reviewer,
            note=request.note,
        )

    def _create_job_from_content(
        self,
        *,
        job_id: str,
        file_name: str,
        raw_content: str,
        content_type: str | None,
        source_path: str | None,
        stages: list[IngestStageResult],
    ) -> FileIngestStatusResponse:
        try:
            document = self._document_service.register_text_document(
                job_id=job_id,
                file_name=file_name,
                raw_content=raw_content,
                source_path=source_path,
                content_type=content_type,
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.bind(
                job_id=job_id,
                file_name=file_name,
            ).exception("document database upload failed")
            return self._store.save(
                failed_ingest_response(
                    job_id=job_id,
                    file_name=file_name,
                    stages=stages,
                    message=str(exc),
                )
            )

        stages.append(
            IngestStageResult(
                stage=IngestStage.UPLOADED_TO_DATABASE,
                status=StageStatus.SUCCESS,
                message="Stored original document in Memgraph.",
            )
        )
        response = FileIngestStatusResponse(
            job_id=job_id,
            file_name=file_name,
            current_stage=IngestStage.UPLOADED_TO_DATABASE,
            completed=False,
            stages=stages,
            document_id=document.id,
        )
        self._logger.bind(
            job_id=job_id,
            document_id=document.id,
            file_name=file_name,
        ).info("ingest job created")
        return self._store.save(response)


ingestion_service = IngestionService()


def _document_from_record(record: dict[str, object]) -> RagDocument:
    properties = _properties(record)
    return RagDocument(
        content=str(properties.get("raw_content") or ""),
        source_title=str(properties.get("file_name") or properties.get("id") or "document"),
        file_name=str(properties.get("file_name") or "document"),
        file_type=str(properties.get("source_type") or "txt"),
        location=str(properties.get("id") or ""),
        url=None,
    )


def _search_result_from_record(record: dict[str, object], score: float) -> SearchResult:
    document = _document_from_record(record)
    return SearchResult(
        content=document.content,
        source_title=document.source_title,
        file_name=document.file_name,
        file_type=document.file_type,
        location=document.location,
        url=document.url,
        score=score,
    )


def _properties(record: dict[str, object]) -> dict[str, object]:
    nested = record.get("properties")
    if isinstance(nested, dict):
        return nested
    return record
