"""Repository layer for `tenants` / `claims` / `claim_documents` / `audit_dockets`."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from psycopg_pool import AsyncConnectionPool

from app.schemas.audit_docket import AuditDocket
from app.schemas.claim import ClaimStatus


@dataclass
class ClaimRow:
    claim_id: str
    tenant_id: str
    thread_id: str
    hospital_ccn: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class ClaimsRepository:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def ensure_tenant(self, *, tenant_id: str, name: str | None = None) -> None:
        async with self._pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO tenants (tenant_id, name) VALUES (%(id)s, %(name)s)
                ON CONFLICT (tenant_id) DO NOTHING
                """,
                {"id": tenant_id, "name": name or tenant_id},
            )

    async def create_claim(
        self, *, claim_id: str, tenant_id: str, thread_id: str, hospital_ccn: str | None
    ) -> ClaimRow:
        async with self._pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO claims (claim_id, tenant_id, thread_id, hospital_ccn, status)
                VALUES (%(claim_id)s, %(tenant_id)s, %(thread_id)s, %(hospital_ccn)s, 'INTAKE')
                RETURNING claim_id, tenant_id, thread_id, hospital_ccn, status, created_at, updated_at
                """,
                {
                    "claim_id": claim_id,
                    "tenant_id": tenant_id,
                    "thread_id": thread_id,
                    "hospital_ccn": hospital_ccn,
                },
            )
            row = await cur.fetchone()
            return ClaimRow(**row)

    async def get_claim(self, *, claim_id: str, tenant_id: str) -> ClaimRow | None:
        async with self._pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                SELECT claim_id, tenant_id, thread_id, hospital_ccn, status, created_at, updated_at
                FROM claims WHERE claim_id = %(claim_id)s AND tenant_id = %(tenant_id)s
                """,
                {"claim_id": claim_id, "tenant_id": tenant_id},
            )
            row = await cur.fetchone()
            return ClaimRow(**row) if row else None

    async def list_claims(self, *, tenant_id: str, limit: int = 50) -> list[ClaimRow]:
        async with self._pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                SELECT claim_id, tenant_id, thread_id, hospital_ccn, status, created_at, updated_at
                FROM claims WHERE tenant_id = %(tenant_id)s
                ORDER BY created_at DESC LIMIT %(limit)s
                """,
                {"tenant_id": tenant_id, "limit": limit},
            )
            rows = await cur.fetchall()
            return [ClaimRow(**row) for row in rows]

    async def update_status(self, *, claim_id: str, status: ClaimStatus) -> None:
        async with self._pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                "UPDATE claims SET status = %(status)s, updated_at = now() WHERE claim_id = %(claim_id)s",
                {"status": status, "claim_id": claim_id},
            )

    async def add_document(
        self,
        *,
        document_id: str,
        claim_id: str,
        file_ref: str,
        original_filename: str,
        content_type: str,
        document_type: str,
    ) -> None:
        async with self._pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO claim_documents
                    (document_id, claim_id, file_ref, original_filename, content_type, document_type)
                VALUES (%(document_id)s, %(claim_id)s, %(file_ref)s, %(original_filename)s,
                        %(content_type)s, %(document_type)s)
                """,
                {
                    "document_id": document_id,
                    "claim_id": claim_id,
                    "file_ref": file_ref,
                    "original_filename": original_filename,
                    "content_type": content_type,
                    "document_type": document_type,
                },
            )

    async def save_docket(self, *, docket: AuditDocket) -> None:
        async with self._pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO audit_dockets
                    (docket_id, claim_id, docket_json, total_billed_cents, total_disputed_cents,
                     certified_at, human_decision, human_decided_at)
                VALUES (%(docket_id)s, %(claim_id)s, %(docket_json)s, %(total_billed_cents)s,
                        %(total_disputed_cents)s, %(certified_at)s, %(human_decision)s, %(human_decided_at)s)
                ON CONFLICT (claim_id) DO UPDATE SET
                    docket_json = EXCLUDED.docket_json,
                    total_billed_cents = EXCLUDED.total_billed_cents,
                    total_disputed_cents = EXCLUDED.total_disputed_cents,
                    certified_at = EXCLUDED.certified_at,
                    human_decision = EXCLUDED.human_decision,
                    human_decided_at = EXCLUDED.human_decided_at
                """,
                {
                    "docket_id": docket.docket_id,
                    "claim_id": docket.claim_id,
                    "docket_json": docket.model_dump_json(),
                    "total_billed_cents": docket.total_billed_cents,
                    "total_disputed_cents": docket.total_disputed_cents,
                    "certified_at": docket.evaluator_certification.certified_at,
                    "human_decision": docket.human_approval.decision if docket.human_approval else None,
                    "human_decided_at": docket.human_approval.decided_at if docket.human_approval else None,
                },
            )

    async def get_docket(self, *, claim_id: str) -> AuditDocket | None:
        async with self._pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                "SELECT docket_json FROM audit_dockets WHERE claim_id = %(claim_id)s",
                {"claim_id": claim_id},
            )
            row = await cur.fetchone()
            # psycopg decodes a `jsonb` column back into a Python dict/list (not a str),
            # so this must be `model_validate`, not `model_validate_json`.
            return AuditDocket.model_validate(row["docket_json"]) if row else None
