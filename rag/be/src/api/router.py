from __future__ import annotations

from fastapi import APIRouter

from api.ingest import router as ingest_router
from api.operations import router as operations_router

api_router = APIRouter()
api_router.include_router(ingest_router)
api_router.include_router(operations_router)
