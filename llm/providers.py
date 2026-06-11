"""LLM provider factory — Groq primary with Ollama fallback via LangChain .with_fallbacks()"""
from __future__ import annotations
import time
import structlog
from langchain_groq import ChatGroq
try:
    from langchain_ollama import ChatOllama
except ImportError:
    ChatOllama = None  # type: ignore[assignment,misc]
from langchain_core.runnables import RunnableWithFallbacks
from langchain_core.callbacks import BaseCallbackHandler
from config.settings import get_settings

from langchain_core.globals import set_llm_cache
from langchain_community.cache import SQLiteCache

logger = structlog.get_logger()

try:
    set_llm_cache(SQLiteCache(database_path=".langchain.db"))
except Exception as e:
    logger.warning("failed_initialize_llm_cache", error=str(e))



class TokenBudgetCallback(BaseCallbackHandler):
    """Track Groq token usage and warn when approaching TPM budget."""

    def __init__(self, groq_budget_tpm: int = 5500):
        self.groq_tokens_this_minute = 0
        self.budget_tpm = groq_budget_tpm
        self.window_start = time.time()
        self.fallbacks_triggered = 0

    def on_llm_end(self, response, **kwargs):
        # Reset window every 60s
        if time.time() - self.window_start > 60:
            self.groq_tokens_this_minute = 0
            self.window_start = time.time()

        usage = response.llm_output.get("token_usage", {}) if response.llm_output else {}
        tokens = usage.get("total_tokens", 0)
        self.groq_tokens_this_minute += tokens

        if self.groq_tokens_this_minute > self.budget_tpm * 0.90:
            logger.warning(
                "groq_tpm_near_limit",
                used=self.groq_tokens_this_minute,
                budget=self.budget_tpm,
            )


_token_tracker = TokenBudgetCallback()


def build_llm_chain(
    temperature: float = 0.0,
    max_tokens: int = 1024,
) -> RunnableWithFallbacks:
    """
    Build a Groq → Ollama fallback chain.

    Usage:
        chain = build_llm_chain() | output_parser
        result = await chain.ainvoke({"key": "value"})

    LangChain automatically falls back to Ollama on:
      - RateLimitError (429)
      - ServiceUnavailableError (503)
      - Timeout / ConnectError
    """
    settings = get_settings()

    groq_llm = ChatGroq(
        model=settings.groq_model,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=settings.groq_api_key,
        timeout=15,
        max_retries=2,
        callbacks=[_token_tracker],
    )

    groq_fallback_llm = ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=settings.groq_api_key,
        timeout=15,
        max_retries=2,
    )

    mixtral_fallback_llm = ChatGroq(
        model="mixtral-8x7b-32768",
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=settings.groq_api_key,
        timeout=15,
        max_retries=2,
    )

    fallbacks = [groq_fallback_llm, mixtral_fallback_llm]

    # Add Ollama Cloud Fallback if credentials are provided
    if ChatOllama is not None and settings.ollama_api_url and settings.ollama_api_key:
        ollama_cloud_llm = ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_api_url,
            headers={"Authorization": f"Bearer {settings.ollama_api_key}"},
            temperature=temperature,
            timeout=120,
        )
        fallbacks.append(ollama_cloud_llm)

    # Add Local Ollama Fallback as a final backup (only if library is available)
    if ChatOllama is not None:
        ollama_local_llm = ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=temperature,
            timeout=90,
        )
        fallbacks.append(ollama_local_llm)

    return groq_llm.with_fallbacks(
        fallbacks=fallbacks,
        exceptions_to_handle=(Exception,),
    )


def get_ollama_llm(temperature: float = 0.0):
    """Return the cloud-based Ollama model if configured, otherwise fallback to Groq."""
    settings = get_settings()
    if ChatOllama is not None and settings.ollama_api_url and settings.ollama_api_key:
        return ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_api_url,
            headers={"Authorization": f"Bearer {settings.ollama_api_key}"},
            temperature=temperature,
            timeout=120,
        )
    # Fallback to cloud Groq llama-3.1-8b-instant if Ollama is not configured
    return ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=temperature,
        api_key=settings.groq_api_key,
        timeout=15,
        max_retries=2,
    )


def get_token_tracker() -> TokenBudgetCallback:
    return _token_tracker
