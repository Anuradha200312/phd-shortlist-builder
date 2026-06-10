# schema.md — Output JSON Schema Documentation

**PhD Shortlist Builder v1.0.0**

---

## Overview

The PhD Shortlist Builder outputs a single JSON file per student containing a ranked list of supervisor recommendations with evidence, explanations, and quality signals.

**File Location:** `sample_output/{student_id}.json`

**Size:** Typically 200–800 KB (depends on number of supervisors and evidence)

---

## Top-Level Schema

```json
{
  "student_id": "string",
  "generated_at": "string (ISO 8601 timestamp)",
  "pipeline_version": "string (semver, e.g. '1.0.0')",
  "shortlist": [/* ShortlistEntry[] */],
  "metadata": {/* PipelineMetadata */}
}
```

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|------------|
| `student_id` | string | Yes | Unique identifier for the student (from input profile) |
| `generated_at` | string | Yes | ISO 8601 timestamp (UTC) of when the shortlist was generated |
| `pipeline_version` | string | Yes | Version of the PhD Shortlist Builder (e.g., "1.0.0") |
| `shortlist` | array | Yes | Array of ShortlistEntry objects, ranked by confidence_score (descending) |
| `metadata` | object | Yes | Pipeline execution metadata and statistics |

---

## ShortlistEntry Schema

Each entry represents one supervisor recommendation:

```json
{
  "rank": 1,
  "supervisor": {/* SupervisorInfo */},
  "research_focus": ["string"],
  "evidence": [/* Evidence[] */],
  "why_match": "string",
  "tier": "string (reach|target|safety|review_needed)",
  "open_positions": [/* OpenPosition[] */],
  "eligibility_flags": ["string"],
  "contamination_risk": ["string"],
  "confidence_score": 0.87,
  "confidence_breakdown": {/* ConfidenceBreakdown */},
  "match_dimensions": {/* MatchDimensions */}
}
```

### Rank
- **Type:** integer (1–200+)
- **Required:** Yes
- **Description:** Position in the ranked shortlist (1 = best match)

---

## SupervisorInfo Schema

```json
{
  "name": "string",
  "institution": "string",
  "department": "string or null",
  "country": "string",
  "email": "string or null",
  "profile_url": "string (URL) or null",
  "orcid": "string (ORCID ID) or null",
  "semantic_scholar_id": "string or null",
  "openalex_id": "string or null",
  "google_scholar_id": "string or null"
}
```

### Example

```json
{
  "name": "Dr. Jane Smith",
  "institution": "Stanford University",
  "department": "Computer Science",
  "country": "USA",
  "email": "jane@stanford.edu",
  "profile_url": "https://profiles.stanford.edu/jane-smith",
  "orcid": "0000-0002-1234-5678",
  "semantic_scholar_id": "2156219",
  "openalex_id": "A123456789",
  "google_scholar_id": "janesmith"
}
```

### Notes
- `orcid`, `profile_url`, `email`, and IDs may be null if not available
- `openalex_id` is the master identifier (used internally to disambiguate)
- `orcid` is verified via ORCID API if available (part of 3-Signal Lock)

---

## Research Focus

```json
"research_focus": [
  "machine learning",
  "natural language processing",
  "transformers",
  "interpretability"
]
```

- **Type:** string array
- **Required:** Yes
- **Description:** Top research areas for this supervisor (extracted from papers)
- **Typical Count:** 3–10 areas

---

## Evidence Schema

Each evidence item represents a paper or grant with verifiable links:

```json
{
  "type": "string (paper|grant)",
  "title": "string",
  "venue": "string (e.g., 'NeurIPS 2024') or null",
  "year": "integer or null",
  "url": "string (DOI or paper URL) or null",
  "doi": "string or null",
  "funder": "string (for grants) or null"
}
```

### Example Paper

```json
{
  "type": "paper",
  "title": "Attention is All You Need",
  "venue": "NeurIPS 2017",
  "year": 2017,
  "url": "https://arxiv.org/abs/1706.03762",
  "doi": "10.48550/arXiv.1706.03762",
  "funder": null
}
```

### Example Grant

```json
{
  "type": "grant",
  "title": "Interpretable Machine Learning for Healthcare",
  "venue": null,
  "year": 2023,
  "url": "https://nsf.gov/awardsearch/showAward?AWD_ID=2300123",
  "doi": null,
  "funder": "NSF (National Science Foundation)"
}
```

### Notes
- `evidence` array typically contains 5–8 items (top papers + top grants)
- All URLs are clickable and verified (not hallucinated)
- DOIs resolve to actual papers/grants

---

## Why_Match

```json
"why_match": "Dr. Jane Smith's recent work on transformer interpretability directly aligns with your interest in explainable AI. Her 2024 paper on attention mechanisms (cited 1200 times) builds on the techniques you studied in your thesis on neural network interpretability. She collaborates with researchers at MIT and Stanford who work on similar problems. Her lab has published 15 papers in the last 2 years, showing active research. Stanford is also listed among your target countries and has a strong ML PhD program."
```

- **Type:** string (200–400 words)
- **Required:** Yes
- **Description:** LLM-generated personalized explanation of why this supervisor is a good match
- **Grounding:** References specific papers, citations, dates, and student profile details
- **Tone:** Professional, concise, actionable

---

## Tier

```json
"tier": "target"
```

- **Type:** enum (reach | target | safety | review_needed)
- **Required:** Yes
- **Meaning:**
  - `reach` — Dream supervisor, excellent but competitive (confidence_score 0.8–1.0)
  - `target` — Strong match, likely good fit (confidence_score 0.6–0.8)
  - `safety` — Solid option, reliable match (confidence_score 0.4–0.6)
  - `review_needed` — Flagged for contamination or data quality issues

---

## Open Positions

```json
[
  {
    "title": "PhD in Machine Learning",
    "url": "https://www.findaphd.com/programs/machine-learning-123",
    "deadline": "2026-03-15",
    "eligibility_flags": [
      "open_to_international",
      "full_funding_available"
    ],
    "source": "findaphd"
  }
]
```

- **Type:** array of objects
- **Required:** Yes (may be empty)
- **Count:** 0–3 positions per supervisor
- **Source:** FindAPhD, jobs.ac.uk, university career pages

### Open Position Fields

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | PhD program/position title |
| `url` | string | Direct link to application |
| `deadline` | string (ISO date) or null | Application deadline |
| `eligibility_flags` | array | Flags indicating suitability for student |
| `source` | string | Where position was sourced (findaphd, jobs_ac_uk, faculty_page) |

### Eligibility Flags

- `open_to_international` — Position accepts international applicants
- `full_funding_available` — Full funding (fees + stipend) offered
- `partial_funding_available` — Partial funding or scholarship
- `accepts_{country}` — Explicitly open to applicants from student's country
- `phd_only` — PhD only (not Master's)
- `funded` — Any funding available

---

## Eligibility Flags

```json
"eligibility_flags": [
  "has_open_phd_position",
  "open_to_international",
  "full_funding_available",
  "accepts_usa"
]
```

- **Type:** string array
- **Required:** Yes (may be empty)
- **Description:** Flags indicating program eligibility for the student

---

## Contamination Risk

```json
"contamination_risk": [
  "advisor_overlap: supervisor published with student's current advisor",
  "data_stale: last paper 7 months old (expected <= 6 months)"
]
```

- **Type:** string array
- **Required:** Yes (may be empty)
- **Description:** Flags indicating potential data quality or conflict-of-interest issues
- **When Present:** Supervision was flagged in contamination self-audit (top-30 only)

### Common Flags

- `student_advisor_conflict` — Supervisor is student's current advisor
- `advisor_overlap` — Supervisor published with student's advisor
- `student_involvement` — Student may have recent involvement (shared author)
- `data_stale` — Last paper / grant data older than 6 months
- `faculty_page_not_confirmed` — Faculty page lookup failed (3-Signal Lock failed)

---

## Confidence Score

```json
"confidence_score": 0.87
```

- **Type:** float (0.0–1.0)
- **Required:** Yes
- **Meaning:** Overall match confidence (used for ranking)
- **Calculation:** 6-signal weighted average (see ConfidenceBreakdown)

### Score Interpretation

| Score Range | Interpretation | Tier |
|------------|----------------|------|
| 0.8–1.0 | Excellent match | reach |
| 0.6–0.8 | Strong match | target |
| 0.4–0.6 | Solid option | safety |
| 0.2–0.4 | Marginal match | review_needed |
| < 0.2 | Not included (filtered earlier) | — |

---

## Confidence Breakdown

```json
{
  "orcid_verified": true,
  "orcid_score": 1.0,
  "faculty_page_confirmed": true,
  "faculty_score": 0.95,
  "paper_topic_overlap": 0.89,
  "overlap_score": 0.89,
  "recent_activity": true,
  "recency_score": 0.9,
  "eligibility_clear": true,
  "eligibility_score": 0.8,
  "h_index": 42,
  "hindex_score": 0.9,
  "total_score": 0.87
}
```

### Component Scores (each 0.0–1.0)

| Component | Weight | Description |
|-----------|--------|-------------|
| `orcid_score` | 20% | ORCID verification (1.0 if verified, 0.0 if not) |
| `faculty_score` | 15% | Faculty page confirmation (1.0 if confirmed) |
| `overlap_score` | 30% | Research topic overlap (cosine similarity of embeddings) |
| `recency_score` | 15% | Recent activity (0.0 if no papers in 5 years, 1.0 if recent) |
| `eligibility_score` | 10% | Program eligibility (country match, funding availability) |
| `hindex_score` | 10% | H-index normalized (0.0–1.0 scale) |

### Total Calculation

```
total_score = (
    orcid_score * 0.20 +
    faculty_score * 0.15 +
    overlap_score * 0.30 +
    recency_score * 0.15 +
    eligibility_score * 0.10 +
    hindex_score * 0.10
)
```

---

## Match Dimensions

```json
{
  "research_overlap": 0.89,
  "recent_activity": true,
  "is_pi_verified": true,
  "h_index": 42,
  "country_match": true,
  "domain_confidence": 0.92,
  "last_paper_year": 2024
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `research_overlap` | float (0–1) | Semantic similarity between supervisor's research and student's interests |
| `recent_activity` | boolean | Is last paper within 5 years? |
| `is_pi_verified` | boolean | Confirmed as faculty PI (not student/postdoc) |
| `h_index` | integer | Hirsch index from Semantic Scholar / OpenAlex |
| `country_match` | boolean | Supervisor's country in student's target_countries |
| `domain_confidence` | float (0–1) | Confidence that supervisor is in correct research domain (passes 2-layer filter) |
| `last_paper_year` | integer | Year of most recent publication |

---

## PipelineMetadata

```json
{
  "total_candidates_considered": 312,
  "data_sources": [
    "semantic_scholar",
    "openalex"
  ],
  "llm_provider_used": "groq",
  "langgraph_run_id": "a1b2c3d4",
  "langsmith_trace_url": "https://smith.langchain.com/public/...",
  "run_duration_seconds": 145.3,
  "audit_summary": {
    "total_audited": 30,
    "clean": 28,
    "flagged": 2,
    "removed": 0
  }
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `total_candidates_considered` | integer | Total supervisors retrieved before filtering |
| `data_sources` | array | APIs used (semantic_scholar, openalex, nih_reporter, ukri_gateway, findhaphd) |
| `llm_provider_used` | string | LLM that generated why_match and confidence_breakdown (groq, ollama) |
| `langgraph_run_id` | string | Unique ID for this pipeline run (first 8 chars of UUID) |
| `langsmith_trace_url` | string | URL to full LangSmith trace (if tracing enabled) |
| `run_duration_seconds` | float | Total wall-clock time (sec) |
| `audit_summary` | object | Contamination audit results on top-30 |

### Audit Summary

| Field | Type | Description |
|-------|------|-------------|
| `total_audited` | integer | Number of entries audited (usually 30) |
| `clean` | integer | Entries with no contamination flags |
| `flagged` | integer | Entries with 1+ contamination flags |
| `removed` | integer | Entries removed during audit (0 in current implementation) |

---

## Complete Example

```json
{
  "student_id": "alice_2024",
  "generated_at": "2026-06-10T15:32:45.123456Z",
  "pipeline_version": "1.0.0",
  "shortlist": [
    {
      "rank": 1,
      "supervisor": {
        "name": "Dr. Jane Smith",
        "institution": "Stanford University",
        "department": "Computer Science",
        "country": "USA",
        "email": "jane@stanford.edu",
        "profile_url": "https://profiles.stanford.edu/jane-smith",
        "orcid": "0000-0002-1234-5678",
        "semantic_scholar_id": "2156219",
        "openalex_id": "A123456789",
        "google_scholar_id": "janesmith"
      },
      "research_focus": [
        "machine learning",
        "natural language processing",
        "interpretability"
      ],
      "evidence": [
        {
          "type": "paper",
          "title": "Attention is All You Need",
          "venue": "NeurIPS 2017",
          "year": 2017,
          "url": "https://arxiv.org/abs/1706.03762",
          "doi": "10.48550/arXiv.1706.03762",
          "funder": null
        },
        {
          "type": "paper",
          "title": "Transformers are Universal Approximators",
          "venue": "ICML 2024",
          "year": 2024,
          "url": "https://arxiv.org/abs/2405.12345",
          "doi": "10.48550/arXiv.2405.12345",
          "funder": null
        },
        {
          "type": "grant",
          "title": "Understanding Transformer Interpretability",
          "venue": null,
          "year": 2023,
          "url": "https://nsf.gov/awardsearch/showAward?AWD_ID=2300123",
          "doi": null,
          "funder": "NSF"
        }
      ],
      "why_match": "Dr. Jane Smith's recent work on transformer interpretability directly aligns with your interest in explainable AI. Her 2024 paper on attention mechanisms (cited 1200 times) builds on the techniques you studied in your thesis. She collaborates with researchers at MIT and maintains active publications. Stanford has an excellent PhD program and is in your target country.",
      "tier": "target",
      "open_positions": [
        {
          "title": "PhD in Computer Science (ML Track)",
          "url": "https://www.findaphd.com/programs/stanford-cs-ml-2024",
          "deadline": "2026-12-15",
          "eligibility_flags": [
            "open_to_international",
            "full_funding_available"
          ],
          "source": "findaphd"
        }
      ],
      "eligibility_flags": [
        "has_open_phd_position",
        "open_to_international",
        "full_funding_available",
        "accepts_usa"
      ],
      "contamination_risk": [],
      "confidence_score": 0.87,
      "confidence_breakdown": {
        "orcid_verified": true,
        "orcid_score": 1.0,
        "faculty_page_confirmed": true,
        "faculty_score": 0.95,
        "paper_topic_overlap": 0.89,
        "overlap_score": 0.89,
        "recent_activity": true,
        "recency_score": 0.9,
        "eligibility_clear": true,
        "eligibility_score": 0.8,
        "h_index": 42,
        "hindex_score": 0.9,
        "total_score": 0.87
      },
      "match_dimensions": {
        "research_overlap": 0.89,
        "recent_activity": true,
        "is_pi_verified": true,
        "h_index": 42,
        "country_match": true,
        "domain_confidence": 0.92,
        "last_paper_year": 2024
      }
    },
    {
      "rank": 2,
      "supervisor": {
        "name": "Prof. John Chen",
        "institution": "MIT",
        "department": "EECS",
        "country": "USA",
        "email": "jchen@mit.edu",
        "profile_url": "https://csail.mit.edu/~jchen",
        "orcid": "0000-0003-5678-9012",
        "semantic_scholar_id": "3456789",
        "openalex_id": "A987654321",
        "google_scholar_id": "johnchen"
      },
      "research_focus": [
        "deep learning",
        "computer vision",
        "neural networks"
      ],
      "evidence": [
        {
          "type": "paper",
          "title": "ResNet: Deep Residual Learning",
          "venue": "CVPR 2015",
          "year": 2015,
          "url": "https://arxiv.org/abs/1512.03385",
          "doi": "10.1109/CVPR.2015.7298965",
          "funder": null
        }
      ],
      "why_match": "Prof. Chen's foundational work on residual networks has been influential across computer science. While his focus is primarily computer vision, the deep learning techniques are transferable to your NLP interests.",
      "tier": "target",
      "open_positions": [],
      "eligibility_flags": [
        "open_to_international"
      ],
      "contamination_risk": [
        "data_stale: last paper 3 years old"
      ],
      "confidence_score": 0.72,
      "confidence_breakdown": {
        "orcid_verified": true,
        "orcid_score": 1.0,
        "faculty_page_confirmed": true,
        "faculty_score": 0.9,
        "paper_topic_overlap": 0.6,
        "overlap_score": 0.6,
        "recent_activity": false,
        "recency_score": 0.5,
        "eligibility_clear": true,
        "eligibility_score": 0.9,
        "h_index": 85,
        "hindex_score": 1.0,
        "total_score": 0.72
      },
      "match_dimensions": {
        "research_overlap": 0.6,
        "recent_activity": false,
        "is_pi_verified": true,
        "h_index": 85,
        "country_match": true,
        "domain_confidence": 0.65,
        "last_paper_year": 2021
      }
    }
  ],
  "metadata": {
    "total_candidates_considered": 312,
    "data_sources": [
      "semantic_scholar",
      "openalex"
    ],
    "llm_provider_used": "groq",
    "langgraph_run_id": "a1b2c3d4",
    "langsmith_trace_url": "https://smith.langchain.com/public/...",
    "run_duration_seconds": 145.3,
    "audit_summary": {
      "total_audited": 30,
      "clean": 28,
      "flagged": 2,
      "removed": 0
    }
  }
}
```

---

## Validation Rules

- ✅ All URLs are valid and tested (not hallucinated)
- ✅ All confidence scores are 0.0–1.0
- ✅ Ranks are consecutive integers 1..N
- ✅ Shortlist is sorted by `confidence_score` descending
- ✅ All referenced countries are ISO 3166-1 (except 'USA' aliased to 'US')
- ✅ `contamination_risk` array is empty if `tier` ≠ "review_needed"
- ✅ All timestamps are ISO 8601 UTC

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | June 2026 | Initial schema (Phase 1) |

---

**Last Updated:** June 2026  
**Status:** Active — used in all outputs
