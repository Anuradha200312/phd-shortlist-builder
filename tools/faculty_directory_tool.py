"""
LangChain @tool to fetch and parse a faculty page for PI verification.

Provides `scrape_faculty_page(url)` which returns a normalized dict with keys:
`url`, `name`, `title`, `department`, `email`, `phone`, `positions`, `profile_text`.

This tool is intended to be used by the ReAct agent when a candidate's faculty page is available.
"""
from __future__ import annotations
from typing import Optional
import structlog
from langchain.tools import tool
import httpx
from bs4 import BeautifulSoup

logger = structlog.get_logger()


@tool
async def scrape_faculty_page(url: str, timeout: int = 15) -> Optional[dict]:
    """
    Scrape a faculty profile page and return structured fields.

    The ReAct agent should call this tool when it has a candidate faculty page URL.
    The tool returns None on failure.
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            html = resp.text

        soup = BeautifulSoup(html, "html.parser")

        # Heuristics to extract common fields
        name = soup.find(["h1", "h2"]) and soup.find(["h1", "h2"]).get_text(strip=True)
        title = None
        for sel in [".title", ".position", "p.title", "span.position"]:
            el = soup.select_one(sel)
            if el:
                title = el.get_text(strip=True)
                break

        email = None
        mail = soup.select_one("a[href^=mailto]")
        if mail:
            email = mail.get_text(strip=True)

        dept = None
        dept_el = soup.find(text=lambda t: t and "department" in t.lower())
        if dept_el:
            parent = dept_el.parent
            dept = parent.get_text(strip=True)

        profile_text = "\n".join(p.get_text(strip=True) for p in soup.find_all("p")[:10])

        out = {
            "url": url,
            "name": name,
            "title": title,
            "department": dept,
            "email": email,
            "profile_text": profile_text,
        }
        logger.info("scrape_faculty_page_ok", url=url)
        return out
    except Exception as e:
        logger.error("scrape_faculty_page_error", url=url, error=str(e))
        return None
