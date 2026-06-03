"""Process-wide structured logging for the RAG backend."""

from __future__ import annotations

import json
import sys
import traceback
from typing import Any

from loguru import logger as _logger

from settings import settings

logger = _logger


def configure_logging() -> None:
    """Configure process-wide structured logging for the RAG backend."""
    logger.remove()
    logger.configure(extra={"service": "rag-be"})
    if settings.log_json:
        logger.add(
            _pretty_json_sink,
            level=settings.log_level.upper(),
            enqueue=True,
            backtrace=False,
            diagnose=False,
        )
        return

    logger.add(
        sys.stderr,
        level=settings.log_level.upper(),
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


def _pretty_json_sink(message: Any) -> None:
    sys.stderr.write(_pretty_json_record(message.record))
    sys.stderr.write("\n")
    sys.stderr.flush()


def _pretty_json_record(record: dict[str, Any]) -> str:
    extra = dict(record["extra"])
    service = extra.pop("service", "rag-be")
    payload: dict[str, Any] = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "service": service,
        "logger": record["name"],
        "location": {
            "file": record["file"].path,
            "function": record["function"],
            "line": record["line"],
        },
        "message": record["message"],
    }
    if extra:
        payload["context"] = extra
    if record["exception"]:
        payload["exception"] = _exception_payload(record["exception"])

    return json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default)


def _exception_payload(exception: Any) -> dict[str, Any]:
    exception_type = getattr(exception, "type", None)
    exception_value = getattr(exception, "value", None)
    exception_traceback = getattr(exception, "traceback", None)
    return {
        "type": getattr(exception_type, "__name__", str(exception_type)),
        "message": str(exception_value),
        "traceback": "".join(
            traceback.format_exception(
                exception_type,
                exception_value,
                exception_traceback,
            )
        ),
    }


def _json_default(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return str(value)
