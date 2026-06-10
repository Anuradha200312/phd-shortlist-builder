PhD Shortlist Builder — Delivery Notes
====================================

This README covers how to run, test, and validate the project in this workspace.

Quick setup
-----------
- Python 3.11+ recommended. Create and activate a virtualenv.
- Install core (for tests and local runs):

```bash
pip install -r requirements.txt
# Optional (for embedding/Chroma features):
pip install sentence-transformers chromadb
```

Running tests & node runners
----------------------------
This project uses lightweight script-based runners under `scripts/` (no pytest required).

- Run all node tests (examples):

```bash
python scripts/run_retrieve_node_test.py
python scripts/run_resolve_node_test.py
python scripts/run_score_node_test.py
python scripts/run_enrich_node_test.py
python scripts/run_validate_node_test.py
python scripts/run_output_node_test.py
python scripts/run_audit_node_test.py
```

FastAPI (local)
---------------
- Run the API locally with Uvicorn:

```bash
uvicorn api.app:app --reload --port 8000
```

- Endpoints of interest:
  - `GET /api/v1/health` — health check
  - `POST /api/v1/index_chroma` — accept JSON list of candidates to index (best-effort)
  - `GET /api/v1/index_status/{task_id}` — check indexing task
  - `GET /api/v1/index_status` — list recent tasks

Chroma index CLI
-----------------
- Index candidates from a JSON file (best-effort, optional):

```bash
python scripts/build_chroma_index.py sample_output/sample_candidates.json
```

Notes & fallbacks
-----------------
- The code contains safe fallbacks when optional dependencies are not installed:
  - If `chromadb` or `sentence-transformers` are missing, the system uses a deterministic overlap heuristic.
  - Database persistence (Postgres) is used only when configured; tests use monkeypatches and lazy imports.

- For production-grade runs, provide `DATABASE_URL` (Postgres) and install `chromadb` + `sentence-transformers`.

What I implemented for delivery
------------------------------
- All Phase 1–3 minimal items implemented and unit-tested.
- Phase 4 remains: polish, performance tuning, final docs and packaged Docker image.

Next suggested steps (optional)
-----------------------------
- Build Docker images and test end-to-end in docker-compose.
- Add a persistent background worker (Redis + RQ/Celery) if long-running indexing is required.
- Add more integration tests that run a small end-to-end pipeline against a test DB and sample profile.

Files added/updated for delivery
-------------------------------
- `DELIVERY_README.md` (this file)
- `scripts/build_chroma_index.py` (CLI)
- FastAPI indexing endpoints and task registry

If you want, I can proceed to implement Phase 4 items now (Docker, final e2e test, packaged README). 

CI Status
---------

![CI](https://github.com/your-org/your-repo/actions/workflows/ci.yml/badge.svg)
