from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

SERVICE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=SERVICE_DIR / ".env",
        env_file_encoding="utf-8",
        env_prefix="RAG_",
        extra="ignore",
    )

    workspace_dir: Path = SERVICE_DIR / "workspace"
    input_dir: Path = SERVICE_DIR / "input"
    output_dir: Path = SERVICE_DIR / "output"
    cache_dir: Path = SERVICE_DIR / "cache"
    llm_model: str | None = None
    embedding_model: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
