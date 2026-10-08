"""FastAPI application factory + lifespan wiring.

See `app/db/pool.py` for the rationale behind storing the pool/checkpointer/
compiled graph on `app.state` rather than a bare module-level dict.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings, refuse_default_secrets
from app.core.logging import RequestContextMiddleware, configure_logging
from app.db.migrate import run_migrations
from app.db.pool import open_database_resources
from app.graph.graph import compile_graph
from app.ingestion.mrf_ingest import seed_demo_hospital_if_missing
from app.repositories.claims_repository import ClaimsRepository
from app.routers import claims

logger = logging.getLogger(__name__)

# JSON responses never need a browser document policy. The SPA's CSP lives on nginx.
_API_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    "Cache-Control": "no-store",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    refuse_default_secrets(settings)

    # Application schema (tenants/claims/mrf_line_items/...) — separate from,
    # and applied before, the LangGraph checkpoint tables.
    applied = await run_migrations(settings.database_url)
    if applied:
        logger.info("applied application migrations: %s", applied)

    async with open_database_resources(settings) as resources:
        app.state.settings = settings
        app.state.pool = resources.pool
        app.state.checkpointer = resources.checkpointer
        app.state.graph = compile_graph(
            pool=resources.pool, checkpointer=resources.checkpointer, settings=settings
        )
        if settings.environment in ("development", "test"):
            await seed_demo_hospital_if_missing(resources.pool)
        orphaned = await ClaimsRepository(resources.pool).fail_orphaned_runs()
        if orphaned:
            logger.warning("marked %d in-flight claims FAILED after restart", orphaned)
        logger.info(
            "EquiClaim backend ready (environment=%s, evaluator_max_iterations=%d)",
            settings.environment,
            settings.evaluator_max_iterations,
        )
        yield


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(environment=settings.environment)
    publish_docs = settings.environment in {"development", "test"}
    app = FastAPI(
        title="EquiClaim",
        description=(
            "Asynchronous, multi-agent forensic audit engine for medical bills, "
            "EOBs, and No Surprises Act / NCCI compliance."
        ),
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if publish_docs else None,
        redoc_url="/redoc" if publish_docs else None,
        openapi_url="/openapi.json" if publish_docs else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Tenant-Id", "X-Request-Id"],
    )
    app.add_middleware(RequestContextMiddleware)

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):  # noqa: ARG001
        response = await call_next(request)
        response.headers.update(_API_SECURITY_HEADERS)
        return response

    app.include_router(claims.router)

    @app.get("/healthz", tags=["ops"])
    async def healthz(request: Request) -> dict[str, str]:
        """Liveness/readiness probe — proves the shared pool is actually usable."""
        pool = request.app.state.pool
        async with pool.connection() as conn, conn.cursor() as cur:
            await cur.execute("SELECT 1")
            await cur.fetchone()
        return {"status": "ok"}

    return app


app = create_app()
