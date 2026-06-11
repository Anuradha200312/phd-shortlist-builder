"""LLM provider factory — Groq primary with automatic key rotation on rate-limit.

Key rotation:
- Multiple Groq keys can be set in .env (GROQ_API_KEY, GROQ_API_KEY_2…5, or GROQ_API_KEYS=key1,key2,…)
- Multiple Ollama keys/URLs supported the same way
- When a 429/rate-limit is hit, the pool marks that key as cooled-down (65 s)
  and the next call automatically picks the next available key.
"""
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
from llm.key_rotation import init_groq_pool, init_ollama_pool, get_groq_pool, get_ollama_pool

from langchain_core.globals import set_llm_cache
from langchain_community.cache import SQLiteCache

logger = structlog.get_logger()

try:
    set_llm_cache(SQLiteCache(database_path=".langchain.db"))
except Exception as e:
    logger.warning("failed_initialize_llm_cache", error=str(e))


# ── Initialise key pools at import time ────────────────────────────────────

def _init_pools():
    settings = get_settings()
    groq_keys = settings.all_groq_keys()
    if groq_keys:
        init_groq_pool(groq_keys, cooldown_seconds=65)
    ollama_keys = settings.all_ollama_keys()
    if ollama_keys:
        init_ollama_pool(ollama_keys, cooldown_seconds=60)


_init_pools()


# ── Token usage tracker ────────────────────────────────────────────────────

class TokenBudgetCallback(BaseCallbackHandler):
    """Track Groq token usage and warn when approaching TPM budget."""

    def __init__(self, groq_budget_tpm: int = 5500):
        self.groq_tokens_this_minute = 0
        self.budget_tpm = groq_budget_tpm
        self.window_start = time.time()
        self.fallbacks_triggered = 0

    def on_llm_end(self, response, **kwargs):
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


# ── Core LLM factory ───────────────────────────────────────────────────────

def _make_groq(api_key: str, temperature: float, max_tokens: int, **kwargs) -> ChatGroq:
    return ChatGroq(
        model=get_settings().groq_model,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=api_key,
        timeout=15,
        max_retries=0,  # we handle retries via key rotation
        **kwargs,
    )


def build_llm_chain(
    temperature: float = 0.0,
    max_tokens: int = 1024,
) -> RunnableWithFallbacks:
    """Build a multi-key Groq chain with automatic key rotation on 429.

    Fallback priority:
      1. All Groq keys (round-robin from pool)
      2. Ollama cloud endpoints (if configured)
      3. Ollama local (if langchain_ollama installed)
    """
    settings = get_settings()
    groq_pool = get_groq_pool()
    ollama_pool = get_ollama_pool()

    # Primary: first available Groq key
    primary_key = groq_pool.get_key() if groq_pool else settings.groq_api_key
    primary = _make_groq(primary_key, temperature, max_tokens,
                          callbacks=[_token_tracker])

    fallbacks = []

    # Fallback: remaining Groq keys
    if groq_pool and groq_pool.size > 1:
        groq_keys = settings.all_groq_keys()
        for key in groq_keys[1:]:  # skip first (already primary)
            fallbacks.append(_make_groq(key, temperature, max_tokens))

    # Fallback: Ollama cloud endpoints
    if ChatOllama is not None:
        ollama_urls = settings.all_ollama_urls()
        ollama_keys = settings.all_ollama_keys()
        for i, url in enumerate(ollama_urls):
            key = ollama_keys[i] if i < len(ollama_keys) else (ollama_keys[0] if ollama_keys else "")
            ollama_llm = ChatOllama(
                model=settings.ollama_model,
                base_url=url,
                headers={"Authorization": f"Bearer {key}"} if key else {},
                temperature=temperature,
                timeout=120,
            )
            fallbacks.append(ollama_llm)

        # Local Ollama as final backup
        fallbacks.append(ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=temperature,
            timeout=90,
        ))

    if not fallbacks:
        # Minimal fallback if nothing else configured
        fallbacks.append(_make_groq(primary_key, temperature, max_tokens))

    return primary.with_fallbacks(
        fallbacks=fallbacks,
        exceptions_to_handle=(Exception,),
    )


def get_groq_key() -> str:
    """Get the next available Groq API key from the pool."""
    pool = get_groq_pool()
    if pool:
        return pool.get_key()
    return get_settings().groq_api_key


def mark_groq_key_limited(key: str) -> None:
    """Call this when a Groq key returns 429 so pool skips it for 65 s."""
    pool = get_groq_pool()
    if pool:
        pool.mark_rate_limited(key)


def get_ollama_llm(temperature: float = 0.0):
    """Return an Ollama LLM, or Groq fallback if Ollama is not available."""
    settings = get_settings()
    ollama_pool = get_ollama_pool()

    if ChatOllama is not None:
        urls = settings.all_ollama_urls()
        keys = settings.all_ollama_keys()
        if urls and keys:
            # Use first available (could be enhanced with pool for Ollama too)
            return ChatOllama(
                model=settings.ollama_model,
                base_url=urls[0],
                headers={"Authorization": f"Bearer {keys[0]}"},
                temperature=temperature,
                timeout=120,
            )

    # Fallback to Groq if Ollama not available
    return ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=temperature,
        api_key=get_groq_key(),
        timeout=15,
        max_retries=2,
    )


def get_token_tracker() -> TokenBudgetCallback:
    return _token_tracker
