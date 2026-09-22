# GraphIntel

A production-grade **Graph RAG platform for Support & Incident Intelligence**.
GraphIntel ingests support tickets, incident reports, postmortems, runbooks,
service-ownership data, and SLA documents; extracts entities and relationships
into a knowledge graph; builds a vector index over document chunks; and answers
operational questions using **hybrid graph + vector retrieval** — always with
citations, a visible reasoning path, a confidence label, and refusal when the
evidence is weak.

The local developer stack can run fully offline with zero external services:
SQLite, a SQL-backed local graph, deterministic hash embeddings, and deterministic
answer/extraction fallbacks. AWS staging/production is deliberately real:
PostgreSQL/pgvector, Amazon Neptune, real embeddings, and a real LLM provider.

## Highlights

- **Source-grounded answers only.** Every response exposes its citations
  (chunk snippets + entity nodes) and the exact graph path used to reason.
- **Graph traversal is first-class**, not an add-on: query → entity linking →
  multi-hop expansion → vector search → merge/rerank → grounded answer.
- **Correction workflows**: edit entities, merge duplicates, add/delete
  relations with ontology validation and an audit trail.
- **Evaluation built in**: a golden-question harness and a release gate
  (PASS / CONDITIONAL / FAIL) that ships as part of the product.
- **Deterministic tests, real production**: CI stays offline and reproducible;
  AWS staging/production must not use mock LLMs, hash embeddings, SQLite, or
  in-memory graph storage.

## Architecture

```
        Next.js UI  ───────────────►  FastAPI  ───────────────►  Retrieval
   (ask · graph explorer ·          (typed REST)            ┌─ QueryAnalyzer (intent, entities, time)
    entities · jobs · eval)                                 ├─ Graph expand (multi-hop, intent-scoped)
                                                            ├─ Vector search (graph-anchored + global)
   Ingestion ─► Extraction ─► Graph + Vector stores         ├─ Merge / rerank
   (jobs)       (rules/LLM)   (Neptune│SQL, pgvector│hash)   └─ Answer (citations, path, confidence, refusal)
```

- **Relational/Vector**: PostgreSQL + pgvector in production; SQLite offline.
- **Graph**: Amazon Neptune in AWS staging/production; SQL-backed graph offline.
- **Embeddings/LLM**: deterministic for local tests; Anthropic Claude for
  generation/extraction and Bedrock or Voyage for production embeddings.

## Repository layout

```
backend/app/
  api/routers/     ingestion · graph · ask · evaluation · admin
  services/        ingestion · extraction · retrieval · answer · evaluation · seed
  models.py schemas.py domain.py graph.py vector.py config.py main.py
backend/tests/     41 tests (happy + failure paths, golden regression, release gate)
frontend/          Next.js 16 · React 19 · TS · Tailwind · React Flow (8 routes)
scripts/           download_datasets · generate_synthetic_demo_data · prepare_demo_data · validate_demo_data
data/              raw/ · synthetic/ · processed/ · fixtures/ (incl. golden_questions.json)
infra/             terraform/ (ECS Fargate stack) · smoke_test.sh · README (runbook)
.github/workflows/ ci.yml (offline) · deploy.yml (no-op until configured)
docs/              architecture · dataset plan · testing · AWS deployment plan · user stories
```

## Quick start (fully offline, no external services)

```bash
pip install -e ".[dev,llm]"
python scripts/prepare_demo_data.py                 # build reproducible demo corpus
uvicorn app.main:app --app-dir backend --port 8000
```

Then, in another shell — seed and exercise the critical path:

```bash
curl -X POST http://localhost:8000/admin/seed        # load the demo knowledge graph
BASE=http://localhost:8000 bash infra/smoke_test.sh  # health → seed → ask → release gate
```

Ask a question:

```bash
curl -X POST http://localhost:8000/ask -H 'Content-Type: application/json' \
  -d '{"question":"Which engineering team owns the service involved in INC-247?"}'
```

Interactive API docs are served at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:3000 (expects the API at NEXT_PUBLIC_API_BASE)
```

Screens: dashboard, document upload, ingestion jobs, **ask** (confidence badge,
citations, reasoning path, actions, limitations), **graph explorer** (React
Flow), **entity review** (edit/merge/relations), and **evaluation**. Every data
view has loading / empty / error / success states; answers additionally render
partial-evidence and refusal states.

### Full container stack

Runs the API, web, PostgreSQL/pgvector, and Redis together:

```bash
cp .env.example .env
docker compose up -d --build
```

## API surface

| Area | Endpoints |
| --- | --- |
| Ingestion | `POST /ingest/upload`, `POST /ingest/text`, `GET /jobs`, `GET /documents`, `GET /documents/{id}/chunks` |
| Graph | `GET/PATCH /entities`, `POST /entities/merge`, `GET/POST/DELETE /relations`, `GET /graph`, `GET /graph/expand` |
| Ask | `POST /ask`, `GET /answers/{id}` |
| Evaluation | `POST /eval/run`, `GET /eval/latest`, `GET /eval/release-gate` |
| Admin/meta | `POST /admin/seed`, `GET /admin/stats`, `GET /audits`, `GET /health`, `GET /ready` |

## Demo data pipeline

`scripts/prepare_demo_data.py` attempts to download public support/incident data,
falls back to deterministic synthetic generation (logging any failed source),
and writes to `data/{raw,synthetic,processed,fixtures}`. The seed corpus supports
five **golden Graph RAG questions** used by the evaluation harness. Validate with
`python scripts/validate_demo_data.py`.

## Testing

```bash
pytest -q            # 41 backend tests
ruff check backend scripts
```

Coverage spans ingestion, extraction, graph correction, hybrid retrieval, the
five golden questions (grounding + determinism), the release gate, and the full
API contract — each with a happy path and at least one failure path. See
[`docs/testing.md`](docs/testing.md). The frontend has Vitest unit tests and a
Playwright e2e smoke spec.

## Deploy to AWS

Infrastructure-as-code (ECS Fargate + RDS/pgvector + ElastiCache Redis + S3 +
ECR + ALB + Secrets Manager + CloudWatch) and CI/CD live in `infra/` — see
[`infra/README.md`](infra/README.md) for the architecture diagram, deploy steps,
and the operations runbook (rollback, backup/restore, teardown).

> **Local development never requires AWS credentials.** Terraform validates
> offline (`terraform init -backend=false && terraform validate`) and the deploy
> workflow is a no-op until a deploy role is configured.

- **CI** (`.github/workflows/ci.yml`): ruff, pytest, demo-data validation,
  Docker build, `terraform validate`, and frontend unit tests — all offline.
- **Deploy** (`.github/workflows/deploy.yml`): build → push ECR → roll out ECS
  (with circuit-breaker auto-rollback) → smoke test, gated on a configured
  deploy role.

## Documentation

- [`docs/architecture/GRAPHINTEL_ARCHITECTURE.md`](docs/architecture/GRAPHINTEL_ARCHITECTURE.md) — technical architecture
- [`docs/DATASET_PLAN.md`](docs/DATASET_PLAN.md) — dataset acquisition & generation
- [`docs/testing.md`](docs/testing.md) — test strategy & regression guardrails
- [`docs/deployment/AWS_DEPLOYMENT_PLAN.md`](docs/deployment/AWS_DEPLOYMENT_PLAN.md) — AWS deployment plan
- [`docs/user-stories/GRAPHINTEL_USER_STORIES.md`](docs/user-stories/GRAPHINTEL_USER_STORIES.md) — product backlog
- `claude_moved/` — archived Claude Code development material; not required at runtime
