from __future__ import annotations

import logging
import sys

from settings import settings

def configure_logging() -> None:
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        stream=sys.stdout,
        force=True,
    )

def get_logger(name:str) -> logging.Logger:
    return logging.getLogger(name)
