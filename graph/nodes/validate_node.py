import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def _infer_country_from_institution(institution: str) -> str:
    """Infer country from institution name using keyword matching.
    Shared copy from verify_pi_node — kept local to avoid circular imports.
    """
    if not institution:
        return ""
    inst_lower = institution.lower()

    USA_KEYWORDS = [
        "university", "college", "institute", "hospital", "nih",
        "national institutes", "stanford", "mit", "harvard", "yale",
        "princeton", "columbia", "caltech", "johns hopkins", "carnegie",
        "rutgers", "purdue", "cornell", "penn state", "michigan", "ohio",
        "florida", "texas", "california", "washington", "new york",
        "boston", "georgia", "illinois", "wisconsin", "minnesota",
        "arizona", "indiana", "virginia", "maryland", "north carolina",
        "pittsburgh", "mayo clinic", "veterans affairs", "emory",
        "vanderbilt", "duke", "rice", "tufts", "northeastern",
        "brigham", "massachusetts", "connecticut", "rochester",
    ]
    UK_KEYWORDS = [
        "oxford", "cambridge", "imperial", "ucl", "king's college london",
        "london school", "edinburgh", "manchester", "birmingham", "bristol",
        "southampton", "nottingham", "warwick", "glasgow", "sheffield",
        "leeds", "liverpool", "newcastle", "cardiff", "exeter",
        "queen mary", "durham", "bath", "surrey", "leicester",
        "hammersmith", "nhs", "wellcome",
    ]
    CANADA_KEYWORDS = [
        "toronto", "mcgill", "ubc", "university of british columbia",
        "alberta", "waterloo", "queens university", "dalhousie",
        "montreal", "ottawa", "calgary", "western university",
        "mcmaster", "simon fraser", "laval",
    ]

    for kw in UK_KEYWORDS:
        if kw in inst_lower:
            return "UK"
    for kw in CANADA_KEYWORDS:
        if kw in inst_lower:
            return "Canada"
    for kw in USA_KEYWORDS:
        if kw in inst_lower:
            return "USA"
    return ""


async def validate_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Validate enriched candidates against hard constraints.

    - Enforces country hard constraint (must be in `target_countries`).
    - Ensures each candidate has at least one piece of `evidence`.
    - Produces `validated_shortlist` in state.

    Country resolution order:
      1. Explicit country field on candidate
      2. Inferred from institution name (keyword matching)
      3. If source == 'nih_reporter', default to USA
      4. Block if still unresolvable

    NOTE: candidates are flat dicts at this stage; the nested `supervisor`
    sub-object only exists in the final output built by output_node.
    """
    enriched: List[Dict[str, Any]] = state.get("enriched_candidates", []) or []
    target_countries = state.get("target_countries") or []

    validated = []
    blocked_by_country = 0
    blocked_by_evidence = 0

    for c in enriched:
        # Candidates in the real pipeline are flat dicts; some test fixtures
        # use a nested `supervisor` sub-dict. Support both.
        sup = c.get("supervisor") or {}
        country = c.get("country") or sup.get("country") or ""

        if target_countries:
            # Resolve country through multiple fallbacks before blocking
            if not country or country in ("Unknown", ""):
                # 1. Try institution-name inference
                institution = c.get("institution") or sup.get("institution") or ""
                country = _infer_country_from_institution(institution)

            if not country or country in ("Unknown", ""):
                # 2. NIH source → always USA
                if c.get("source") == "nih_reporter":
                    country = "USA"

            # Write resolved country back to candidate so output_node sees it
            if country and country not in ("Unknown", ""):
                c["country"] = country

            # Hard constraint: block if still not in target list
            if not country or country not in target_countries:
                blocked_by_country += 1
                continue

        evidence = c.get("evidence") or c.get("papers") or c.get("grants") or []
        if not evidence:
            blocked_by_evidence += 1
            continue
        c["evidence"] = evidence

        validated.append(c)

    state["validated_shortlist"] = validated
    state["validation_summary"] = {
        "input_count": len(enriched),
        "validated_count": len(validated),
        "blocked_by_country": blocked_by_country,
        "blocked_by_evidence": blocked_by_evidence,
    }

    logger.info("validate_node_complete", **state["validation_summary"]) if logger else None
    return state
