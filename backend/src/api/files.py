from fastapi import APIRouter, File, UploadFile

from file_store import save_upload_file
from rag_ingest_client import (
    RagIngestClientError,
    get_rag_ingest_status,
    request_rag_ingest,
)
from schemas.files import (
    FileIngestStatusResponse,
    FileUploadResponse,
    IngestStage,
    IngestStageResult,
    RagIngestRequest,
    StageStatus,
)

router = APIRouter(prefix="/api/files", tags=["files"])

# 사용자가 업로드한 파일 저장 및 RAG ingest 서버에 처리 요청
@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)) -> FileUploadResponse:
    saved = await save_upload_file(file)

    stages = [
        IngestStageResult(
            stage=IngestStage.UPLOADED,
            status=StageStatus.SUCCESS,
            message="파일 업로드가 완료되었습니다.",
            path=str(saved["stored_path"]),
        )
    ]

    payload = RagIngestRequest(**saved)

    try:
        request_rag_ingest(payload)
        stages.append(
            IngestStageResult(
                stage=IngestStage.PARSED,
                status=StageStatus.PENDING,
                message="RAG 서버에 파싱/변환/적재/인덱싱 작업을 요청했습니다.",
            )
        )
        current_stage = IngestStage.UPLOADED
        warning = None
    except RagIngestClientError as exc:
        stages.append(
            IngestStageResult(
                stage=IngestStage.FAILED,
                status=StageStatus.FAILED,
                message="RAG 서버 작업 요청에 실패했습니다.",
                error=str(exc),
            )
        )
        current_stage = IngestStage.FAILED
        warning = str(exc)

    return FileUploadResponse(
        job_id=str(saved["job_id"]),
        file_name=str(saved["file_name"]),
        content_type=saved["content_type"],
        file_size=int(saved["file_size"]),
        current_stage=current_stage,
        completed=False,
        stages=stages,
        warning=warning,
    )


# RAG ingest 서버에서 업로드 파일 처리 상태 조회
@router.get("/{job_id}/status", response_model=FileIngestStatusResponse)
def get_file_status(job_id: str) -> FileIngestStatusResponse:
    try:
        return get_rag_ingest_status(job_id)
    except RagIngestClientError as exc:
        return FileIngestStatusResponse(
            job_id=job_id,
            file_name="unknown",
            current_stage=IngestStage.FAILED,
            completed=False,
            stages=[
                IngestStageResult(
                    stage=IngestStage.FAILED,
                    status=StageStatus.FAILED,
                    message="RAG 서버 상태 조회에 실패했습니다.",
                    error=str(exc),
                )
            ],
            warning=str(exc),
        )
