"""diskcache wrapper — L2 cache for API responses."""
from __future__ import annotations
from pathlib import Path
from typing import Optional

import diskcache
import structlog

logger = structlog.get_logger()


def get_disk_cache(cache_dir: str = "./cache") -> diskcache.Cache:
    """Return a diskcache.Cache instance."""
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    return diskcache.Cache(cache_dir, size_limit=500 * 1024 * 1024)  # 500 MB


class CacheWrapper:
    """Thin wrapper over diskcache.Cache with logging."""

    def __init__(self, cache_dir: str = "./cache"):
        self._cache = get_disk_cache(cache_dir)

    def get(self, key: str) -> Optional[dict]:
        result = self._cache.get(key)
        if result is not None:
            logger.debug("diskcache_hit", key=key[:20])
        return result

    def set(self, key: str, value: dict, expire: int = 86400):
        self._cache.set(key, value, expire=expire)

    def clear(self):
        self._cache.clear()

    @property
    def stats(self) -> dict:
        return {"size": len(self._cache), "volume": self._cache.volume()}
