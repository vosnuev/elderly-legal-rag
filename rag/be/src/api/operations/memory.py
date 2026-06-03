from __future__ import annotations

from fastapi import APIRouter

from knowledge_runtime.schemas import (
    MemoryDocumentResponse,
    MemoryDocumentUpdateRequest,
)
from knowledge_runtime.service import knowledge_runtime

router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.get("/global", response_model=MemoryDocumentResponse)
def get_global_memory() -> MemoryDocumentResponse:
    return knowledge_runtime.memory.get_global()


@router.put("/global", response_model=MemoryDocumentResponse)
def update_global_memory(
    request: MemoryDocumentUpdateRequest,
) -> MemoryDocumentResponse:
    return knowledge_runtime.memory.update_global(request)
