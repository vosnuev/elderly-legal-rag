"""Process-wide structured logging for the RAG backend."""

from __future__ import annotations

import sys
from typing import Any

from loguru import logger as _logger

from settings import settings

logger = _logger


def configure_logging() -> None:
    """Configure process-wide structured logging for the RAG backend."""
    logger.remove()
    logger.configure(extra={"service": "rag-be"})
    logger.add(
        sys.stderr,
        level=settings.log_level.upper(),
        serialize=settings.log_json,
        enqueue=True,
        backtrace=False,
        diagnose=False,
        format=(
            "{time:YYYY-MM-DDTHH:mm:ss.SSSZ} | {level} | "
            "{extra[service]} | {name}:{function}:{line} | {message}"
        ),
    )


def bind_logger(**context: Any):
    return logger.bind(**context)
