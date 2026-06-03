"""Original document registration boundary.

This module validates document inputs, creates the stored document record, and
returns the generated document identity used by background work.
"""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from itertools import count
from pathlib import Path

from observability.logger import bind_logger
from knowledge_runtime.schemas import RegisteredDocument, SUPPORTED_DOCUMENT_SUFFIXES
from query.read.inspection import get_document_record
from query.schema import DocumentNode
from query.write import register_document

_ENTRY_COUNTER = count(1)


class DocumentRegistry:
    def __init__(self) -> None:
        self._logger = bind_logger(component="knowledge_document_registry")

    def register_text(
        self,
        *,
        job_id: str,
        file_name: str,
        raw_content: str,
        source_path: str | None = None,
        content_type: str | None = None,
    ) -> RegisteredDocument:
        suffix = _suffix_from_file_name(file_name)
        if suffix not in SUPPORTED_DOCUMENT_SUFFIXES:
            raise ValueError(f"Unsupported input suffix: {suffix}")

        normalized = _normalize_for_hash(raw_content)
        content_hash = sha256(normalized.encode("utf-8")).hexdigest()
        document = DocumentNode(
            entry_number=next(_ENTRY_COUNTER),
            document_version=1,
            content_hash=content_hash,
            raw_content=raw_content,
            file_name=file_name,
            source_type=content_type or suffix.lstrip("."),
            source_path=source_path,
            metadata={
                "registered_at": datetime.now(UTC).isoformat(),
                "last_ingest_job_id": job_id,
            },
        )
        result = register_document(document.model_dump(exclude_none=True))
        document_id = str(result["rows"][0]["document_id"])
        self._logger.bind(
            job_id=job_id,
            document_id=document_id,
            file_name=file_name,
        ).info("document registered")
        return RegisteredDocument(
            document_id=document_id,
            file_name=file_name,
            content_type=document.source_type,
            content_hash=content_hash,
        )

    def get_document(self, document_id: str) -> DocumentNode:
        return DocumentNode.model_validate(get_document_record(document_id))


def _normalize_for_hash(raw_content: str) -> str:
    return raw_content.replace("\r\n", "\n").replace("\r", "\n").strip()


def _suffix_from_file_name(file_name: str) -> str:
    return Path(file_name).suffix.lower() or ".txt"
