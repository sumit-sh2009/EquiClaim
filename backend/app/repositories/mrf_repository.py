"""Repository layer for `mrf_line_items` / `mrf_qpa_medians` (Phase 3).

All queries are parameterized (never string-interpolated) and go through the
same `AsyncConnectionPool` the LangGraph checkpointer uses (see
`app/db/pool.py`), fetching rows as dicts (`row_factory=dict_row` set on the
pool itself).
"""

from __future__ import annotations

from dataclasses import dataclass

from psycopg_pool import AsyncConnectionPool


@dataclass
class HospitalRow:
    hospital_ccn: str
    npi: str | None
    name: str
    state: str | None
    mrf_source_url: str | None
    mrf_last_ingested_at: object | None


@dataclass
class QpaMedianRow:
    hospital_ccn: str
    cpt_hcpcs_code: str
    median_negotiated_cents: int | None
    payer_count_sampled: int
    max_gross_charge_cents: int | None
    min_discounted_cash_cents: int | None


class MrfRepository:
    """Read/write access to the MRF benchmark corpus."""

    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def get_qpa_median(
        self, *, hospital_ccn: str, cpt_hcpcs_code: str
    ) -> QpaMedianRow | None:
        """Fetch the pre-computed geographic median negotiated rate for one code."""
        async with self._pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                SELECT hospital_ccn, cpt_hcpcs_code, median_negotiated_cents,
                       payer_count_sampled, max_gross_charge_cents, min_discounted_cash_cents
                FROM mrf_qpa_medians
                WHERE hospital_ccn = %(hospital_ccn)s AND cpt_hcpcs_code = %(code)s
                """,
                {"hospital_ccn": hospital_ccn, "code": cpt_hcpcs_code},
            )
            row = await cur.fetchone()
            if row is None:
                return None
            return QpaMedianRow(**row)

    async def get_qpa_medians_bulk(
        self, *, hospital_ccn: str, cpt_hcpcs_codes: list[str]
    ) -> dict[str, QpaMedianRow]:
        """Batch variant of `get_qpa_median` for all codes on a claim in one round trip."""
        if not cpt_hcpcs_codes:
            return {}
        async with self._pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                SELECT hospital_ccn, cpt_hcpcs_code, median_negotiated_cents,
                       payer_count_sampled, max_gross_charge_cents, min_discounted_cash_cents
                FROM mrf_qpa_medians
                WHERE hospital_ccn = %(hospital_ccn)s AND cpt_hcpcs_code = ANY(%(codes)s)
                """,
                {"hospital_ccn": hospital_ccn, "codes": cpt_hcpcs_codes},
            )
            rows = await cur.fetchall()
            return {row["cpt_hcpcs_code"]: QpaMedianRow(**row) for row in rows}

    async def bulk_insert_line_items(self, *, rows: list[dict[str, object]]) -> int:
        """Bulk-insert ingested MRF rows (Phase 3 ingestion pipeline). Returns row count."""
        if not rows:
            return 0
        async with self._pool.connection() as conn, conn.cursor() as cur:
            await cur.executemany(
                """
                INSERT INTO mrf_line_items (
                    hospital_ccn, cpt_hcpcs_code, code_type, description,
                    gross_charge_cents, discounted_cash_cents, payer_name, plan_name,
                    negotiated_dollar_cents, negotiated_percentage, negotiated_algorithm,
                    source_publish_date
                ) VALUES (
                    %(hospital_ccn)s, %(cpt_hcpcs_code)s, %(code_type)s, %(description)s,
                    %(gross_charge_cents)s, %(discounted_cash_cents)s,
                    %(payer_name)s, %(plan_name)s,
                    %(negotiated_dollar_cents)s, %(negotiated_percentage)s,
                    %(negotiated_algorithm)s, %(source_publish_date)s
                )
                """,
                rows,
            )
        return len(rows)

    async def refresh_qpa_medians(self) -> None:
        """Recompute the materialized median view after an ingestion batch."""
        async with self._pool.connection() as conn, conn.cursor() as cur:
            await cur.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY mrf_qpa_medians")

    async def get_hospital(self, *, hospital_ccn: str) -> HospitalRow | None:
        async with self._pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                SELECT hospital_ccn, npi, name, state, mrf_source_url, mrf_last_ingested_at
                FROM hospitals WHERE hospital_ccn = %(ccn)s
                """,
                {"ccn": hospital_ccn},
            )
            row = await cur.fetchone()
            return HospitalRow(**row) if row else None

    async def upsert_hospital(
        self, *, hospital_ccn: str, npi: str | None, name: str, state: str | None,
        mrf_source_url: str | None,
    ) -> None:
        async with self._pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO hospitals
                    (hospital_ccn, npi, name, state, mrf_source_url, mrf_last_ingested_at)
                VALUES (%(ccn)s, %(npi)s, %(name)s, %(state)s, %(url)s, now())
                ON CONFLICT (hospital_ccn) DO UPDATE SET
                    npi = EXCLUDED.npi,
                    name = EXCLUDED.name,
                    state = EXCLUDED.state,
                    mrf_source_url = EXCLUDED.mrf_source_url,
                    mrf_last_ingested_at = now()
                """,
                {
                    "ccn": hospital_ccn,
                    "npi": npi,
                    "name": name,
                    "state": state,
                    "url": mrf_source_url,
                },
            )
