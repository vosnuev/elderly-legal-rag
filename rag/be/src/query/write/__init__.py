from __future__ import annotations

from query.write.cypher import write_query
from query.write.document_registration import register_document

__all__ = [
    "register_document",
    "write_query",
]
