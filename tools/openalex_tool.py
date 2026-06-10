"""
LangChain @tool wrapper for OpenAlex API searches.

Provides `search_openalex(query, limit=10)` returning normalized records. Uses OpenAlex
works endpoint and normalizes output for the pipeline.
"""
from __future__ import annotations
from typing import List
import structlog
from langchain.tools import tool

from data_sources.base import BaseDataSource

logger = structlog.get_logger()


class OpenAlexClient(BaseDataSource):
    BASE_URL = "https://api.openalex.org"
    SOURCE_NAME = "openalex"

    async def search_works(self, query: str, limit: int = 10) -> dict:
        endpoint = "works"
        params = {
            "search": query,
            "per-page": limit
        }
        return await self._get(endpoint, params=params)


@tool
async def search_openalex(query: str, limit: int = 10) -> List[dict]:
    """
    Search OpenAlex for works matching `query` and return normalized candidate records.

    Returns list of dicts each with: `id`, `source`, `title`, `authors`, `year`, `doi`, `url`, `citation_count`, `abstract`.
    """
    client = OpenAlexClient()
    try:
        resp = await client.search_works(query, limit=limit)
        results = resp.get("results") or resp.get("data") or []
        out = []
        for w in results:
            authors = [a.get("author", {}).get("display_name") for a in w.get("authorships", [])]
            item = {
                "id": w.get("id"),
                "source": "openalex",
                "title": w.get("title"),
                "authors": authors,
                "year": w.get("publication_year"),
                "doi": w.get("doi"),
                "url": w.get("id"),
                "citation_count": w.get("cited_by_count"),
                "abstract": w.get("abstract") or None,
            }
            out.append(item)
        logger.info("openalex_search", query=query, results=len(out))
        return out
    except Exception as e:
        logger.error("openalex_error", error=str(e), query=query)
        return []
