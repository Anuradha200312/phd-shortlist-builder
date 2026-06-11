"""Application settings using Pydantic Settings v2."""
from __future__ import annotations
from functools import lru_cache
from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Groq API Keys (multiple keys rotate on rate-limit) ─────────────────
    # Primary key (backwards-compat)
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    # Additional keys: comma-separated in GROQ_API_KEYS or GROQ_API_KEY_2/3/4/5
    groq_api_keys_extra: str = Field(default="", alias="GROQ_API_KEYS")
    groq_api_key_2: str = Field(default="", alias="GROQ_API_KEY_2")
    groq_api_key_3: str = Field(default="", alias="GROQ_API_KEY_3")
    groq_api_key_4: str = Field(default="", alias="GROQ_API_KEY_4")
    groq_api_key_5: str = Field(default="", alias="GROQ_API_KEY_5")
    groq_model: str = Field(default="llama-3.3-70b-versatile", alias="GROQ_MODEL")

    # ── Ollama API Keys / URLs (multiple endpoints rotate on failure) ───────
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3.2:3b", alias="OLLAMA_MODEL")
    # Primary cloud key (backwards-compat)
    ollama_api_url: str = Field(default="", alias="OLLAMA_API_URL")
    ollama_api_key: str = Field(default="", alias="OLLAMA_API_KEY")
    # Additional Ollama keys: comma-separated in OLLAMA_API_KEYS
    ollama_api_keys_extra: str = Field(default="", alias="OLLAMA_API_KEYS")
    ollama_api_key_2: str = Field(default="", alias="OLLAMA_API_KEY_2")
    ollama_api_key_3: str = Field(default="", alias="OLLAMA_API_KEY_3")
    # Additional Ollama URLs (for different Ollama Cloud endpoints)
    ollama_api_url_2: str = Field(default="", alias="OLLAMA_API_URL_2")
    ollama_api_url_3: str = Field(default="", alias="OLLAMA_API_URL_3")

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

    # ── Derived helpers (not env vars) ─────────────────────────────────────────

    def all_groq_keys(self) -> List[str]:
        """Return all configured Groq API keys (deduplicated, non-empty)."""
        keys = []
        # Primary key
        if self.groq_api_key:
            keys.append(self.groq_api_key)
        # Comma-separated GROQ_API_KEYS
        for k in self.groq_api_keys_extra.split(","):
            if k.strip():
                keys.append(k.strip())
        # Individual numbered keys
        for k in [self.groq_api_key_2, self.groq_api_key_3,
                   self.groq_api_key_4, self.groq_api_key_5]:
            if k:
                keys.append(k)
        # Deduplicate preserving order
        seen = set()
        return [k for k in keys if k not in seen and not seen.add(k)]

    def all_ollama_keys(self) -> List[str]:
        """Return all configured Ollama API keys (deduplicated, non-empty)."""
        keys = []
        if self.ollama_api_key:
            keys.append(self.ollama_api_key)
        for k in self.ollama_api_keys_extra.split(","):
            if k.strip():
                keys.append(k.strip())
        for k in [self.ollama_api_key_2, self.ollama_api_key_3]:
            if k:
                keys.append(k)
        seen = set()
        return [k for k in keys if k not in seen and not seen.add(k)]

    def all_ollama_urls(self) -> List[str]:
        """Return all configured Ollama API URLs (deduplicated, non-empty)."""
        urls = []
        if self.ollama_api_url:
            urls.append(self.ollama_api_url)
        for u in [self.ollama_api_url_2, self.ollama_api_url_3]:
            if u:
                urls.append(u)
        seen = set()
        return [u for u in urls if u not in seen and not seen.add(u)]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
