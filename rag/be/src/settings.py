from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
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
    embedding_model: str = "openai/text-embedding-3-large"
    embedding_dimensions: int = 3072
    embedding_worker_count: int = Field(default=5, ge=1)

    memgraph_uri: str = "bolt://127.0.0.1:7687"
    memgraph_username: str | None = None
    memgraph_password: SecretStr | None = None

    redis_url: str = "redis://127.0.0.1:6379/0"
    observability_enabled: bool = True
    observability_stream_prefix: str = "rag:observability:jobs"
    observability_stream_maxlen: int = Field(default=2_000, ge=100)
    observability_xread_block_ms: int = Field(default=15_000, ge=100)

    openrouter_api_key: SecretStr | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    graph_llm_model: str | None = None

    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8010
    external_mcp_path: str = "/mcp"
    cors_allowed_origins: list[str] = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]
    query_timeout_ms: int = Field(default=30_000, gt=0)
    query_max_rows: int = Field(default=100, gt=0)
    text_search_index_name: str = "rag_text_idx"
    document_text_search_index_name: str = "rag_document_text_idx"
    review_note_text_search_index_name: str = "rag_review_note_text_idx"
    graph_candidate_tool_budget: int = Field(default=80, ge=1)
    log_level: str = "INFO"
    log_json: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
