# GraphIntel Frontend

The GraphIntel frontend is a Next.js application for support and incident
intelligence workflows. It provides dashboards, question answering, graph
exploration, ingestion views, entity review, and evaluation screens.

## Stack

- Next.js 16 App Router
- React 19
- TypeScript
- Tailwind CSS
- React Flow
- Vitest and React Testing Library
- Playwright smoke tests

## Routes

| Route | Purpose |
| --- | --- |
| `/` | Dashboard with corpus metrics, graph counts, release-gate status, and seed action |
| `/ask` | Ask operational questions and inspect confidence, citations, reasoning path, actions, and limitations |
| `/graph` | Explore or expand graph neighborhoods from seed entities |
| `/entities` | Review, edit, merge, and correct entities and relations |
| `/upload` | Upload files or paste text for ingestion |
| `/jobs` | Inspect ingestion job state and per-job errors |
| `/evaluation` | Run golden-question evaluations and review release-gate status |

## Configuration

`NEXT_PUBLIC_API_BASE` defines the backend API base URL. The value is inlined at
build time.

```bash
cp .env.local.example .env.local
```

The default backend URL is `http://localhost:8000`.

## Development

```bash
npm install
npm run dev
```

Open `http://localhost:3000`. Start the backend first, then seed demo data from
the dashboard or with `POST /admin/seed`.

## Scripts

| Command | Description |
| --- | --- |
| `npm run dev` | Start the development server |
| `npm run build` | Create a production build |
| `npm run start` | Serve the production build |
| `npm run lint` | Run ESLint 9 flat config with Next core-web-vitals |
| `npm run typecheck` | Run TypeScript without emitting files |
| `npm run test` | Run Vitest unit/component tests |
| `npm run e2e` | Run Playwright smoke tests |

## Docker

```bash
docker build \
  --build-arg NEXT_PUBLIC_API_BASE=http://localhost:8000 \
  -t graphintel-frontend .

docker run -p 3000:3000 graphintel-frontend
```

The repository-level `docker-compose.yml` builds this app as the `web` service.

## Code Organization

| Path | Purpose |
| --- | --- |
| `app/` | Route-level screens |
| `components/` | Product and shared UI components |
| `components/ui/` | Small Tailwind UI primitives |
| `lib/api.ts` | Typed API client and error handling |
| `lib/types.ts` | Types mirroring backend API contracts |
| `lib/useAsync.ts` | Abortable async loading hook |
| `tests/unit/` | Component and API-client unit tests |
| `e2e/` | Playwright smoke spec |

## UX Expectations

Every data view should provide loading, empty, error, and success states. Answer
views should clearly distinguish grounded answers, partial evidence, and
insufficient evidence/refusal states.
