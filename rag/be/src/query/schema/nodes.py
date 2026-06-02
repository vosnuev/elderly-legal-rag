from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DocumentNode(BaseModel):
    """원본 입력 문서 노드.

    사용자가 업로드한 text/json/md 등의 원문을 그대로 보관한다. graph construction은
    이 노드의 `id`를 시작점으로 chunk 생성과 relationship candidate 생성을 진행한다.
    """

    id: str | None = None
    entry_number: int
    document_version: int = 1
    content_hash: str
    raw_content: str
    file_name: str
    source_type: str
    source_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChunkNode(BaseModel):
    """원본 문서에서 agent가 생성한 semantic chunk 노드.

    `Document -[:HAS_CHUNK]-> Chunk` 형태로 연결된다. chunk text는 원문에서 복사된
    텍스트여야 하며, start/end unique string은 원문 위치를 다시 찾기 위한 marker이다.
    embedding vector와 model 정보는 이 노드에 저장한다.
    """

    id: str | None = None
    document_id: str
    chunk_index: int
    text: str
    tags: list[str] = Field(default_factory=list)
    summary: str = ""
    reason: str = ""
    start_unique_string: str
    end_unique_string: str
    start_char: int | None = None
    end_char: int | None = None
    embedding_status: str = "pending"
    embedding_model: str | None = None
    embedding: list[float] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
