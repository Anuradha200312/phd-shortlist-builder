"""
LangChain @tool wrapper for FindAPhD search scraping.

Provides `search_findaphd(query, limit=10)` which scrapes search results and
returns normalized position/PhD-advert records.
"""
from __future__ import annotations
from typing import List
import urllib.parse
import structlog
from langchain.tools import tool
import httpx
from bs4 import BeautifulSoup

logger = structlog.get_logger()


@tool
async def search_findaphd(query: str, limit: int = 10) -> List[dict]:
    """
    Search FindAPhD for `query` and return a list of positions.

    Each item includes: `id`, `source`, `title`, `institution`, `location`, `url`, `summary`.
    """
    base = "https://www.findaphd.com"
    search_url = f"{base}/search.aspx?Keywords={urllib.parse.quote(query)}"
    out = []
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(search_url)
            resp.raise_for_status()
            html = resp.text
        soup = BeautifulSoup(html, "html.parser")
        results = soup.select(".resultitem, .search-result, .phditem")[:limit]
        for r in results:
            a = r.find("a", href=True)
            title = a.get_text(strip=True) if a else None
            url = base + a["href"] if a and a["href"].startswith("/") else (a["href"] if a else None)
            inst = r.select_one(".university, .institution")
            institution = inst.get_text(strip=True) if inst else None
            loc = r.select_one(".location")
            location = loc.get_text(strip=True) if loc else None
            summary = r.select_one("p") and r.select_one("p").get_text(strip=True)
            item = {
                "id": url,
                "source": "findaphd",
                "title": title,
                "institution": institution,
                "location": location,
                "url": url,
                "summary": summary,
            }
            out.append(item)
        logger.info("findaphd_search", query=query, results=len(out))
        return out
    except Exception as e:
        logger.error("findaphd_error", error=str(e), query=query)
        return []
