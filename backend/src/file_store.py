from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from settings import settings


# 업로드 파일명을 경로로 쓰기 전, 위험한 문자 제거
def sanitize_file_name(file_name: str | None) -> str:
    safe_name = Path(file_name or "uploaded_file").name
    return safe_name or "uploaded_file"


# 업로드된 파일 backend 로컬 저장소에 저장 및 RAG 처리/상태 조회에 필요한 작업 정보 반환
async def save_upload_file(file: UploadFile) -> dict[str, object]:
    job_id = uuid4().hex
    job_dir = settings.upload_dir / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    file_name = sanitize_file_name(file.filename)
    save_path = job_dir / file_name

    content = await file.read()
    save_path.write_bytes(content)

    return {
        "job_id": job_id,
        "file_name": file_name,
        "content_type": file.content_type,
        "file_size": len(content),
        "stored_path": str(save_path),
    }
