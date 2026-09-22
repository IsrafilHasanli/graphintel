# Contributing

Thank you for your interest in GraphIntel. This project is currently maintained
as a public reference implementation for Graph RAG support and incident
intelligence.

## Development Setup

```bash
pip install -e ".[dev,llm]"
python scripts/prepare_demo_data.py
pytest -q
ruff check backend scripts
```

Frontend checks:

```bash
cd frontend
npm install
npm run test
npm run typecheck
npm run lint
npm run build
```

## Pull Request Checklist

- Keep changes focused and explain the motivation.
- Preserve deterministic local behavior.
- Do not commit `.env`, Terraform state, local databases, generated corpora, or
  dependency/build folders.
- Add or update tests for behavior changes.
- Update documentation when public commands, configuration, architecture, or
  deployment behavior changes.
- Do not introduce new external services unless they are required by the
  architecture and documented.

## Code Style

- Backend code should follow the existing FastAPI/service/module structure.
- Prefer environment-driven configuration through `backend/app/config.py`.
- Keep local tests independent from production credentials and external cloud
  services.
- Frontend components should provide loading, empty, error, and success states
  for data-driven views.

## Data Policy

Only commit small stable fixtures. Generated raw, synthetic, and processed data
should be reproduced with scripts and remain ignored by Git.
