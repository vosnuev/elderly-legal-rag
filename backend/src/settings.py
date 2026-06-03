from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

SERVICE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = SERVICE_DIR / "src"
REPO_ROOT = SERVICE_DIR.parent

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
    reload: bool = False
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:8501",
            "http://127.0.0.1:8501",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
    )
    langchain_project: str | None = None
    repo_root: Path = REPO_ROOT
    src_dir: Path = SRC_DIR

    openrouter_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENROUTER_API_KEY", "BACKEND_OPENROUTER_API_KEY"),
    )
    openrouter_model: str = "openai/gpt-oss-120b"
    openrouter_app_title: str = "SKN28 Backend Agent"
    openrouter_app_url: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_provider_order: list[str] = Field(default_factory=lambda: ["cerebras"])
    openrouter_allow_fallbacks: bool = True
    openrouter_require_parameters: bool = False

    llm_temperature: float = 0.2
    llm_timeout_ms: int = 60_000
    llm_max_retries: int = 2
    llm_max_tokens: int | None = Field(default=None, gt=0)
    llm_reasoning_effort: str | None = None

    rag_mcp_url: str = "http://127.0.0.1:8010/mcp"
    tool_timeout_ms: int = Field(default=30_000, gt=0)

    log_level: str = "INFO"
    log_llm_context: bool = True

# Settings 인스턴스를 캐시해서 앱 전체에서 재사용
@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
