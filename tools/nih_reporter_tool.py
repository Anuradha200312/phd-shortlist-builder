"""
LangChain @tool wrapper for NIH RePORTER project search.

Provides `search_nih_reporter(query, limit=10)` returning normalized grant/project records.
"""
from __future__ import annotations
from typing import List
import httpx
import structlog
from langchain.tools import tool

from data_sources.base import BaseDataSource

logger = structlog.get_logger()


class NIHReporterClient(BaseDataSource):
    BASE_URL = "https://api.reporter.nih.gov/v2"
    SOURCE_NAME = "nih_reporter"

    async def search_projects(self, query: str, limit: int = 10) -> dict:
        endpoint = "projects/search"
        url = f"{self.BASE_URL}/{endpoint}"
        
        # NIH RePORTER API v2 requires a POST request with specific payload
        payload = {
            "criteria": {
                "advanced_text_search": {
                    "search_text": query,
                    "search_field": "projecttitle,terms"
                }
            },
            "include_fields": [
                "ProjectNum",
                "ApplId",
                "ProjectTitle",
                "OrgName",
                "Fy",
                "AwardAmount",
                "AbstractText",
                "PrincipalInvestigators"
            ],
            "limit": limit
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()


@tool
async def search_nih_reporter(query: str, limit: int = 10) -> List[dict]:
    """
    Search NIH RePORTER for projects matching `query` and return normalized grant records.

    Returns list of dicts each with: `id`, `source`, `title`, `authors`, `pi_name`, `organization`, `year`, `award_amount`, `abstract`.
    """
    client = NIHReporterClient()
    try:
        resp = await client.search_projects(query, limit=limit)
        results = resp.get("results") or []
        out = []
        for p in results:
            pi_list = p.get("PrincipalInvestigators") or []
            pi_name = None
            if pi_list:
                contact_pi = next((pi for pi in pi_list if pi.get("is_contact_pi")), pi_list[0])
                pi_name = contact_pi.get("full_name") or f"{contact_pi.get('first_name', '')} {contact_pi.get('last_name', '')}".strip()
                if pi_name and "," in pi_name:
                    parts = pi_name.split(",")
                    pi_name = f"{parts[1].strip()} {parts[0].strip()}"

            item = {
                "id": p.get("ProjectNum") or str(p.get("ApplId")) or p.get("id"),
                "source": "nih_reporter",
                "title": p.get("ProjectTitle"),
                "authors": [pi_name] if pi_name else [],
                "pi_name": pi_name,
                "organization": p.get("OrgName"),
                "institution": p.get("OrgName"),  # carry forward for dedup/country
                "country": "USA",  # NIH is a US federal agency — all grants are USA
                "year": p.get("Fy"),
                "award_amount": p.get("AwardAmount"),
                "abstract": p.get("AbstractText") or None,
            }
            out.append(item)
        logger.info("nih_reporter_search", query=query, results=len(out))
        return out
    except Exception as e:
        logger.error("nih_reporter_error", error=str(e), query=query)
        return []
