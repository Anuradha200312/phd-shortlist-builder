"""Base data source client — shared HTTP logic with retry + caching."""
from __future__ import annotations
import hashlib
import json
from typing import Optional

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = structlog.get_logger()


class BaseDataSource:
    """Base class for all API data source clients."""

    BASE_URL: str = ""
    SOURCE_NAME: str = "base"

    def __init__(self, cache=None, timeout: int = 15):
        self.cache = cache
        self.timeout = timeout

    def _cache_key(self, endpoint: str, params: dict) -> str:
        """Generate a stable cache key from endpoint + params."""
        raw = f"{self.SOURCE_NAME}:{endpoint}:{json.dumps(params, sort_keys=True)}"
        return hashlib.md5(raw.encode()).hexdigest()

    def _get_cached(self, key: str) -> Optional[dict]:
        if self.cache:
            return self.cache.get(key)
        return None

    def _set_cached(self, key: str, data: dict, ttl: int = 86400):
        if self.cache:
            self.cache.set(key, data, expire=ttl)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError)),
    )
    async def _get(self, endpoint: str, params: dict = None) -> dict:
        """Make a GET request with retry and optional caching."""
        params = params or {}
        cache_key = self._cache_key(endpoint, params)

        # Check cache
        cached = self._get_cached(cache_key)
        if cached is not None:
            logger.debug("cache_hit", source=self.SOURCE_NAME, endpoint=endpoint)
            return cached

        url = f"{self.BASE_URL}/{endpoint}" if not endpoint.startswith("http") else endpoint
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        self._set_cached(cache_key, data)
        logger.debug("api_call", source=self.SOURCE_NAME, endpoint=endpoint, status=resp.status_code)
        return data
