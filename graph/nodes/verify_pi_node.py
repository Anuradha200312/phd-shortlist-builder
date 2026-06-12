"""verify_pi_node: Career-stage verification with faculty directory hard gate.
Phase 2: Rule-based + faculty dir + LLM, after mapping paper records to supervisors."""
from __future__ import annotations
import asyncio
import structlog
from graph.state import ShortlistState
from chains.pi_verify_chain import verify_pi_status
from data_sources.openalex import OpenAlexClient

logger = structlog.get_logger()

def normalize_country(country: str) -> str:
    if not country:
        return ""
    c = country.upper().strip()
    if c in ("US", "USA", "UNITED STATES", "UNITED STATES OF AMERICA"):
        return "USA"
    if c in ("GB", "UK", "UNITED KINGDOM", "GREAT BRITAIN"):
        return "UK"
    if c in ("CA", "CAN", "CANADA"):
        return "Canada"
    return country


# Institution name fragments → country mapping (covers NIH & OpenAlex gaps)
_INST_COUNTRY_MAP = [
    # USA
    (["university", "college", "institute", "hospital", "nih", "national institutes",
      "stanford", "mit", "harvard", "yale", "princeton", "columbia", "caltech",
      "johns hopkins", "carnegie", "rutgers", "purdue", "cornell", "penn state",
      "michigan", "ohio", "florida", "texas", "california", "washington",
      "new york", "boston", "georgia", "illinois", "wisconsin", "minnesota",
      "arizona", "indiana", "virginia", "maryland", "north carolina",
      "pittsburgh", "mayo clinic", "veterans affairs"], "USA"),
    # UK
    (["oxford", "cambridge", "imperial", "ucl", "king's college london",
      "london school", "edinburgh", "manchester", "birmingham", "bristol",
      "southampton", "nottingham", "warwick", "glasgow", "sheffield",
      "leeds", "liverpool", "newcastle", "cardiff", "exeter",
      "queen mary", "durham", "bath", "surrey", "leicester",
      "hammersmith", "nhs", "wellcome"], "UK"),
    # Canada
    (["toronto", "mcgill", "ubc", "university of british columbia",
      "alberta", "waterloo", "queens university", "dalhousie",
      "montreal", "ottawa", "calgary", "western university",
      "mcmaster", "simon fraser", "laval"], "Canada"),
]


def infer_country_from_institution(institution: str) -> str:
    """Infer country from institution name using keyword matching."""
    if not institution:
        return ""
    inst_lower = institution.lower()
    for keywords, country in _INST_COUNTRY_MAP:
        for kw in keywords:
            if kw in inst_lower:
                return country
    return ""

async def enrich_paper_to_supervisor(c: dict) -> dict:
    """Enrich a paper candidate into a supervisor candidate.

    Fast path: NIH records already have name/institution/country from source.
    OpenAlex records: look up author profile only (skip works fetch to save time).
    SemanticScholar: skip API lookup (affiliation rarely returned correctly).
    """
    sup = dict(c)

    # --- Name resolution ---
    authors = c.get("authors", [])
    if c.get("name"):
        pass  # already resolved (NIH sets name=PI name at tool level)
    elif authors:
        sup["name"] = authors[-1]
    else:
        sup["name"] = "Unknown"
        return sup

    name = sup["name"]

    # Build paper evidence from this record
    paper_evidence = {
        "type": "paper",
        "title": c.get("title", "Unknown Paper"),
        "venue": c.get("venue"),
        "year": c.get("year"),
        "url": c.get("url"),
        "doi": c.get("doi"),
    }
    if not sup.get("papers"):
        sup["papers"] = [paper_evidence]
    if not sup.get("evidence"):
        sup["evidence"] = [paper_evidence]

    source = c.get("source", "")

    # --- Fast path: NIH records are already fully enriched at source ---
    if source == "nih_reporter":
        # country=USA, institution=OrgName already set by nih_reporter_tool
        # No API call needed — just carry forward research_areas if available
        if not sup.get("research_areas"):
            sup["research_areas"] = c.get("research_areas") or c.get("keywords") or []
        sup["institution"] = sup.get("institution") or "Unknown"
        sup["country"] = sup.get("country") or "USA"
        sup["last_paper_year"] = sup.get("last_paper_year") or c.get("year")
        return sup

    # --- OpenAlex: single author profile lookup (skip works fetch) ---
    if source == "openalex":
        try:
            client = OpenAlexClient()
            results = await client.search_authors(query=name, limit=1)
            if results:
                author = results[0]
                sup["openalex_id"] = author.get("id")
                orcid = author.get("orcid") or ""
                if orcid.startswith("https://orcid.org/"):
                    orcid = orcid.replace("https://orcid.org/", "")
                sup["orcid"] = orcid or sup.get("orcid")
                sup["paper_count"] = author.get("works_count", 0)
                sup["h_index"] = author.get("summary_stats", {}).get("h_index", 0)

                insts = author.get("last_known_institutions", [])
                if insts and not sup.get("institution"):
                    sup["institution"] = insts[0].get("display_name")
                    sup["country"] = normalize_country(insts[0].get("country_code") or "")

                # Research areas from x_concepts
                concepts = author.get("x_concepts") or author.get("topics") or []
                if concepts and not sup.get("research_areas"):
                    sup["research_areas"] = [
                        x.get("display_name") or x.get("name")
                        for x in sorted(concepts, key=lambda x: x.get("score", 0), reverse=True)
                        if (x.get("display_name") or x.get("name")) and x.get("level", 0) >= 1
                    ][:10]
        except Exception as e:
            logger.warning("openalex_enrich_failed", name=name, error=str(e))

    # --- SemanticScholar / other: skip API call, use what we have ---
    # (SemanticScholar author lookup is slow and rarely returns institution country)

    # Fallbacks for missing fields
    sup["institution"] = sup.get("institution") or "Unknown"
    if not sup.get("country") or sup["country"] in ("", "Unknown"):
        inferred = infer_country_from_institution(sup["institution"])
        sup["country"] = inferred if inferred else (sup.get("country") or "Unknown")
    sup["last_paper_year"] = sup.get("last_paper_year") or c.get("year")
    if not sup.get("research_areas"):
        sup["research_areas"] = (
            c.get("research_areas") or c.get("keywords") or c.get("topics") or []
        )
    return sup

async def verify_pi_node(state: ShortlistState) -> dict:
    """Verify candidates are faculty PIs, not students or postdocs.

    Processes all candidates CONCURRENTLY (up to 15 at a time) instead of
    sequentially to dramatically reduce wall-clock time.
    """
    candidates = state["resolved_candidates"]
    logger.info("verify_pi_node_start", candidates_in=len(candidates))

    semaphore = asyncio.Semaphore(15)  # 15 concurrent enrichment + verify calls

    async def _process(c: dict):
        async with semaphore:
            try:
                enriched = await enrich_paper_to_supervisor(c)
                result = await verify_pi_status(enriched)
                if result["is_pi_verified"]:
                    return {**enriched, **result}
                else:
                    logger.debug(
                        "pi_verify_rejected",
                        name=enriched.get("name"),
                        reason=result.get("contamination_risk"),
                    )
                    return None
            except Exception as e:
                logger.warning("verify_pi_process_failed", error=str(e))
                return None

    results = await asyncio.gather(*[_process(c) for c in candidates])
    verified = [r for r in results if r is not None]

    logger.info("verify_pi_node_complete", candidates_out=len(verified))
    return {"resolved_candidates": verified}
