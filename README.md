# 🎓 PhD Shortlist Builder

An AI-powered system that helps students find matching PhD supervisors and programs. Built using **LangChain**, **LangGraph**, and **FastAPI** to retrieve, filter, and score potential advisors based on research interests and academic history.

---

## 📖 What This Project Does

When applying for a PhD, finding the right supervisor (Professor / Principal Investigator) is one of the most critical steps. Typically, students have to manually search through university faculty directories, publication indexes, and grant websites to check if a supervisor:
1. Works in their exact domain of interest.
2. Is active (has published papers recently).
3. Has research funding (grants) to support PhD students.
4. Is located in their desired country.

**PhD Shortlist Builder** automates this entire process. It takes a student's academic profile (GPA, publications, target countries, research interests) and outputs a personalized, ranked list of matching supervisors complete with direct links to their papers, active grants, and eligibility details.

---

## 🔄 Project Workflow (Step-by-Step)

The pipeline runs as a **LangGraph state machine** (a structured flow where data passes from node to node):

```
[Student Profile] 
       │
       ▼
1. Ingest Node (LLM expands student's interests into search keywords)
       │
       ▼
2. Retrieve Node (Searches Semantic Scholar, OpenAlex, NIH Reporter, and UKRI)
       │
       ▼
3. Resolve Node (Disambiguates authors and filters out wrong domains)
       │
       ▼
4. Verify PI Node (Confirms target country eligibility and active academic status)
       │
       ▼
5. Score Node (Computes embedding similarities and assigns Reach/Target/Safety tiers)
       │
       ▼
6. Enrich Node (LLM writes a custom "why_match" explanation per candidate)
       │
       ▼
7. Validate Node (Asserts data schema compliance and checks constraints)
       │
       ▼
8. Audit Node (Audits the top 30 candidates for high confidence and quality)
       │
       ▼
9. Output Node (Saves results to the database and exports a JSON shortlist)
```

---

## 📥 Input and Output

### 1. System Input
The system accepts a **Student Profile** in JSON format.
**Example (`student_profile.json`):**
```json
{
  "student_id": "student_001",
  "education": [
    {
      "degree": "M.S. in Computer Science",
      "institution": "Stanford University",
      "gpa": "3.9/4.0",
      "graduation_year": 2024
    }
  ],
  "skills": ["Python", "PyTorch", "Medical Imaging"],
  "research_interests": ["medical image segmentation", "federated learning"],
  "target_countries": ["USA", "UK", "Canada"]
}
```

### 2. System Output
The system outputs a detailed **Shortlist JSON** containing ranked supervisors, matching metrics, and links to papers or grants.
**Example (`sample_output/student_001.json`):**
```json
{
  "student_id": "student_001",
  "generated_at": "2026-06-11T05:24:31Z",
  "shortlist": [
    {
      "rank": 1,
      "supervisor": {
        "name": "Dr. Jane Smith",
        "institution": "Harvard University",
        "country": "USA",
        "profile_url": "https://...",
        "orcid": "0000-0002-1825-0097"
      },
      "research_focus": ["medical image segmentation", "federated learning"],
      "why_match": "Dr. Smith's recent publication on federated segmentation of MRI scans directly aligns with your master's thesis work.",
      "tier": "target",
      "confidence_score": 0.92,
      "evidence": [
        {
          "type": "paper",
          "title": "Federated Learning for Medical Image Segmentation",
          "venue": "IEEE TMI",
          "year": 2024,
          "url": "https://doi.org/10.1109/TMI.2024.123456"
        }
      ]
    }
  ]
}
```

---

## 🛠️ Main Modules and Their Purpose

- 🌐 **`api`**: Houses the FastAPI web server. Defines HTTP endpoints to run the builder and register feedback.
- ⛓️ **`chains`**: Individual LangChain LLM prompts and pipelines (e.g. query expansion, generating matching reasons, classifying research domains).
- 🗄️ **`db`**: Database configuration, SQLAlchemy models, and helper functions (CRUD) to interact with the PostgreSQL database.
- 🔍 **`data_sources`**: API clients that connect to academic data sources (OpenAlex, Semantic Scholar, NIH Reporter, and UKRI Gateway).
- 🕸️ **`graph`**: The LangGraph state machine orchestrator that defines how data moves between steps (Nodes) and the branching logic (Edges).
- 🎯 **`scoring`**: Code that computes similarity scores and assigns Reach, Target, or Safety labels based on the student's background.
- ⚙️ **`llm`**: Setup logic for LLMs, including multi-provider rate-limiting fallbacks.

---

## 🧠 How the Code Works Internally

1. **Multi-Tier LLM Resilience**:
   When invoking AI models, the project uses a fallback chain (`ChatGroq` with `with_fallbacks`). If the primary high-power model (`llama-3.3-70b-versatile`) hits rate limits, it automatically falls back to `llama-3.1-8b-instant`, then `mixtral-8x7b-32768`, and finally to local `Ollama` if available.
2. **Entity Disambiguation (3-Signal Lock)**:
   Author names can conflict. The system resolves this by requiring validation from at least 2 of 3 signals: (1) Verified ORCID ID, (2) Active affiliation on faculty directories, (3) High semantic similarity (>0.70) between publications and student profile interests.
3. **Closing the Feedback Loop**:
   If a user uploads past application outcomes (e.g. who was admitted, interviewed, or rejected), the system records this in PostgreSQL. Next time a shortlist is generated, the scoring algorithm applies a weight boost to research areas or universities that yielded positive outcomes.

---

## 🚀 Setup and Installation

### Prerequisites
- [Python 3.11+](https://www.python.org/downloads/)
- [Docker & Docker Compose](https://www.docker.com/products/docker-desktop/) (to run database and fallback services)
- [Groq API Key](https://console.groq.com/) (free tier available)

### Installation Steps

1. **Clone the Repository**:
   ```bash
   git clone <repo-url>
   cd phd-shortlist-builder
   ```

2. **Set Up the Virtual Environment**:
   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   python -m pip install -e .
   ```

4. **Configure Environment Variables**:
   Create a file named `.env` in the root folder and add your Groq API key:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   ```

5. **Start PostgreSQL**:
   ```bash
   docker compose up -d postgres
   ```

6. **Initialize Database Tables**:
   ```bash
   python scripts/init_db_tables.py
   ```

---

## 💻 Commands to Run the Project

### 1. Run via CLI (Single Command)
Generate a shortlist for a student profile:
```bash
python main.py run --profile tests/fixtures/sample_student_profile.json
```

### 2. Run the FastAPI Web Server
Start the HTTP server:
```bash
python -m uvicorn api.app:app --host 127.0.0.1 --port 8000 --reload
```
- **Interactive Swagger Docs**: View and test API endpoints at `http://127.0.0.1:8000/docs`.
- **Health Check**: `http://127.0.0.1:8000/api/v1/health`
- **Feedback Ingestion**: Upload outcomes CSV via `POST /api/v1/feedback`.

---

## 🧪 How to Test the Project

We use **pytest** for testing. Run the following command to execute the test suite:
```bash
python -m pytest
```

---

## 📂 Folder Structure

```
phd-shortlist-builder/
│
├── api/                    # FastAPI web server and routes
├── chains/                 # LangChain LLM prompts and pipelines
├── config/                 # Pydantic Settings & logger setups
├── data_sources/           # API wrapper clients (Semantic Scholar, OpenAlex, etc.)
├── db/                     # SQLAlchemy models and database CRUD operations
├── feedback/               # Outcomes CSV parsing and feedback analysis logic
├── graph/                  # LangGraph nodes, state, and routing edges
├── llm/                    # Provider configurations and fallback router
├── scoring/                # Scoring algorithms and tier classifications
├── tests/                  # Pytest unit tests and test fixtures
│
├── Dockerfile              # Docker container setup
├── docker-compose.yml      # Service manager (PostgreSQL, Ollama)
├── pyproject.toml          # Project metadata and dependencies
├── main.py                 # Typer CLI entry point
└── .env                    # Local environment secrets configuration
```

---

## 📝 Missing or Incomplete Features

- **Google Scholar Scraping**: Google Scholar lacks a public API and is heavily rate-limited/cap-blocked. Author profiles are resolved best-effort via OpenAlex and Semantic Scholar identifiers instead.
- **Alembic Database Migrations**: Alembic is configured, but future schema upgrades will require creating migrations via `alembic revision --autogenerate`.
