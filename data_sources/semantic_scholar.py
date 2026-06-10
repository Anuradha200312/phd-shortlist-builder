"""Semantic Scholar API client."""
from __future__ import annotations
from typing import Optional
import structlog
from data_sources.base import BaseDataSource

logger = structlog.get_logger()


class SemanticScholarClient(BaseDataSource):
    """Client for the Semantic Scholar Academic Graph API."""

    BASE_URL = "https://api.semanticscholar.org/graph/v1"
    SOURCE_NAME = "semantic_scholar"

    async def search_authors(self, query: str, limit: int = 20) -> list[dict]:
        """Search for authors by research topic."""
        data = await self._get("author/search", params={"query": query, "limit": limit})
        return data.get("data", [])

    async def get_author(self, author_id: str, fields: Optional[list[str]] = None) -> dict:
        """Get detailed author info including papers."""
        default_fields = [
            "name", "affiliations", "homepage", "paperCount", "citationCount",
            "hIndex", "papers.title", "papers.year", "papers.venue",
            "papers.citationCount", "papers.externalIds",
        ]
        params = {"fields": ",".join(fields or default_fields)}
        return await self._get(f"author/{author_id}", params=params)

    async def search_papers(self, query: str, limit: int = 20) -> list[dict]:
        """Search papers by keyword."""
        data = await self._get("paper/search", params={
            "query": query,
            "limit": limit,
            "fields": "title,year,venue,authors,abstract,citationCount,externalIds",
        })
        return data.get("data", [])
