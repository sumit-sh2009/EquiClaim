"""CMS Machine-Readable File (MRF) ingestion pipeline — Phase 3.

Downloads/reads a hospital's CMS Data Dictionary **v3.0** standard-charge
file (CSV "Tall" template — see `app.schemas.cms_mrf.CmsMrfTallChargeSlice`),
validates each row at the CMS wire-format boundary, converts dollar amounts
to integer cents, and bulk-loads the result into `mrf_line_items`. After a
batch completes, `mrf_qpa_medians` (the QPA-proxy materialized view) is
refreshed so `MRFBenchmarkWorker` sees up-to-date medians immediately.

Usage (CLI):
    uv run python -m app.ingestion.mrf_ingest --hospital-ccn 450123 \\
        --hospital-name "Example Regional Medical Center" --file ./fixtures/example_mrf_tall.csv

Row-level validation errors are collected and reported rather than aborting
the whole batch — CMS files in the wild are frequently malformed, and a
single bad row must never block ingestion of an otherwise-valid file (this
is itself one of the price-transparency non-compliance patterns described
in the mandate).
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from psycopg_pool import AsyncConnectionPool
from pydantic import ValidationError

from app.core.config import get_settings
from app.repositories.mrf_repository import MrfRepository
from app.schemas.cms_mrf import CmsMrfTallChargeSlice

logger = logging.getLogger(__name__)


@dataclass
class IngestionReport:
    hospital_ccn: str
    total_rows: int
    inserted_rows: int
    skipped_rows: int
    errors: list[str]


def _row_to_insertable(
    slice_: CmsMrfTallChargeSlice, *, hospital_ccn: str, source_publish_date: date
) -> dict[str, object] | None:
    if slice_.code_1 is None or slice_.code_1_type is None:
        return None
    return {
        "hospital_ccn": hospital_ccn,
        "cpt_hcpcs_code": slice_.code_1,
        "code_type": slice_.code_1_type,
        "description": slice_.description,
        "gross_charge_cents": slice_.to_cents(slice_.standard_charge_gross),
        "discounted_cash_cents": slice_.to_cents(slice_.standard_charge_discounted_cash),
        "payer_name": slice_.payer_name,
        "plan_name": slice_.plan_name,
        "negotiated_dollar_cents": slice_.to_cents(slice_.standard_charge_negotiated_dollar),
        "negotiated_percentage": slice_.standard_charge_negotiated_percentage,
        "negotiated_algorithm": slice_.standard_charge_negotiated_algorithm,
        "source_publish_date": source_publish_date,
    }


def parse_tall_csv(path: Path) -> tuple[list[CmsMrfTallChargeSlice], list[str]]:
    """Parse a CMS CSV "Tall" file into validated slices, collecting row errors."""
    slices: list[CmsMrfTallChargeSlice] = []
    errors: list[str] = []
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for line_no, row in enumerate(reader, start=2):  # header is line 1
            try:
                slices.append(CmsMrfTallChargeSlice.model_validate(row))
            except ValidationError as exc:
                errors.append(f"row {line_no}: {exc.errors()[0]['msg']}")
    return slices, errors


async def ingest_file(
    *,
    pool: AsyncConnectionPool,
    hospital_ccn: str,
    hospital_name: str,
    file_path: Path,
    source_publish_date: date | None = None,
    hospital_state: str | None = None,
    mrf_source_url: str | None = None,
) -> IngestionReport:
    """Ingest one hospital's CMS Tall CSV MRF into Postgres and refresh QPA medians."""
    repo = MrfRepository(pool)
    publish_date = source_publish_date or date.today()

    await repo.upsert_hospital(
        hospital_ccn=hospital_ccn,
        npi=None,
        name=hospital_name,
        state=hospital_state,
        mrf_source_url=mrf_source_url or str(file_path),
    )

    slices, parse_errors = parse_tall_csv(file_path)
    rows: list[dict[str, object]] = []
    for slice_ in slices:
        row = _row_to_insertable(slice_, hospital_ccn=hospital_ccn, source_publish_date=publish_date)
        if row is not None:
            rows.append(row)

    inserted = await repo.bulk_insert_line_items(rows=rows)
    await repo.refresh_qpa_medians()

    report = IngestionReport(
        hospital_ccn=hospital_ccn,
        total_rows=len(slices) + len(parse_errors),
        inserted_rows=inserted,
        skipped_rows=len(slices) - inserted,
        errors=parse_errors,
    )
    logger.info(
        "MRF ingest complete: hospital=%s inserted=%d skipped=%d errors=%d",
        hospital_ccn,
        report.inserted_rows,
        report.skipped_rows,
        len(report.errors),
    )
    return report


async def _main_async(args: argparse.Namespace) -> None:
    from psycopg.rows import dict_row

    settings = get_settings()
    async with AsyncConnectionPool(
        conninfo=settings.database_url,
        min_size=1,
        max_size=4,
        kwargs={"autocommit": True, "row_factory": dict_row},
    ) as pool:
        report = await ingest_file(
            pool=pool,
            hospital_ccn=args.hospital_ccn,
            hospital_name=args.hospital_name,
            file_path=Path(args.file),
        )
        print(report)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Ingest a CMS MRF Tall CSV file.")
    parser.add_argument("--hospital-ccn", required=True)
    parser.add_argument("--hospital-name", required=True)
    parser.add_argument("--file", required=True)
    asyncio.run(_main_async(parser.parse_args()))


if __name__ == "__main__":
    main()
