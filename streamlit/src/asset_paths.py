from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path


ROBOT_ICON_PATH = Path(__file__).resolve().parent / "assets" / "old_robot.png"


@lru_cache(maxsize=1)
def robot_icon_data_uri() -> str:
    encoded = base64.b64encode(ROBOT_ICON_PATH.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
