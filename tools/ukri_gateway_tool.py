"""
LangChain @tool wrapper for UKRI Gateway to Research search.

Provides `search_ukri(query, limit=10)` returning normalized grant/project records.
"""
from __future__ import annotations
from typing import List
import structlog
from langchain.tools import tool

from data_sources.base import BaseDataSource

logger = structlog.get_logger()


class UKRIClient(BaseDataSource):
    BASE_URL = "https://gtr.ukri.org/ws/"
    SOURCE_NAME = "ukri"

    async def search_projects(self, query: str, limit: int = 10) -> dict:
        endpoint = "search/projects"
        params = {"searchTerm": query, "max": limit}
        return await self._get(endpoint, params=params)


@tool
async def search_ukri(query: str, limit: int = 10) -> List[dict]:
    """
    Search UKRI GtR for projects matching `query` and return normalized grant records.

    Returns list of dicts each with: `id`, `source`, `title`, `pi_name`, `organization`, `year`, `award_amount`, `abstract`.
    """
    client = UKRIClient()
    try:
        resp = await client.search_projects(query, limit=limit)
        results = resp.get("projects") or resp.get("results") or []
        out = []
        for p in results:
            item = {
                "id": p.get("projectId") or p.get("id"),
                "source": "ukri",
                "title": p.get("projectTitle") or p.get("title"),
                "pi_name": p.get("leadResearcher") or None,
                "organization": p.get("leadOrganisationName") or None,
                "year": p.get("startYear") or None,
                "award_amount": p.get("projectTotalCost"),
                "abstract": p.get("summary") or None,
            }
            out.append(item)
        logger.info("ukri_search", query=query, results=len(out))
        return out
    except Exception as e:
        logger.error("ukri_error", error=str(e), query=query)
        return []