"""Shared pytest fixtures for DB-backed integration tests.

These tests talk to a real Postgres instance (see `backend/.env` /
`docker-compose.yml`) — they are the Phase 1 gate proving the
`AsyncPostgresSaver` + `interrupt_before` pause/resume mechanics actually
work end-to-end, and are reused by later phases to exercise the real node
logic against real checkpointed state.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.core.config import get_settings
from app.db.migrate import run_migrations
from app.db.pool import _build_checkpoint_serializer
from app.graph.graph import compile_graph


@pytest_asyncio.fixture
async def pool() -> AsyncIterator[AsyncConnectionPool]:
    settings = get_settings()
    await run_migrations(settings.database_url)
    async with AsyncConnectionPool(
        conninfo=settings.database_url,
        min_size=1,
        max_size=5,
        kwargs={"autocommit": True, "row_factory": dict_row},
    ) as p:
        yield p


@pytest_asyncio.fixture
async def graph(pool: AsyncConnectionPool):
    settings = get_settings()
    checkpointer = AsyncPostgresSaver(pool, serde=_build_checkpoint_serializer())
    await checkpointer.setup()
    return compile_graph(pool=pool, checkpointer=checkpointer, settings=settings)


@pytest.fixture
def settings():
    return get_settings()
