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

    app_title: str = "법률 RAG 프론트"
    page_title: str = "법률 RAG 프론트"
    layout: Literal["centered", "wide"] = "wide"
    initial_sidebar_state: Literal["auto", "expanded", "collapsed"] = "expanded"
    backend_base_url: AnyUrl = "http://127.0.0.1:8000"
    backend_timeout_seconds: float = 15
    chat_backend_mock: bool = True
    chat_mock_chunk_delay_seconds: float = 0.02
    log_llm_context: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
