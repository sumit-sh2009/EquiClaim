"""Repository for `tenant_api_keys` (Phase 8 hardening)."""

from __future__ import annotations

import uuid

from psycopg_pool import AsyncConnectionPool


class TenantApiKeyRepository:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def resolve_tenant_for_key(self, key_hash: str) -> str | None:
        async with self._pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                SELECT tenant_id FROM tenant_api_keys
                WHERE key_hash = %(hash)s AND revoked_at IS NULL
                """,
                {"hash": key_hash},
            )
            row = await cur.fetchone()
            return row["tenant_id"] if row else None

    async def issue_key(self, *, tenant_id: str, key_hash: str) -> str:
        key_id = str(uuid.uuid4())
        async with self._pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO tenant_api_keys (key_id, tenant_id, key_hash)
                VALUES (%(key_id)s, %(tenant_id)s, %(hash)s)
                """,
                {"key_id": key_id, "tenant_id": tenant_id, "hash": key_hash},
            )
        return key_id

    async def revoke_key(self, *, key_id: str) -> None:
        async with self._pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                "UPDATE tenant_api_keys SET revoked_at = now() WHERE key_id = %(key_id)s",
                {"key_id": key_id},
            )
