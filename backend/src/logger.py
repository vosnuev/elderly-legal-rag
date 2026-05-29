from __future__ import annotations

import logging
import sys

from settings import settings

# 앱 전체 logging 형식과 레벨 설정
def configure_logging() -> None:
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        stream=sys.stdout,
        force=True,
    )

# 이름별 logger 인스턴스 반환
def get_logger(name:str) -> logging.Logger:
    return logging.getLogger(name)
