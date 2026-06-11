"""verify_pi_node: Career-stage verification with faculty directory hard gate.
Phase 2: Rule-based + faculty dir + LLM, after mapping paper records to supervisors."""
from __future__ import annotations
import structlog
from graph.state import ShortlistState
from chains.pi_verify_chain import verify_pi_status
from data_sources.openalex import OpenAlexClient
from data_sources.semantic_scholar import SemanticScholarClient

logger = structlog.get_logger()

def normalize_country(country: str) -> str:
    if not country:
        return "Unknown"
    c = country.upper().strip()
    if c in ("US", "USA", "UNITED STATES", "UNITED STATES OF AMERICA"):
        return "USA"
    if c in ("GB", "UK", "UNITED KINGDOM", "GREAT BRITAIN"):
        return "UK"
    return country

async def enrich_paper_to_supervisor(c: dict) -> dict:
    """Enrich a paper candidate into a supervisor candidate."""
    # Start with a copy of candidate
    sup = dict(c)
    
    # 1. Identify supervisor name from authors list (usually the last author)
    authors = c.get("authors", [])
    if not authors:
        sup["name"] = sup.get("name") or "Unknown"
        return sup
        
    name = authors[-1]
    sup["name"] = name
    
    # Preserve the paper as evidence
    paper_evidence = {
        "type": "paper",
        "title": c.get("title", "Unknown Paper"),
        "venue": c.get("venue"),
        "year": c.get("year"),
        "url": c.get("url"),
        "doi": c.get("doi"),
    }
    sup["papers"] = [paper_evidence]
    sup["evidence"] = [paper_evidence]

    # Query APIs to enrich the author profile
    source = c.get("source")
    if source == "openalex":
        try:
            client = OpenAlexClient()
            results = await client.search_authors(query=name, limit=1)
            if results:
                author = results[0]
                sup["openalex_id"] = author.get("id")
                sup["orcid"] = author.get("orcid")
                if sup["orcid"] and sup["orcid"].startswith("https://orcid.org/"):
                    sup["orcid"] = sup["orcid"].replace("https://orcid.org/", "")
                sup["paper_count"] = author.get("works_count", 0)
                sup["h_index"] = author.get("summary_stats", {}).get("h_index", 0)
                
                insts = author.get("last_known_institutions", [])
                if insts:
                    sup["institution"] = insts[0].get("display_name")
                    sup["country"] = normalize_country(insts[0].get("country_code"))
                
                # Fetch recent works to find last paper year
                if sup["openalex_id"]:
                    works = await client.get_author_works(sup["openalex_id"].split("/")[-1], limit=5)
                    if works:
                        sup["last_paper_year"] = max([w.get("publication_year") for w in works if w.get("publication_year")] or [c.get("year") or 0])
                        # Add extra papers to evidence
                        for w in works[:4]:
                            if w.get("title") != c.get("title"):
                                extra_paper = {
                                    "type": "paper",
                                    "title": w.get("title", "Unknown Paper"),
                                    "year": w.get("publication_year"),
                                    "doi": w.get("doi"),
                                }
                                sup["papers"].append(extra_paper)
                                sup["evidence"].append(extra_paper)
        except Exception as e:
            logger.warning("openalex_enrich_failed", name=name, error=str(e))
            
    elif source == "semantic_scholar":
        try:
            client = SemanticScholarClient()
            results = await client.search_authors(query=name, limit=1)
            if results:
                author_id = results[0].get("authorId")
                if author_id:
                    profile = await client.get_author(author_id)
                    sup["semantic_scholar_id"] = author_id
                    sup["h_index"] = profile.get("hIndex", 0)
                    sup["paper_count"] = profile.get("paperCount", 0)
                    
                    affs = profile.get("affiliations", [])
                    if affs:
                        sup["institution"] = affs[0]
                        
                    papers = profile.get("papers", [])
                    if papers:
                        sup["last_paper_year"] = max([p.get("year") for p in papers if p.get("year")] or [c.get("year") or 0])
                        # Add extra papers to evidence
                        for p in papers[:4]:
                            if p.get("title") != c.get("title"):
                                extra_paper = {
                                    "type": "paper",
                                    "title": p.get("title", "Unknown Paper"),
                                    "year": p.get("year"),
                                    "venue": p.get("venue"),
                                }
                                sup["papers"].append(extra_paper)
                                sup["evidence"].append(extra_paper)
        except Exception as e:
            logger.warning("semantic_scholar_enrich_failed", name=name, error=str(e))

    # Fallbacks for missing fields
    sup["institution"] = sup.get("institution") or "Unknown"
    sup["country"] = sup.get("country") or "Unknown"
    sup["last_paper_year"] = sup.get("last_paper_year") or c.get("year")
    
    return sup

async def verify_pi_node(state: ShortlistState) -> dict:
    """Verify candidates are faculty PIs, not students or postdocs."""
    candidates = state["resolved_candidates"]
    logger.info("verify_pi_node_start", candidates_in=len(candidates))

    verified = []
    for c in candidates:
        # 1. Map and enrich the candidate first
        enriched_candidate = await enrich_paper_to_supervisor(c)
        
        # 2. Call the real PI verification chain
        result = await verify_pi_status(enriched_candidate)
        if result["is_pi_verified"]:
            verified.append({**enriched_candidate, **result})
        else:
            logger.info("pi_verify_rejected", name=enriched_candidate.get("name"), reason=result.get("contamination_risk"))

    logger.info("verify_pi_node_complete", candidates_out=len(verified))

    return {"resolved_candidates": verified}
