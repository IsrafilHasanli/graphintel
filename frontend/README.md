# GraphIntel Frontend

Operational UI for the GraphIntel Graph RAG platform (support & incident
intelligence). Built with Next.js 16 (App Router), React 19, TypeScript, Tailwind,
and React Flow.

## Screens

| Route         | Purpose                                                                 |
| ------------- | ----------------------------------------------------------------------- |
| `/`           | Dashboard: corpus/graph counts, entity coverage, release-gate, seed.    |
| `/ask`        | Ask a question; answer + confidence + citations + reasoning path.       |
| `/graph`      | Interactive React Flow graph explorer (browse or expand from a seed).   |
| `/entities`   | Entity review: edit, merge, inspect relations, add/delete relations.    |
| `/upload`     | Upload a file or paste text; shows the resulting ingestion job.         |
| `/jobs`       | Ingestion jobs list with state badges and per-job error drill-down.     |
| `/evaluation` | Run golden-question evals, view metrics and the release gate.           |

## Prerequisites

- Node.js 20+
- The GraphIntel FastAPI backend running and reachable at
  `NEXT_PUBLIC_API_BASE` (default `http://localhost:8000`).

## Configuration

`NEXT_PUBLIC_API_BASE` sets the backend base URL. It is inlined at build time,
so rebuild after changing it.

```bash
cp .env.local.example .env.local   # optional; edit if backend is elsewhere
```

## Run locally

```bash
npm install
npm run dev            # http://localhost:3000
```

The dashboard is the landing screen. If you see empty states, click
**Seed demo data** (POST `/admin/seed`) to load the deterministic demo corpus,
then try the golden questions on `/ask`.

## Scripts

```bash
npm run dev        # dev server
npm run build      # production build (Next standalone output)
npm run start      # serve the production build
npm run lint       # ESLint 9 flat config with Next core-web-vitals
npm run typecheck  # tsc --noEmit
npm run test       # Vitest unit/component tests
npm run e2e        # Playwright smoke tests (needs the app + backend running)
```

### Playwright

```bash
npx playwright install    # one-time browser download
npm run start &           # or: npm run dev &
npm run e2e
```

Set `E2E_BASE_URL` to target a non-default frontend URL.

## Docker

Multi-stage build (node:20-alpine) using Next.js standalone output.

```bash
docker build \
  --build-arg NEXT_PUBLIC_API_BASE=http://localhost:8000 \
  -t graphintel-frontend .
docker run -p 3000:3000 graphintel-frontend
```

The repository `docker-compose.yml` builds this directory as the `web` service.

## Architecture notes

- `lib/api.ts` — single typed fetch wrapper; reads `NEXT_PUBLIC_API_BASE`,
  builds URLs (array params repeat keys for `/graph/expand?seed=`), and throws
  a typed `ApiError` carrying HTTP status + parsed body (used to surface 422
  ontology violations).
- `lib/types.ts` — TypeScript types mirroring the backend contract.
- `lib/useAsync.ts` — abortable data-loading hook powering loading/empty/error
  states across every data view.
- `components/ui/*` — small Tailwind design system (Badge, Card, Button, Table,
  Field, Modal, StateView).
- Accessibility: semantic landmarks, labelled controls, keyboard-operable rows
  and dialogs, `aria-live` regions for async answers/results, visible focus
  rings, and a skip-to-content link.

## UI states

Every data view implements loading, empty, error, and success states via
`AsyncView`. The Ask answer additionally renders partial-evidence (limitations)
and insufficient-evidence (refusal, red styling) states distinctly.
