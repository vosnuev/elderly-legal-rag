from enum import StrEnum

from pydantic import BaseModel, Field

# 파일 처리 단계 값 정의
class IngestStage(StrEnum):
    UPLOADED = "uploaded"
    PARSED = "parsed"
    CONVERTED = "converted"
    STORED = "stored"
    INDEXED = "indexed"
    FAILED = "failed"

# 각 처리 단계의 성공/대기/실패 대기 값 정의
class StageStatus(StrEnum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"

# 업로드 파일 타입의 지원 상태 정의
class FileTypeSupport(StrEnum):
    SUPPORTED = "supported"
    RAG_REQUIRED = "rag_required"
    PLANNED = "planned"
    UNSUPPORTED = "unsupported"

# 파일 처리 단계별 결과 표현하는 모델
class IngestStageResult(BaseModel):
    stage : IngestStage
    status : StageStatus
    message : str
    path : str | None = None
    error : str | None = None

# backend가 RAG ingest 서버에 전달할 파일 처리 요청 모델
class RagIngestRequest(BaseModel):
    job_id : str
    file_name : str
    content_type : str | None = None
    file_size : int
    stored_path : str

# 파일 업로드 직후, frontend에 반환할 응답 모델
class FileUploadResponse(BaseModel):
    job_id : str
    file_name : str
    content_type : str | None = None
    file_size : int
    current_stage : IngestStage
    completed : bool = False
    stages : list[IngestStageResult] = Field(default_factory=list)
    warning : str | None = None

# 파일 처리 상태 조회 응답 모델
class FileIngestStatusResponse(BaseModel):
    job_id : str
    file_name : str
    current_stage : IngestStage
    completed : bool
    stages : list[IngestStageResult]
    warning : str | None = None
