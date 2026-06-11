"""Key rotation manager — automatically cycles through multiple API keys
when one hits a rate limit (429) or quota error.

Usage (in llm/providers.py):
    from llm.key_rotation import groq_key_pool, ollama_key_pool
    key = groq_key_pool.get_key()
    groq_key_pool.mark_rate_limited(key)   # call on 429
"""
from __future__ import annotations

import threading
import time
from typing import List, Optional
import structlog

logger = structlog.get_logger()


class KeyPool:
    """Thread-safe rotating API key pool with rate-limit awareness.

    When a key is marked as rate-limited it is put in a cooldown period
    (default 60 s) and skipped until that period expires.  If ALL keys are
    in cooldown the pool returns the least-recently-limited key and logs a
    warning.
    """

    def __init__(self, keys: List[str], cooldown_seconds: int = 65, name: str = "pool"):
        self._keys: List[str] = [k.strip() for k in keys if k.strip()]
        self._cooldown = cooldown_seconds
        self._name = name
        self._index = 0
        self._limited_until: dict[str, float] = {}   # key -> epoch when cooldown ends
        self._lock = threading.Lock()

    # ── public interface ──────────────────────────────────────────────────────

    def get_key(self) -> str:
        """Return the next available key (round-robin, skipping cooled-down keys)."""
        with self._lock:
            if not self._keys:
                raise ValueError(f"KeyPool '{self._name}' has no keys configured.")

            now = time.time()
            available = [k for k in self._keys if now >= self._limited_until.get(k, 0)]

            if not available:
                # All keys are rate-limited — pick the one whose cooldown ends soonest
                key = min(self._keys, key=lambda k: self._limited_until.get(k, 0))
                wait = max(0.0, self._limited_until[key] - now)
                logger.warning(
                    "all_keys_rate_limited",
                    pool=self._name,
                    returning_key_index=self._keys.index(key),
                    cooldown_remaining_s=round(wait, 1),
                )
                return key

            # Round-robin within available keys
            # Find the next available key starting from _index
            n = len(self._keys)
            for offset in range(n):
                candidate = self._keys[(self._index + offset) % n]
                if candidate in available:
                    self._index = (self._keys.index(candidate) + 1) % n
                    return candidate

            return available[0]

    def mark_rate_limited(self, key: str) -> None:
        """Call this when a key returns a 429/quota error."""
        with self._lock:
            self._limited_until[key] = time.time() + self._cooldown
            logger.warning(
                "key_rate_limited",
                pool=self._name,
                key_suffix=key[-6:] if len(key) > 6 else "***",
                cooldown_s=self._cooldown,
                keys_remaining=sum(
                    1 for k in self._keys
                    if time.time() >= self._limited_until.get(k, 0)
                ) - 1,
            )

    def mark_invalid(self, key: str) -> None:
        """Permanently remove an invalid / revoked key from the pool."""
        with self._lock:
            if key in self._keys:
                self._keys.remove(key)
                logger.error(
                    "key_removed_invalid",
                    pool=self._name,
                    key_suffix=key[-6:] if len(key) > 6 else "***",
                    remaining=len(self._keys),
                )

    @property
    def size(self) -> int:
        return len(self._keys)

    @property
    def available_count(self) -> int:
        now = time.time()
        with self._lock:
            return sum(1 for k in self._keys if now >= self._limited_until.get(k, 0))


# ── Singleton pools (populated by llm/providers.py from settings) ──────────

_groq_pool: Optional[KeyPool] = None
_ollama_pool: Optional[KeyPool] = None


def init_groq_pool(keys: List[str], cooldown_seconds: int = 65) -> KeyPool:
    global _groq_pool
    _groq_pool = KeyPool(keys, cooldown_seconds=cooldown_seconds, name="groq")
    logger.info("groq_key_pool_init", total_keys=len(keys))
    return _groq_pool


def init_ollama_pool(keys: List[str], cooldown_seconds: int = 60) -> KeyPool:
    global _ollama_pool
    _ollama_pool = KeyPool(keys, cooldown_seconds=cooldown_seconds, name="ollama")
    logger.info("ollama_key_pool_init", total_keys=len(keys))
    return _ollama_pool


def get_groq_pool() -> Optional[KeyPool]:
    return _groq_pool


def get_ollama_pool() -> Optional[KeyPool]:
    return _ollama_pool
