from __future__ import annotations

from fastapi import APIRouter

from api.operations.documents import router as documents_router
from api.operations.health import router as health_router
from api.operations.search import router as search_router

router = APIRouter()
router.include_router(health_router)
router.include_router(documents_router)
router.include_router(search_router)
