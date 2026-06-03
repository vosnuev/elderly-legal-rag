from __future__ import annotations

from fastapi import APIRouter

from knowledge_runtime.service import knowledge_runtime

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "rag-be",
    }


@router.get("/api/system/dependencies")
def dependencies() -> dict[str, object]:
    return knowledge_runtime.system.dependency_summary().model_dump()
