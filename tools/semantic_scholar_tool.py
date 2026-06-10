"""
LangChain @tool wrapper for Semantic Scholar searches.

Provides `search_semantic_scholar(query, limit=10)` which returns a list of candidate
records in a normalized dict form. Designed to be called by a ReAct agent.
"""
from __future__ import annotations
from typing import List
import structlog
from langchain.tools import tool

from data_sources.base import BaseDataSource

logger = structlog.get_logger()


class SemanticScholarClient(BaseDataSource):
    BASE_URL = "https://api.semanticscholar.org/graph/v1"
    SOURCE_NAME = "semantic_scholar"

    async def search_papers(self, query: str, limit: int = 10) -> dict:
        endpoint = "paper/search"
        params = {
            "query": query,
            "limit": limit,
            "fields": "title,authors,year,doi,openAccessPdf,abstract,url,citationCount"
        }
        return await self._get(endpoint, params=params)


@tool
async def search_semantic_scholar(query: str, limit: int = 10) -> List[dict]:
    """
    Search Semantic Scholar for papers matching `query` and return normalized candidate records.

    Docstring used as tool description for ReAct agents. The tool must return a list of dicts.
    Each dict should include at least: `id`, `source`, `title`, `authors`, `year`, `doi`, `url`, `citation_count`, `abstract`.
    """
    client = SemanticScholarClient()
    try:
        resp = await client.search_papers(query, limit=limit)
        hits = resp.get("data") or resp.get("results") or []
        out = []
        for h in hits:
            item = {
                "id": h.get("paperId") or h.get("id") or h.get("doi") or h.get("url"),
                "source": "semantic_scholar",
                "title": h.get("title"),
                "authors": [a.get("name") for a in h.get("authors", [])],
                "year": h.get("year"),
                "doi": h.get("doi"),
                "url": h.get("url") or (h.get("openAccessPdf") or {}).get("url"),
                "citation_count": h.get("citationCount"),
                "abstract": h.get("abstract"),
            }
            out.append(item)
        logger.info("semantic_scholar_search", query=query, results=len(out))
        return out
    except Exception as e:
        logger.error("semantic_scholar_error", error=str(e), query=query)
        return []
