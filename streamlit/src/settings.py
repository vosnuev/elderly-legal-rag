from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AnyUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

SERVICE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=SERVICE_DIR / ".env",
        env_file_encoding="utf-8",
        env_prefix="STREAMLIT_",
        extra="ignore",
    )

    app_title: str = "SKN28 Streamlit Workspace"
    page_title: str = "SKN28 Streamlit"
    layout: Literal["centered", "wide"] = "wide"
    backend_base_url: AnyUrl = "http://127.0.0.1:8000"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
