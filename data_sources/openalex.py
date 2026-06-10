"""OpenAlex API client — uses OpenAlex ID as master supervisor identifier."""
from __future__ import annotations
from typing import Optional
import structlog
from data_sources.base import BaseDataSource

logger = structlog.get_logger()


class OpenAlexClient(BaseDataSource):
    """Client for the OpenAlex API (free, no auth required)."""

    BASE_URL = "https://api.openalex.org"
    SOURCE_NAME = "openalex"

    async def search_authors(
        self, query: str, country: Optional[str] = None, limit: int = 25
    ) -> list[dict]:
        """Search for researchers by topic or name."""
        params = {
            "search": query,
            "per_page": limit,
            "select": "id,display_name,orcid,last_known_institutions,works_count,cited_by_count,summary_stats,topics",
        }
        if country:
            params["filter"] = f"last_known_institutions.country_code:{country}"

        data = await self._get("authors", params=params)
        return data.get("results", [])

    async def get_author(self, openalex_id: str) -> dict:
        """Get detailed author info by OpenAlex ID."""
        return await self._get(f"authors/{openalex_id}")

    async def get_author_works(self, openalex_id: str, limit: int = 20) -> list[dict]:
        """Get recent works by an author."""
        params = {
            "filter": f"author.id:{openalex_id}",
            "sort": "publication_date:desc",
            "per_page": limit,
            "select": "id,title,publication_year,primary_location,authorships,cited_by_count,doi",
        }
        data = await self._get("works", params=params)
        return data.get("results", [])

    async def search_works(self, query: str, limit: int = 20) -> list[dict]:
        """Search works (papers) by keyword."""
        params = {
            "search": query,
            "per_page": limit,
            "select": "id,title,publication_year,primary_location,authorships,cited_by_count,abstract_inverted_index",
        }
        data = await self._get("works", params=params)
        return data.get("results", [])
