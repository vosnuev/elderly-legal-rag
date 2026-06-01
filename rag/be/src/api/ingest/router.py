from __future__ import annotations

from fastapi import APIRouter

from api.ingest.jobs import router as jobs_router
from api.ingest.review import router as review_router

router = APIRouter()
router.include_router(jobs_router)
router.include_router(review_router)
