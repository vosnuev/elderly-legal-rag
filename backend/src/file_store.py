from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from settings import settings


# 파일 유효성 검사 실패 시 발생하는 예외
class FileValidationError(ValueError):
    pass


EXECUTABLE_SIGNATURES = (b"MZ", b"\x7fELF")
TEXT_EXTENSIONS = {".csv", ".json", ".txt", ".md"}


# 업로드 파일명을 경로로 쓰기 전, 위험한 문자 제거
def sanitize_file_name(file_name: str | None) -> str:
    safe_name = Path(file_name or "uploaded_file").name
    return safe_name or "uploaded_file"


# 업로드 파일 확장자를 허용 목록 기준으로 검사
def validate_file_extension(file_name: str) -> str:
    ext = Path(file_name).suffix.lower()
    allowed = [item.lower() for item in settings.upload_allowed_extensions]

    if not ext:
        raise FileValidationError("파일 확장자가 없습니다.")
    if allowed and ext not in allowed:
        raise FileValidationError(
            f"지원하지 않는 파일 형식입니다: '{ext}'. 허용 형식: {', '.join(allowed)}"
        )

    return ext


# 업로드 Content-Type이 확장자별 허용 MIME인지 검사
def validate_content_type(ext: str, content_type: str | None) -> None:
    normalized = (content_type or "").split(";", 1)[0].strip().lower()
    if not normalized:
        return

    allowed_by_ext = {
        key.lower(): [item.lower() for item in value]
        for key, value in settings.upload_allowed_mime_types.items()
    }
    allowed = allowed_by_ext.get(ext, [])
    if allowed and normalized not in allowed:
        raise FileValidationError(
            f"파일 MIME 타입이 허용되지 않습니다: '{normalized}'. "
            f"{ext} 허용 MIME: {', '.join(allowed)}"
        )


# 확장자를 속인 실행 파일이나 스크립트 업로드를 차단
def validate_file_content(ext: str, content: bytes) -> None:
    head = content[:4096]
    stripped = head.lstrip()

    if head.startswith(EXECUTABLE_SIGNATURES):
        raise FileValidationError("실행 파일은 업로드할 수 없습니다.")
    if ext in TEXT_EXTENSIONS and stripped.startswith(b"#!"):
        raise FileValidationError("스크립트 파일은 업로드할 수 없습니다.")
    if ext in TEXT_EXTENSIONS and b"\x00" in head:
        raise FileValidationError("텍스트 파일에 바이너리 데이터가 포함되어 있습니다.")


# 업로드된 파일 backend 로컬 저장소에 저장 및 RAG 처리/상태 조회에 필요한 작업 정보 반환
async def save_upload_file(file: UploadFile) -> dict[str, object]:
    file_name = sanitize_file_name(file.filename)
    ext = validate_file_extension(file_name)
    validate_content_type(ext, file.content_type)

    content = await file.read()
    validate_file_content(ext, content)

    # 파일 크기 제한 검사
    max_bytes = settings.upload_max_file_mb * 1024 * 1024
    if len(content) > max_bytes:
        size_mb = len(content) / 1024 / 1024
        raise FileValidationError(
            f"파일 크기({size_mb:.1f}MB)가 최대 허용 크기({settings.upload_max_file_mb}MB)를 초과합니다."
        )

    job_id = uuid4().hex
    job_dir = settings.upload_dir / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    save_path = job_dir / file_name
    save_path.write_bytes(content)

    return {
        "job_id": job_id,
        "file_name": file_name,
        "content_type": file.content_type,
        "file_size": len(content),
        "stored_path": str(save_path),
    }
