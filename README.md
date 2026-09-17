# EquiClaim

Asynchronous, multi-agent forensic audit engine for hospital bills. EquiClaim
ingests a patient's bill + EOB, benchmarks billed amounts against CMS
Hospital Price Transparency (MRF) data, audits them against No Surprises Act
(45 CFR § 149) and NCCI invariants via a LangGraph evaluator-optimizer loop,
pauses for human-in-the-loop review, and emits a statute-cited **Audit
Docket** + formal dispute notice.

See [`.cursor/plans/equiclaim_architecture_blueprint_d34b3966.plan.md`](.cursor/plans/equiclaim_architecture_blueprint_d34b3966.plan.md)
for the full architectural blueprint (system topology, data contracts,
`EquiClaimState` design, agent graph invariants, and phased implementation
plan this repo was built against).

## Stack

| Tier | Technology |
|---|---|
| Frontend | React 19, Vite, Tailwind CSS 4, TanStack Query, React Router |
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
    hooks/          TanStack Query hooks (polling with backoff)
    components/     StatusBadge, Money, ReviewPanel, DocketViewer
    pages/          UploadPage, LedgerPage, ClaimDetailPage
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
- **Production**: a per-tenant API key, hashed with SHA-256 and looked up in
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

Secrets (`EQUICLAIM_DATABASE_URL`, `EQUICLAIM_API_SHARED_SECRET`, tenant API
keys) should come from the deployment environment (an `--env-file`, or a
secrets manager) — nothing sensitive is baked into either image. `backend/
Dockerfile` bakes in a `/healthz` `HEALTHCHECK`; `frontend/Dockerfile`'s prod
image exposes the same at `/healthz` via nginx.

Structured access logs (`app/core/logging.py`) tag every request with a
correlation id (`X-Request-Id`, generated if absent and echoed back),
resolved `tenant_id`, status code, and latency — safe to pipe into any log
aggregator without an extra JSON-logging dependency.
