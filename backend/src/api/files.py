import asyncio
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from file_store import FileValidationError, save_upload_file
from rate_limiter import enforce_rate_limit
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
async def upload_file(request: Request, file: UploadFile = File(...)) -> FileUploadResponse:
    enforce_rate_limit(request, "file_upload")

    try:
        saved = await save_upload_file(file)
    except FileValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

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
        # urlopen은 블로킹 I/O이므로 스레드 풀에서 실행
        await asyncio.to_thread(request_rag_ingest, payload)
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


# backend가 발급한 job_id 형식인지 확인
def _validate_job_id(job_id: str) -> None:
    try:
        parsed = UUID(hex=job_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="job_id 형식이 올바르지 않습니다.") from exc

    if parsed.hex != job_id:
        raise HTTPException(status_code=400, detail="job_id 형식이 올바르지 않습니다.")


# RAG ingest 서버에서 업로드 파일 처리 상태 조회
@router.get("/{job_id}/status", response_model=FileIngestStatusResponse)
def get_file_status(job_id: str) -> FileIngestStatusResponse:
    _validate_job_id(job_id)

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
