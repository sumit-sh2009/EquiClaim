# EquiClaim

Asynchronous, multi-agent forensic audit engine for hospital bills. EquiClaim
ingests a patient's bill + EOB, benchmarks billed amounts against CMS
Hospital Price Transparency (MRF) data, audits them against No Surprises Act
(45 CFR § 149) and NCCI invariants via a LangGraph evaluator-optimizer loop,
pauses for human-in-the-loop review, and emits a statute-cited **Audit
Docket** + formal dispute notice.

The architecture lives in this repository: data contracts in `backend/app/schemas/`,
shared graph state in `backend/app/graph/state.py`, and the agent topology in
`backend/app/graph/graph.py`.

## Stack

| Tier | Technology |
|---|---|
| Frontend | React 19, Vite, Tailwind CSS 4, shadcn/ui (Base UI), React Hook Form + Zod, TanStack Query + Table, react-dropzone, Sonner, lucide-react, motion, React Router |
| API | FastAPI, Pydantic v2, uvicorn |
| Agents | LangGraph (`StateGraph`, evaluator-optimizer reflection loop, `interrupt_before` HITL) |
| Persistence | PostgreSQL — `psycopg_pool.AsyncConnectionPool` + `langgraph-checkpoint-postgres` (`AsyncPostgresSaver`) |
| Tooling | `uv` (backend), `npm` (frontend), `ruff`/`mypy`/`pytest` (backend), `oxlint`/`tsc` (frontend) |

## Repository layout

```
backend/            FastAPI + LangGraph service (uv-managed)
  app/
    core/           settings, security (tenant auth), structured logging
    schemas/        Pydantic v2 data contracts (cents-integer, model_validators)
    domain/         CARC/RARC, CPT/HCPCS, NCCI, statutory citation allow-lists
    graph/          EquiClaimState, reducers, agent nodes, compiled StateGraph
    repositories/   Postgres data access (claims, MRF, tenant API keys)
    routers/        /claims API (upload, status, resume, docket)
    services/       document parsing, dispute-notice templating, graph runner
  migrations/       hand-rolled SQL for the application schema
  fixtures/         sample bill/EOB/MRF data used by tests
  tests/            pytest (schemas, graph pipeline, evaluator, API, security)
frontend/           Vite + React + TypeScript SPA
  src/
    api/            axios client
    lib/            cn() (clsx + tailwind-merge), Zod schemas (CCN, intake, review)
    hooks/          TanStack Query hooks (polling with backoff)
    components/     ui/ (shadcn + acid primitives), site/ (header, footer, annotated bill),
                    StatusBadge, Money, ReviewPanel, DocketViewer
    pages/          LandingPage, UploadPage (RHF + dropzone wizard), LedgerPage
                    (TanStack Table), ClaimDetailPage
docker-compose.yml           local dev stack (Postgres + backend + frontend, hot reload)
docker-compose.prod.yml      production overlay (immutable images, nginx-served SPA)
```

## Local development

```bash
cp .env.example backend/.env      # adjust DATABASE_URL / secrets as needed
cp .env.example frontend/.env     # VITE_API_BASE_URL / VITE_API_BEARER_TOKEN / VITE_TENANT_ID

cd backend && uv sync && uv run uvicorn app.main:app --reload
cd frontend && npm install && npm run dev
```

Or via Docker Compose (Postgres + backend + frontend, all hot-reloading):

```bash
docker compose up --build
```

- Backend: http://localhost:8000 (`/healthz`, OpenAPI docs at `/docs`)
- Frontend: http://localhost:5173

In `development` and `test`, startup loads `backend/fixtures/example_mrf_tall.csv`
for hospital CCN `450123` when that hospital has no price file yet. The upload
page's **Load sample bill & EOB** uses the same CCN, so a fresh database can
run the sample audit without a manual ingest. Other CCNs return `400` until
their CMS file is loaded with `python -m app.ingestion.mrf_ingest`.

## Frontend design system

The interface is **neo-brutalist acid**, specified in
[`docs/design-system.md`](docs/design-system.md). Paper
`#F8F4E8`, ink `#09090B`, acid `#D2E823`. Elevation is a solid offset shadow,
never a blur. Interactive elements carry a 2px ink border. Radius stays at or
under 32px (buttons 12px).

- **Typography** — Dela Gothic One for display and uppercase headings. Space
  Grotesk for body. IBM Plex Mono for claim IDs, CPT codes, citations, and
  money. Amounts use tabular figures.
- **Color** — acid is the only accent: primary buttons, disputed amounts, the
  authority band, and the footer submit. Night mode inverts paper and ink
  and keeps acid. A 3% noise overlay sits on the page. A mix-blend cursor
  scales over links and buttons.
- **Motion** — display words rise in on load, the sample statement’s scan
  tracks scroll through three beats (read, price, cite), and the audit trail
  draws a vertical rule. `prefers-reduced-motion` prints the text and skips
  the pin.
- **Landing** (`/`) — a pinned exhibit beside the annotated sample statement
  (CARC 45, NCCI PTP, NSA), a labeled list of the authorities it can cite,
  one large ruling plus three notes, and a vertical audit trail.
- **Upload** (`/upload`) — three steps (hospital, documents, review) validated
  with React Hook Form + Zod. Files are `.json` or `.txt` via react-dropzone.
- **Ledger** (`/claims`) — TanStack Table with sort, live filter, and empty
  and error states.
- **Claim detail** (`/claims/:id`) — billed vs. disputed figures, findings,
  the dispute notice, and the certification trail. Human review confirms
  through an alert dialog.
- **Accessibility** — skip link, landmarks, `aria-current` on the stepper,
  visible focus rings, and reduced-motion support.

## Tests & linting

```bash
cd backend
uv run pytest       # schemas, graph pipeline (pause/resume), evaluator invariants, API, tenant auth
uv run ruff check .
uv run mypy app

cd frontend
npm run build        # tsc -b && vite build
npm run lint          # oxlint
```

Backend tests require a reachable Postgres (see `EQUICLAIM_DATABASE_URL` in
`backend/.env`); `app/db/migrate.py` applies the application schema
automatically and `AsyncPostgresSaver.setup()` owns the LangGraph checkpoint
tables.

## Authentication & tenant isolation

Every `/claims` request must present `Authorization: Bearer <token>`:

- **Local/dev/test** (`EQUICLAIM_ENVIRONMENT=development|test`): the shared
  secret in `EQUICLAIM_API_SHARED_SECRET` plus an explicit `X-Tenant-Id`
  header. This path is refused in any other environment.
- **Production**: a per-tenant API key, hashed with HMAC-SHA256 and a server
  pepper (`EQUICLAIM_API_KEY_PEPPER`), looked up in
  `tenant_api_keys` (`app/repositories/tenant_keys_repository.py`) — leaking
  or rotating one tenant's key never affects another tenant.

All claim/status/resume/docket queries are scoped by `tenant_id` at the
repository layer (`ClaimsRepository.get_claim(..., tenant_id=...)`), so a
cross-tenant request gets a `404` (not a `403`) and cannot even confirm a
claim id exists. See `backend/tests/test_security.py`.

## Deployment

`docker-compose.prod.yml` layers on top of the base file for a
production-shaped deployment: immutable images (no bind mounts), the backend
run without `--reload`, and the frontend built to static assets and served
by nginx (`frontend/Dockerfile`'s `prod` stage) instead of the Vite dev
server.

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Secrets (`EQUICLAIM_DATABASE_URL`, `EQUICLAIM_API_SHARED_SECRET`,
`EQUICLAIM_API_KEY_PEPPER`, tenant API keys) should come from the deployment environment (an `--env-file`, or a
secrets manager) — nothing sensitive is baked into either image. `backend/
Dockerfile` bakes in a `/healthz` `HEALTHCHECK`; `frontend/Dockerfile`'s prod
image exposes the same at `/healthz` via nginx.

Structured access logs (`app/core/logging.py`) tag every request with a
correlation id (`X-Request-Id`, generated if absent and echoed back),
resolved `tenant_id`, status code, and latency — safe to pipe into any log
aggregator without an extra JSON-logging dependency.
