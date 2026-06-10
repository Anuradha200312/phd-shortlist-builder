"""
LangChain @tool wrapper for NIH RePORTER project search.

Provides `search_nih_reporter(query, limit=10)` returning normalized grant/project records.
"""
from __future__ import annotations
from typing import List
import structlog
from langchain.tools import tool

from data_sources.base import BaseDataSource

logger = structlog.get_logger()


class NIHReporterClient(BaseDataSource):
    BASE_URL = "https://api.reporter.nih.gov/v1"
    SOURCE_NAME = "nih_reporter"

    async def search_projects(self, query: str, limit: int = 10) -> dict:
        endpoint = "projects/search"
        params = {"query": query, "size": limit}
        return await self._get(endpoint, params=params)


@tool
async def search_nih_reporter(query: str, limit: int = 10) -> List[dict]:
    """
    Search NIH RePORTER for projects matching `query` and return normalized grant records.

    Returns list of dicts each with: `id`, `source`, `title`, `pi_name`, `organization`, `year`, `award_amount`, `abstract`.
    """
    client = NIHReporterClient()
    try:
        resp = await client.search_projects(query, limit=limit)
        results = resp.get("results") or resp.get("projects") or []
        out = []
        for p in results:
            item = {
                "id": p.get("projectNumber") or p.get("applicationId") or p.get("id"),
                "source": "nih_reporter",
                "title": p.get("projectTitle") or p.get("title"),
                "pi_name": (p.get("piNames") or [p.get("principal_investigator")])[0] if (p.get("piNames") or p.get("principal_investigator")) else None,
                "organization": p.get("organizationName") or p.get("org_name"),
                "year": p.get("fy") or p.get("projectStartYear"),
                "award_amount": p.get("awardAmount") or p.get("totalCost"),
                "abstract": p.get("abstractText") or p.get("abstract") or None,
            }
            out.append(item)
        logger.info("nih_reporter_search", query=query, results=len(out))
        return out
    except Exception as e:
        logger.error("nih_reporter_error", error=str(e), query=query)
        return []
