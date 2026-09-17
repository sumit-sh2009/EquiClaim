"""Postgres connection pool + LangGraph checkpointer lifecycle.

Resolves the `[VERIFY]` gap in the reference sheet: there is no single
official recipe combining FastAPI `lifespan`, `AsyncConnectionPool`, and
`AsyncPostgresSaver`. This module is the canonical EquiClaim answer:

- One `AsyncConnectionPool` is opened for the whole process lifetime and
  stored on `app.state.pool` (Starlette-official mechanism for exactly this
  kind of shared, app-lifetime resource — the bare FastAPI sample's
  module-level dict is a documentation simplification, not a constraint).
- The *same* pool backs both (a) the LangGraph `AsyncPostgresSaver` and
  (b) the application repository layer (`app/repositories/`), so we never
  run two competing pools against the same database.
- `AsyncPostgresSaver.setup()` is called exactly once at startup — this is
  what creates/migrates LangGraph's own `checkpoints` / `checkpoint_writes`
  / `checkpoint_blobs` / `checkpoint_migrations` tables. The *application*
  schema (tenants/claims/mrf_line_items/...) is migrated separately via
  `app/db/migrate.py` and never touched here.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.core.config import Settings

logger = logging.getLogger(__name__)

# Every EquiClaim Pydantic domain model that can appear inside `EquiClaimState`
# (and therefore gets msgpack-serialized into a checkpoint) must be explicitly
# allow-listed here. Without this, LangGraph's `JsonPlusSerializer` falls back
# to a permissive-with-warning mode for "unregistered" types that it says will
# be *blocked* in a future version — see the reference sheet's LangGraph
# Evaluator-Optimizer notes on `JsonPlusSerializer` / `LANGGRAPH_STRICT_MSGPACK`.
_CHECKPOINT_ALLOWED_MODULES: tuple[tuple[str, str], ...] = (
    ("app.schemas.claim", "SourceDocument"),
    ("app.schemas.claim_line_item", "ClaimLineItem"),
    ("app.schemas.denial_mapping", "DenialMapping"),
    ("app.schemas.mrf_benchmark", "MRFBenchmark"),
    ("app.schemas.compliance_finding", "ComplianceFinding"),
    ("app.schemas.audit_docket", "AuditDocket"),
    ("app.schemas.audit_docket", "LineItemFinding"),
    ("app.schemas.audit_docket", "EvaluatorCertification"),
    ("app.schemas.audit_docket", "HumanApproval"),
)


def _build_checkpoint_serializer() -> JsonPlusSerializer:
    return JsonPlusSerializer(allowed_msgpack_modules=_CHECKPOINT_ALLOWED_MODULES)


@dataclass
class DatabaseResources:
    """Bundled handles created at startup and torn down at shutdown."""

    pool: AsyncConnectionPool
    checkpointer: AsyncPostgresSaver


@asynccontextmanager
async def open_database_resources(settings: Settings) -> AsyncIterator[DatabaseResources]:
    """Open the shared pool + checkpointer; guarantees clean shutdown.

    Intended to be driven from the FastAPI `lifespan` context manager (see
    `app/main.py`), but is a standalone async context manager so it can also
    be used directly in scripts/tests without spinning up FastAPI.
    """
    pool = AsyncConnectionPool(
        conninfo=settings.database_url,
        min_size=settings.db_pool_min_size,
        max_size=settings.db_pool_max_size,
        kwargs={"autocommit": True, "row_factory": dict_row},
        open=False,
    )
    await pool.open()
    logger.info(
        "opened AsyncConnectionPool (min=%s, max=%s)",
        settings.db_pool_min_size,
        settings.db_pool_max_size,
    )

    checkpointer = AsyncPostgresSaver(pool, serde=_build_checkpoint_serializer())
    await checkpointer.setup()
    logger.info("AsyncPostgresSaver.setup() complete (checkpoint tables ready)")

    try:
        yield DatabaseResources(pool=pool, checkpointer=checkpointer)
    finally:
        await pool.close()
        logger.info("closed AsyncConnectionPool")
