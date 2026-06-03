from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from itertools import count
from pathlib import Path
from uuid import uuid4

from ingestion.schemas import SUPPORTED_INPUT_SUFFIXES
from logger import bind_logger
from query.read.inspection import get_document_record
from query.schema import DocumentNode
from query.write import register_document

_ENTRY_COUNTER = count(1)


class DocumentIngestService:
    def __init__(self) -> None:
        self._logger = bind_logger(component="document_ingest_service")

    def register_text_document(
        self,
        *,
        job_id: str,
        file_name: str,
        raw_content: str,
        source_path: str | None = None,
        content_type: str | None = None,
    ) -> DocumentNode:
        suffix = _suffix_from_file_name(file_name)
        if suffix not in SUPPORTED_INPUT_SUFFIXES:
            raise ValueError(f"Unsupported input suffix: {suffix}")

        normalized = _normalize_for_hash(raw_content)
        document = DocumentNode(
            id=str(uuid4()),
            entry_number=next(_ENTRY_COUNTER),
            document_version=1,
            content_hash=sha256(normalized.encode("utf-8")).hexdigest(),
            raw_content=raw_content,
            file_name=file_name,
            source_type=content_type or suffix.lstrip("."),
            source_path=source_path,
            metadata={
                "registered_at": datetime.now(UTC).isoformat(),
                "last_ingest_job_id": job_id,
            },
        )
        register_document(document.model_dump())
        self._logger.bind(
            job_id=job_id,
            document_id=document.id,
            file_name=file_name,
        ).info("document registered")
        return document

    def get_registered_document(self, document_id: str) -> DocumentNode:
        record = get_document_record(document_id)
        return DocumentNode.model_validate(record)


def _normalize_for_hash(raw_content: str) -> str:
    return raw_content.replace("\r\n", "\n").replace("\r", "\n").strip()


def _suffix_from_file_name(file_name: str) -> str:
    suffix = Path(file_name).suffix.lower() or ".txt"
    return suffix
