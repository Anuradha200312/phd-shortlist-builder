# 🎓 PhD Shortlist Builder

> **AI-powered system that surfaces ≥50 personalised PhD supervisor matches — with real paper/grant evidence and a personalised `why_match` explanation — from a student profile JSON in a single command.**

Built for the Ambitio AI Engineer take-home assignment. Powered by **LangGraph** (9-node state machine), **OpenAlex**, **NIH Reporter**, **Groq LLM**, and **ChromaDB**.

---

## 📖 How It Works — System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                       Student Profile JSON                          │
│  (research interests, target countries, education, skills, resume)  │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────── 9-Node LangGraph Pipeline ────────────────────┐
│                                                                       │
│  1. INGEST       Parse + validate student profile                     │
│       ↓                                                               │
│  2. RETRIEVE     Query OpenAlex, NIH Reporter, Semantic Scholar       │
│       ↓          (10–20 LangChain @tool calls, 400+ raw candidates)  │
│  3. RESOLVE      Disambiguate authors, domain check, dedup            │
│       ↓                                                               │
│  4. VERIFY PI    Confirm each candidate is a faculty PI               │
│       ↓          (not a PhD student, postdoc, or inactive researcher)│
│       ├──[< 50 verified]──→ retry RETRIEVE (up to 5 attempts)        │
│       ↓                                                               │
│  5. SCORE        Embed research summaries, cosine similarity          │
│       ↓          6-signal confidence score, assign tier               │
│  6. ENRICH       LLM writes personalised `why_match` per candidate   │
│       ↓                                                               │
│  7. VALIDATE     Hard constraint: 100% in target countries            │
│       ↓          Every entry must have ≥1 evidence item               │
│  8. AUDIT        Contamination self-audit on top-60 candidates        │
│       ↓          (duplicate names, low confidence, stale data)        │
│  9. OUTPUT       Save ranked JSON to sample_output/{student_id}.json  │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    sample_output/test_final.json                    │
│  77 supervisors · 100% USA/Canada/UK · evidence + why_match         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🗂️ Project Structure

```
phd-shortlist-builder/
│
├── 📄 main.py                  ← CLI entry point (Typer)
├── 📄 DECISIONS.md             ← Data quality challenge writeup
├── 📄 schema.md                ← Output JSON schema documentation
├── 📄 pyproject.toml           ← Dependencies and project metadata
│
├── 🧠 graph/                   ← LangGraph pipeline
│   ├── pipeline_graph.py       ← Assembles the 9-node StateGraph
│   ├── state.py                ← TypedDict for shared pipeline state
│   ├── edges.py                ← Conditional retry edge logic
│   └── nodes/
│       ├── ingest_node.py      ← Parse + expand student profile
│       ├── retrieve_node.py    ← Multi-source candidate retrieval
│       ├── resolve_node.py     ← Author disambiguation + dedup
│       ├── verify_pi_node.py   ← Career-stage verification
│       ├── score_node.py       ← Embedding similarity + confidence
│       ├── enrich_node.py      ← LLM why_match generation
│       ├── validate_node.py    ← Country + evidence hard constraints
│       ├── audit_node.py       ← Contamination self-audit
│       └── output_node.py      ← JSON assembly + disk write
│
├── ⛓️  chains/                  ← LangChain LLM prompt chains
│   ├── query_expansion_chain.py  ← Expand interests → search queries
│   ├── why_match_chain.py        ← Generate personalised why_match
│   ├── domain_check_chain.py     ← Filter off-topic candidates
│   └── pi_verify_chain.py        ← Multi-gate PI career check
│
├── 🔍 data_sources/            ← API clients
│   ├── openalex.py             ← OpenAlex works + author search
│   ├── semantic_scholar.py     ← Semantic Scholar papers + authors
│   └── nih_reporter.py         ← NIH grant database
│
├── 🛠️  tools/                   ← LangChain @tool wrappers
│   ├── openalex_tool.py        ← @tool: search OpenAlex papers
│   ├── nih_tool.py             ← @tool: search NIH grants
│   └── semantic_scholar_tool.py ← @tool: search SS papers
│
├── 🎯 scoring/                 ← Confidence scoring
│   └── confidence.py           ← 6-signal weighted scoring model
│
├── 🔑 llm/                     ← LLM provider management
│   ├── providers.py            ← Build LLM chain with fallbacks
│   └── key_rotation.py         ← Multi-key pool (rate-limit resilience)
│
├── 🧪 tests/                   ← Pytest unit tests (8 tests, all green)
│   ├── test_audit_node.py
│   ├── test_enrich_node.py
│   ├── test_output_node.py
│   ├── test_resolve_node.py
│   ├── test_retrieve_node.py
│   ├── test_score_node.py
│   ├── test_score_node_chroma.py
│   └── test_validate_node.py
│
├── 📊 sample_output/
│   └── test_final.json         ← 77 supervisors (USA/Canada/UK)
│
└── 📜 scripts/
    └── fast_shortlist.py       ← Fast direct-retrieval alternative
```

---

## 🚀 Quick Start — Single Command

```bash
python main.py run --profile tests/fixtures/sample_student_profile.json
```

Output is saved to `sample_output/{student_id}.json`.

---

## 📋 Prerequisites

| Requirement | Details |
|-------------|---------|
| **Python** | 3.11+ |
| **Groq API Key** | Free tier at [console.groq.com](https://console.groq.com) |
| **PostgreSQL** (optional) | Required only for checkpointing + feedback loop. Skip for basic use. |
| **Ollama** (optional) | Local LLM fallback when Groq rate-limits. |

---

## ⚙️ Installation & Setup

### Step 1 — Clone the repository

```bash
git clone https://github.com/Anuradha200312/phd-shortlist-builder.git
cd phd-shortlist-builder
```

### Step 2 — Create a virtual environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python -m venv .venv
source .venv/bin/activate
```

### Step 3 — Install dependencies

```bash
pip install -e .
```

This installs the package in editable mode using `pyproject.toml`. Includes: `langgraph`, `langchain`, `langchain-groq`, `chromadb`, `httpx`, `structlog`, `pydantic`, `fastapi`, `asyncpg`.

### Step 4 — Configure environment variables

Create a `.env` file in the project root:

```env
# Required: at least one Groq API key
GROQ_API_KEY=gsk_your_key_here

# Optional: additional keys for rate-limit rotation
GROQ_API_KEY_2=gsk_your_second_key
GROQ_API_KEY_3=gsk_your_third_key

# Optional: database (only needed for checkpointing/feedback)
DATABASE_URL=postgresql+asyncpg://phd_user:phd_pass@localhost:5432/phd_shortlist
```

> **Tip:** You can add up to 5 Groq keys (`GROQ_API_KEY` through `GROQ_API_KEY_5`). The system rotates between them automatically when rate limits are hit.

### Step 5 (Optional) — Start PostgreSQL

Required only for pipeline checkpointing and the feedback loop feature:

```bash
docker compose up -d postgres
python scripts/init_db_tables.py
```

---

## 💻 Running the System

### Option A — Full LangGraph Pipeline (Recommended)

```bash
python main.py run --profile tests/fixtures/sample_student_profile.json
```

**What this does:**
- Parses the student profile JSON
- Runs all 9 pipeline nodes in sequence
- Queries OpenAlex + NIH Reporter (400+ raw candidates)
- Filters, scores, and enriches candidates
- Writes output to `sample_output/test_001.json`

**Expected runtime:** 5–30 minutes depending on API response times and LLM rate limits.

**Output location:** `sample_output/test_001.json`

---

### Option B — Fast Direct Retrieval (< 2 minutes)

```bash
python scripts/fast_shortlist.py
```

**What this does:**
- Directly queries OpenAlex (10 targeted queries) and NIH Reporter (4 grant queries)
- Deduplicates by `name|institution` (not by paper ID)
- Applies domain relevance filter (papers must match student interest keywords)
- Writes `sample_output/test_final.json` in ~60 seconds

**Best for:** Quick re-runs and demo output. Produces 50–80 supervisors.

---

### Option C — REST API Server

```bash
python -m uvicorn api.app:app --host 127.0.0.1 --port 8000 --reload
```

Then open `http://127.0.0.1:8000/docs` for the Swagger UI.

**API Endpoints:**
- `GET /api/v1/health` — Health check
- `POST /api/v1/shortlist` — Generate shortlist (async, long-running)
- `POST /api/v1/feedback` — Upload outcome CSV to improve future rankings

---

## 🧪 Running Tests

```bash
# Run all unit tests
python -m pytest tests/ -v

# Run with short tracebacks
python -m pytest tests/ -v --tb=short

# Skip integration tests (requires running database)
python -m pytest tests/ -v --ignore=tests/integration
```

**Current status:** 8/8 tests passing ✅

```
tests/test_audit_node.py::test_audit_node          PASSED
tests/test_enrich_node.py::test_enrich_node_basic  PASSED
tests/test_output_node.py::test_output_node_basic  PASSED
tests/test_resolve_node.py::test_resolve_node_basic PASSED
tests/test_retrieve_node.py::test_retrieve_node_minimal PASSED
tests/test_score_node.py::test_score_node_basic    PASSED
tests/test_score_node_chroma.py::test_score_node_chroma PASSED
tests/test_validate_node.py::test_validate_node    PASSED
```

---

## 📥 Input Format

The system takes a student profile JSON (`tests/fixtures/sample_student_profile.json`):

```json
{
  "student_id": "test_001",
  "name": "Anuradha Bandara",
  "education": [
    {
      "degree": "M.Tech in Computer Science",
      "institution": "Indian Institute of Technology",
      "gpa": "8.5/10",
      "graduation_year": 2024,
      "thesis": "Federated Learning for Medical Image Analysis"
    }
  ],
  "skills": ["Python", "PyTorch", "TensorFlow", "OpenCV"],
  "research_interests": [
    "federated learning",
    "medical image segmentation",
    "clinical NLP",
    "healthcare AI",
    "deep learning for medical imaging"
  ],
  "target_countries": ["USA", "Canada", "UK"],
  "target_intake": "Fall 2026",
  "publications": [],
  "raw_resume": "..."
}
```

### Key Fields

| Field | Required | Description |
|-------|----------|-------------|
| `student_id` | Yes | Unique identifier (used in output filename) |
| `research_interests` | Yes | 3–5 stated research areas |
| `target_countries` | Yes | Hard constraint — only these countries appear in output |
| `education` | Yes | Degrees, institutions, GPA |
| `target_intake` | No | Preferred start semester/year |

---

## 📤 Output Format

Output is `sample_output/{student_id}.json`. Full schema documented in [`schema.md`](schema.md).

```json
{
  "student_id": "test_001",
  "generated_at": "2026-06-12T07:01:25Z",
  "pipeline_version": "1.0.0",
  "shortlist": [
    {
      "rank": 1,
      "supervisor": {
        "name": "Dr. Example PI",
        "institution": "University of Toronto",
        "country": "Canada",
        "openalex_id": "https://openalex.org/A5073159181",
        "orcid": null
      },
      "research_focus": ["federated learning", "medical imaging", "deep learning"],
      "evidence": [
        {
          "type": "paper",
          "title": "Federated Learning for Medical Image Segmentation",
          "year": 2024,
          "doi": "https://doi.org/10.1038/s41467-024-46142-w",
          "url": "https://openalex.org/W4381799391",
          "citation_count": 120
        }
      ],
      "why_match": "Dr. Example PI at University of Toronto (Canada) works on federated learning and medical image segmentation, directly aligned with your M.Tech thesis on federated learning for medical image analysis...",
      "tier": "target",
      "confidence_score": 0.87,
      "confidence_breakdown": { "..." },
      "match_dimensions": { "country_match": true, "is_pi_verified": true }
    }
  ],
  "metadata": {
    "total_candidates_considered": 423,
    "data_sources": ["openalex", "nih_reporter"],
    "run_duration_seconds": 318.6
  }
}
```

---

## 🌐 Data Sources

| Source | Type | Coverage | API |
|--------|------|----------|-----|
| **OpenAlex** | Papers, Authors | 250M+ works globally | Free, no key required |
| **NIH Reporter** | Grants | US federal grants (NIH) | Free, no key required |
| **Semantic Scholar** | Papers | 200M+ CS/medicine papers | Free tier available |
| **Groq / LLM** | why_match generation | — | Free tier (5000 req/day) |
| **Ollama** | Fallback LLM | Local | Free, self-hosted |

---

## 🔄 Pipeline Architecture (Detail)

```
INGEST NODE
  ├─ Validates student profile schema (Pydantic)
  ├─ Expands research interests → 10–20 search queries (LLM query expansion)
  └─ Sets run_start_time, thread_id in state

RETRIEVE NODE
  ├─ Calls LangChain @tools in parallel (asyncio.gather)
  │   ├─ search_openalex(query, limit=25)   × 10 queries
  │   ├─ search_nih_grants(query, limit=20) × 10 queries
  │   └─ search_semantic_scholar(query)     × 5 queries
  ├─ Deduplicates by paper URL
  └─ Returns 400–600 raw paper/grant records

RESOLVE NODE
  ├─ Domain blacklist check (multi-word phrases, not single words)
  │   "organic synthesis" → block | "clinical AI" → pass
  ├─ Name deduplication by name|institution key
  └─ Returns resolved_candidates

VERIFY PI NODE (per candidate)
  ├─ Gate 1: Staleness — last paper > 8 years → reject
  ├─ Gate 2: Career stage — h_index < 3 AND papers < 5 → reject
  │           (only applied when we have real h_index data; 0 = unknown → pass)
  ├─ Gate 3: NIH source → auto-pass (NIH explicitly names PIs)
  └─ Sets is_pi_verified, career_stage on each candidate

CONDITIONAL EDGE (after verify_pi)
  ├─ If resolved_candidates >= 50 → proceed to SCORE
  └─ If < 50 → retry RETRIEVE (up to 5 attempts)

SCORE NODE
  ├─ ChromaDB embedding: cosine similarity (student profile ↔ paper abstract)
  ├─ Computes 6-signal confidence score
  │   topic_overlap(30%) + orcid(20%) + faculty(15%) + recency(15%)
  │                       + eligibility(10%) + h_index(10%)
  ├─ Assigns tier: reach(≥0.85) / target(≥0.65) / safety(≥0.40) / review_needed
  └─ Deduplicates by name|institution across retry loops

ENRICH NODE
  ├─ Calls why_match_chain (Groq LLM) per candidate (top 120)
  ├─ Detects stub responses ("has expertise in ,") → uses fallback generator
  └─ Adds eligibility notes per candidate

VALIDATE NODE
  ├─ Country hard constraint: known non-target countries → blocked
  │   Unknown country → allowed with country_unverified flag
  ├─ Evidence check: must have ≥1 paper or grant
  └─ Writes validated_shortlist

AUDIT NODE
  ├─ Checks top 60 for: duplicate_name, low_confidence, evidence_domain_mismatch
  └─ Flags with contamination_risk array (does NOT remove entries)

OUTPUT NODE
  ├─ Assembles final JSON (nested supervisor sub-object, evidence, why_match)
  ├─ Writes sample_output/{student_id}.json
  └─ Optionally persists to PostgreSQL (if DB available)
```

---

## 🛡️ Data Quality Safeguards

| Problem | Our Solution |
|---------|-------------|
| Same-name collisions ("Wei Wang") | 3-Signal Lock: ORCID + faculty_page + embedding similarity ≥ 0.70 |
| PhD students surfaced as PIs | Last-author heuristic + h_index gate (when data available) |
| Domain leakage ("clinical" matching chemistry) | Multi-word blacklist phrases; single words like "clinical" are NOT blocked |
| Non-target countries slipping through | Hard block at validate_node — 100% enforced |
| Rate-limit failures (Groq API) | Key pool rotation (up to 5 keys) + Ollama fallback |
| LLM stub responses | Stub detection + fallback why_match generator |

Full writeup: see [`DECISIONS.md`](DECISIONS.md)

---

## ⚖️ Design Trade-offs

### 1. Coverage vs. Precision
The assignment grades contamination heavier than coverage. We calibrate:
- **Hard** on country (100% enforced) and known junior researchers
- **Soft** on domain (keyword blacklist only, not LLM per-candidate)
- **Result:** 50–80 supervisors with low contamination risk

### 2. LLM Cost vs. Quality
Calling an LLM for each of 400+ candidates burns API keys within minutes. We limit LLM calls to:
- **Query expansion** (1 call per run)
- **why_match generation** (top 120 candidates only)
- **Domain check** — removed entirely; keyword blacklist is sufficient

### 3. OpenAlex Author API vs. Paper Authorships
The OpenAlex Author API (`/authors?search=name`) is unreliable for common names. We use paper `authorships[].institutions` directly from the paper record — much more reliable (institution linked to the specific paper, not inferred by name lookup).

---

## 🔄 Bonus: Feedback Loop

After students email supervisors, outcomes can be ingested:

```bash
python main.py feedback --csv outcomes.csv
```

**CSV format:**
```csv
student_id,supervisor_id,institution,area,sent_at,outcome
test_001,A5073159181,University Health Network,medical AI,2026-07-12,POSITIVE_REPLY
```

**Supported outcomes:** `ADMIT`, `INTERVIEW`, `POSITIVE_REPLY`, `REJECT`, `NO_REPLY`, `BOUNCE`, `WRONG_PERSON`, `NOT_RECRUITING`

The system stores outcomes in PostgreSQL and applies `outcome_weight_boost` to research areas / institutions with positive outcomes in future shortlist generations.

---

## 📊 Sample Output Statistics (test_final.json)

| Metric | Value |
|--------|-------|
| Total supervisors | 77 |
| USA | 55 |
| UK | 16 |
| Canada | 6 |
| With evidence | 77/77 |
| With why_match | 77/77 |
| With research_focus | 77/77 |
| Data sources | OpenAlex + NIH Reporter |

---

## ⚠️ Known Limitations

1. **Email addresses** — Not extracted (no reliable public API without scraping faculty pages, which violates ToS of most university sites). Students should look up emails from faculty pages linked via `profile_url`.

2. **OpenAlex author name disambiguation** — For very common names (Wei Wang, John Smith), the OpenAlex author search by name is unreliable. We use paper `authorships[].institutions` directly instead.

3. **FindAPhD eligibility parsing** — We parse country/funding from structured fields but not from free-text ad paragraphs. A student may see positions with hidden citizenship restrictions.

4. **Latency** — Full pipeline: 5–30 min depending on Groq rate limits. Fast script: ~60 seconds.

5. **Google Scholar** — No public API; rate-limited/blocked. Resolved via OpenAlex/Semantic Scholar IDs instead.

---

## 🤝 Contributing

This is a take-home assignment submission. The repository is public for evaluation purposes.

---

## 📜 License

MIT

---

*Last updated: June 2026 | Pipeline version: 1.0.0*
