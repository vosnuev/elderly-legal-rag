from __future__ import annotations

from fastapi import APIRouter

from ingestion.service import ingestion_service

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "rag-be",
    }


@router.get("/api/system/dependencies")
def dependencies() -> dict[str, object]:
    return ingestion_service.dependency_summary()
