# GraphIntel Test Strategy

Testing is a product feature, not an afterthought. Every layer runs offline and
deterministically (SQLite + in-process graph + hashed embeddings + templated
answers), so the whole suite is reproducible in CI with no external services.

## Backend (pytest)

Located in `backend/tests`. Run with:

```bash
pip install -e ".[dev,llm]"
pytest -q
```

Fixtures (`conftest.py`) bind the SQLAlchemy engine to a throwaway SQLite file
before any app import, recreate the schema per test, and provide:

- `session` — empty schema + ORM session (unit tests).
- `seeded_session` — full demo corpus ingested through the real pipeline.
- `client` / `seeded_client` — FastAPI `TestClient` (empty / seeded).

Coverage by area (happy path **and** at least one failure path each, per the
Definition of Done):

| Suite | Happy path | Failure path |
| --- | --- | --- |
| `test_ingestion.py` | CSV tickets ingest, chunk, embed | malformed row recorded, empty file → failed, invalid JSON → failed |
| `test_extraction.py` | incident → entities/relations, mention linking | unknown kind → error, unknown id ignored |
| `test_graph.py` | multi-hop expand, filtered traversal, merge repoint, manual add | ontology violation rejected, double-delete no-op |
| `test_retrieval_answer.py` | 5 golden questions grounded (params) | out-of-domain refusal; cold==warm determinism |
| `test_evaluation.py` | all golden pass, gate PASS | no-data → 5 refusals → gate FAIL |
| `test_api.py` | health, seed/stats, ask, entity edit/merge, relation delete, graph expand, eval | 404s, 400 empty question, 415 bad upload, 422 ontology |

### Regression guardrails

- **Golden-question regression** (`test_retrieval_answer.py`) is parametrized
  over `data/fixtures/golden_questions.json`. Each question must be answered
  (not refused), expose citations and a graph reasoning path, surface every
  expected entity, and contain every expected reasoning edge.
- **Release gate** (`test_evaluation.py`) asserts the seeded corpus yields a
  `PASS` and an empty corpus yields a `FAIL`.
- **Determinism** — a cold service and a warm service must return identical
  chunk rankings and scores (protects the "visible, reproducible reasoning"
  product principle).

## Frontend

Vitest + React Testing Library for component/unit tests and Playwright for an
e2e smoke spec (see `frontend/`). The e2e spec expects the backend running at
`NEXT_PUBLIC_API_BASE`.

## CI

`.github/workflows/ci.yml` runs ruff, the pytest suite, a build of the API
image, and (when the frontend deps resolve) the frontend unit tests. The demo
data pipeline is validated by `scripts/validate_demo_data.py`.
