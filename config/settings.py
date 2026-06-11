"""Application settings using Pydantic Settings v2."""
from __future__ import annotations
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM Providers ──────────────────────────────────────────────────────────
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.3-70b-versatile", alias="GROQ_MODEL")

    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3.2:3b", alias="OLLAMA_MODEL")
    ollama_api_url: str = Field(default="", alias="OLLAMA_API_URL")
    ollama_api_key: str = Field(default="", alias="OLLAMA_API_KEY")

    # ── LangSmith ──────────────────────────────────────────────────────────────
    langchain_tracing_v2: str = Field(default="false", alias="LANGCHAIN_TRACING_V2")
    langchain_api_key: str = Field(default="", alias="LANGCHAIN_API_KEY")
    langchain_project: str = Field(default="phd-shortlist-builder", alias="LANGCHAIN_PROJECT")

    # ── Database ───────────────────────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://phd_user:phd_pass@localhost:5432/phd_shortlist",
        alias="DATABASE_URL",
    )
    database_url_sync: str = Field(
        default="postgresql://phd_user:phd_pass@localhost:5432/phd_shortlist",
        alias="DATABASE_URL_SYNC",
    )

    # ── App ────────────────────────────────────────────────────────────────────
    app_env: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    api_key: str = Field(default="dev-secret", alias="API_KEY")

    # ── Pipeline ───────────────────────────────────────────────────────────────
    min_candidates_required: int = Field(default=50, alias="MIN_CANDIDATES_REQUIRED")
    max_candidates_to_enrich: int = Field(default=120, alias="MAX_CANDIDATES_TO_ENRICH")
    max_retrieval_attempts: int = Field(default=3, alias="MAX_RETRIEVAL_ATTEMPTS")
    why_match_concurrency: int = Field(default=10, alias="WHY_MATCH_CONCURRENCY")
    cache_dir: str = Field(default="./cache", alias="CACHE_DIR")
    output_dir: str = Field(default="./sample_output", alias="OUTPUT_DIR")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
