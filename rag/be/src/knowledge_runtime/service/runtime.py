"""Composition root for knowledge runtime services."""

from __future__ import annotations

from knowledge_runtime.documents.catalog import DocumentCatalog
from knowledge_runtime.documents.registry import DocumentRegistry
from knowledge_runtime.jobs.projector import JobProjector
from knowledge_runtime.jobs.progress import JobProgressModifier
from knowledge_runtime.jobs.store import JobStore
from knowledge_runtime.service.catalog import CatalogService
from knowledge_runtime.service.documents import DocumentWorkService
from knowledge_runtime.service.memory import MemoryService
from knowledge_runtime.service.reviews import ReviewWorkService
from knowledge_runtime.service.status import StatusService
from knowledge_runtime.service.system import SystemService
from knowledge_runtime.tasks.store import TaskStore
from knowledge_runtime.tasks.submitter import TaskSubmitter
from knowledge_runtime.workers.pool import WorkerPool
from knowledge_runtime.workers.runner import PipelineRunner
from observability.consume.service import observer
from settings import settings


class KnowledgeRuntime:
    def __init__(
        self,
        *,
        documents: DocumentWorkService,
        catalog: CatalogService,
        reviews: ReviewWorkService,
        memory: MemoryService,
        status: StatusService,
        system: SystemService,
        worker_pool: WorkerPool,
    ) -> None:
        self.documents = documents
        self.catalog = catalog
        self.reviews = reviews
        self.memory = memory
        self.status = status
        self.system = system
        self._worker_pool = worker_pool

    @classmethod
    def create_default(cls) -> "KnowledgeRuntime":
        job_store = JobStore()
        task_store = TaskStore()
        progress_modifier = JobProgressModifier(job_store=job_store)
        projector = JobProjector(job_store=job_store, task_store=task_store)
        worker_pool = WorkerPool(
            task_store=task_store,
            progress_modifier=progress_modifier,
            observer=observer,
            runner=PipelineRunner(),
            build_worker_count=settings.knowledge_build_worker_count,
            review_worker_count=settings.knowledge_review_worker_count,
            queue_max_size=settings.knowledge_task_queue_max_size,
        )
        submitter = TaskSubmitter(
            task_store=task_store,
            worker_pool=worker_pool,
            observer=observer,
        )
        registry = DocumentRegistry()
        return cls(
            documents=DocumentWorkService(
                registry=registry,
                job_store=job_store,
                submitter=submitter,
                projector=projector,
            ),
            catalog=CatalogService(catalog=DocumentCatalog()),
            reviews=ReviewWorkService(
                submitter=submitter,
                projector=projector,
            ),
            memory=MemoryService(),
            status=StatusService(
                projector=projector,
                observer=observer,
            ),
            system=SystemService(),
            worker_pool=worker_pool,
        )

    async def start_workers(self) -> None:
        await self._worker_pool.start()

    async def stop_workers(self) -> None:
        await self._worker_pool.stop()


knowledge_runtime = KnowledgeRuntime.create_default()
