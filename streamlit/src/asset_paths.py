from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path


APP_ICON_PATH = Path(__file__).resolve().parent / "assets" / "new_dog_icon.png"


@lru_cache(maxsize=1)
def app_icon_data_uri() -> str:
    encoded = base64.b64encode(APP_ICON_PATH.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
