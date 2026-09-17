"""Lightweight, dependency-free SQL migration runner for the *application*
schema (tenants/hospitals/mrf_line_items/claims/claim_documents/audit_dockets).

This intentionally does NOT touch LangGraph's own checkpoint tables — those
are created exclusively by `AsyncPostgresSaver.setup()` (see `app/db/pool.py`).

Usage:
    uv run python -m app.db.migrate
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import psycopg

from app.core.config import get_settings

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"

_ENSURE_MIGRATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    filename    TEXT PRIMARY KEY,
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


async def run_migrations(database_url: str | None = None) -> list[str]:
    """Apply every `*.sql` file in `migrations/` not yet recorded as applied.

    Returns the list of filenames that were newly applied (empty if the
    schema was already up to date). Idempotent — safe to call on every
    application startup.
    """
    database_url = database_url or get_settings().database_url
    applied: list[str] = []

    async with await psycopg.AsyncConnection.connect(database_url, autocommit=True) as conn:
        async with conn.cursor() as cur:
            await cur.execute(_ENSURE_MIGRATIONS_TABLE)
            await cur.execute("SELECT filename FROM schema_migrations")
            rows = await cur.fetchall()
            already_applied = {row[0] for row in rows}

        for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if sql_file.name in already_applied:
                continue
            sql = sql_file.read_text()
            async with conn.cursor() as cur:
                await cur.execute(sql)
                await cur.execute(
                    "INSERT INTO schema_migrations (filename) VALUES (%s)",
                    (sql_file.name,),
                )
            logger.info("applied migration %s", sql_file.name)
            applied.append(sql_file.name)

    return applied


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    applied = asyncio.run(run_migrations())
    if applied:
        print(f"Applied {len(applied)} migration(s): {', '.join(applied)}")
    else:
        print("Schema already up to date.")


if __name__ == "__main__":
    main()
