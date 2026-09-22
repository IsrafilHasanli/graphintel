# Testing Strategy

GraphIntel's test suite is designed to run offline and deterministically. Local
and CI tests use SQLite, the SQL graph mirror, deterministic embeddings, and
deterministic answer/extraction fallbacks.

## Backend

Run:

```bash
pip install -e ".[dev,llm]"
pytest -q
ruff check backend scripts
```

The backend suite currently contains 50 tests covering:

| Area | Coverage |
| --- | --- |
| Configuration | production safety checks, placeholder key rejection, managed-environment requirements |
| Ingestion | CSV, JSON, text, chunking, embeddings, job state, row/file failures |
| Extraction | deterministic extraction, entity/relation parsing, unsupported kinds |
| Graph | ontology validation, traversal, filtered expansion, relation deletion, manual relation add, entity merge |
| Retrieval and answers | golden questions, citations, reasoning paths, refusal behavior, determinism |
| Evaluation | golden-question runs, release-gate PASS/FAIL behavior |
| API | health, readiness, seed/stats, ask, uploads, graph review, evaluation endpoints |
| Vector providers | deterministic, Voyage request shape, FastEmbed/Bedrock provider selection behavior |

## Frontend

Run:

```bash
cd frontend
npm install
npm run test
npm run typecheck
npm run lint
npm run build
```

Frontend coverage uses Vitest and React Testing Library for unit/component tests.
The Playwright smoke spec is available with:

```bash
npx playwright install
npm run e2e
```

The e2e run expects the frontend and backend to be running. Use `E2E_BASE_URL`
when targeting a non-default frontend URL.

## Data Validation

Run:

```bash
python scripts/prepare_demo_data.py
python scripts/validate_demo_data.py
```

The data validation path checks that the demo corpus supports the golden
questions and minimum fixture expectations.

## CI

`.github/workflows/ci.yml` runs:

- Python install
- Ruff
- demo-data preparation and validation
- pytest
- API Docker image build
- Terraform format and validation
- frontend install and tests

The workflow is intended to run without production credentials.

## Regression Guardrails

- Golden-question tests assert that expected entities and reasoning edges remain
  retrievable.
- The release gate must pass on seeded data and fail on empty data.
- Deterministic retrieval protects repeatability between cold and warm service
  instances.
- Production safety tests reject unsafe managed-environment configurations.
