"""System and dependency projection service."""

from __future__ import annotations

from knowledge_runtime.schemas import (
    RuntimeDependencySummary,
    SUPPORTED_DOCUMENT_SUFFIXES,
)
from settings import settings


class SystemService:
    def dependency_summary(self) -> RuntimeDependencySummary:
        return RuntimeDependencySummary(
            runtime="Knowledge runtime",
            settings="pydantic-settings",
            database_uri=settings.memgraph_uri,
            external_mcp_endpoint=(
                f"http://{settings.mcp_host}:{settings.mcp_port}"
                f"{settings.external_mcp_path}"
            ),
            supported_files=sorted(SUPPORTED_DOCUMENT_SUFFIXES),
            worker={
                "build_worker_count": settings.knowledge_build_worker_count,
                "review_worker_count": settings.knowledge_review_worker_count,
                "queue_max_size": settings.knowledge_task_queue_max_size,
            },
        )
