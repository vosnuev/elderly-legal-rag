from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

SERVICE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = SERVICE_DIR / "src"
REPO_ROOT = SERVICE_DIR.parent
RAG_DIR = REPO_ROOT / "rag"


# backend 환경 변수와 기본 설정을 담는 설정 클래스
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=SERVICE_DIR / ".env",
        env_file_encoding="utf-8",
        env_prefix="BACKEND_",
        extra="ignore",
    )

    service_name: str = "SKN28 Backend"
    service_version: str = "0.1.0"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    reload: bool = True
    cors_origins: list[str] = Field(default_factory=list)
    langchain_project: str | None = None
    repo_root: Path = REPO_ROOT
    src_dir: Path = SRC_DIR
    workspace_dir: Path = RAG_DIR / "workspace"
    input_dir: Path = RAG_DIR / "input"
    output_dir: Path = RAG_DIR / "output"
    cache_dir: Path = RAG_DIR / "cache"
    upload_dir: Path = SERVICE_DIR / "storage" / "uploads"

    openrouter_api_key: SecretStr | None = None
    openrouter_model: str = "openai/gpt-oss-120b"
    openrouter_app_title: str = "SKN28 Backend Agent"
    openrouter_app_url: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    llm_temperature: float = 0.2
    llm_timeout_ms: int = 60_000
    llm_max_retries: int = 2
    llm_reasoning_effort: str = "medium"

    agent_clarification_option_count: int = Field(default=3, ge=3, le=3)
    agent_custom_input_enabled: bool = True
    agent_demo_mode: bool = True

    rag_ingest_url: str = "http://127.0.0.1:8010/ingest"
    rag_ingest_status_url: str = "http://127.0.0.1:8010/ingest/status"
    rag_ingest_timeout_ms: int = Field(default=10_000, gt=0)
    rag_search_url: str = "http://127.0.0.1:8010/search"
    rag_search_top_k: int = Field(default=5, ge=1, le=20)
    rag_search_timeout_ms: int = Field(default=10_000, gt=0)

    log_level: str = "INFO"
    log_llm_context: bool = True


# Settings 인스턴스를 캐시해서 앱 전체에서 재사용
@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
