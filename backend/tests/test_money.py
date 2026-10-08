"""Cents conversion and document parsing stay exact at the extraction boundary."""

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from app.domain.money import dollars_to_cents
from app.graph.nodes.intake import intake_forensic_worker
from app.schemas.claim import SourceDocument
from app.services.document_parser import StructuredJsonDocumentParser


def test_half_up_keeps_the_cent_binary_floats_drop() -> None:
    assert dollars_to_cents("1.005") == 101
    assert dollars_to_cents(Decimal("10.10")) == 1010
    assert dollars_to_cents("0.1") == 10
    assert dollars_to_cents("1,250.55") == 125_055
    assert dollars_to_cents(None) is None
    assert round(1.005 * 100) == 100


def test_json_bill_parses_money_as_decimal() -> None:
    parsed = StructuredJsonDocumentParser().parse(
        raw_text='{"line_items":[{"ref":"1","billed_amount":10.10,"code":"99284"}]}',
        document_type="BILL",
    )
    assert parsed.line_items[0].billed_amount_dollars == Decimal("10.10")


@pytest.mark.asyncio
async def test_eob_zero_patient_share_replaces_the_bill_amount(tmp_path: Path) -> None:
    bill = tmp_path / "bill.json"
    eob = tmp_path / "eob.json"
    bill.write_text(
        '{"line_items":[{"ref":"99284","description":"Visit","code":"99284",'
        '"billed_amount":"1500.00","patient_responsibility":"1180.00"}]}',
        encoding="utf-8",
    )
    eob.write_text(
        '{"line_items":[{"ref":"99284","allowed_amount":"0.00","patient_responsibility":"0.00"}]}',
        encoding="utf-8",
    )
    now = datetime.now(UTC)
    state = {
        "claim_id": "c1",
        "source_documents": [
            SourceDocument(
                document_id="d1",
                claim_id="c1",
                document_type="BILL",
                file_ref=str(bill),
                original_filename="bill.json",
                content_type="application/json",
                uploaded_at=now,
            ),
            SourceDocument(
                document_id="d2",
                claim_id="c1",
                document_type="EOB",
                file_ref=str(eob),
                original_filename="eob.json",
                content_type="application/json",
                uploaded_at=now,
            ),
        ],
    }
    result = await intake_forensic_worker(state)  # type: ignore[arg-type]
    item = result["line_items"][0]
    assert item.billed_amount_cents == 150_000
    assert item.allowed_amount_cents == 0
    assert item.patient_responsibility_cents == 0


@pytest.mark.asyncio
async def test_repeated_refs_keep_every_bill_line(tmp_path: Path) -> None:
    bill = tmp_path / "bill.json"
    bill.write_text(
        '{"line_items":['
        '{"ref":"1","description":"First","code":"99284","billed_amount":"10.00"},'
        '{"ref":"1","description":"Second","code":"99284","billed_amount":"20.00"},'
        '{"ref":"2","description":"Third","code":"99284","billed_amount":"30.00"}'
        "]}",
        encoding="utf-8",
    )
    now = datetime.now(UTC)
    state = {
        "claim_id": "c1",
        "source_documents": [
            SourceDocument(
                document_id="d1",
                claim_id="c1",
                document_type="BILL",
                file_ref=str(bill),
                original_filename="bill.json",
                content_type="text/plain",
                uploaded_at=now,
            )
        ],
    }
    result = await intake_forensic_worker(state)  # type: ignore[arg-type]
    billed = sorted(item.billed_amount_cents for item in result["line_items"])
    assert billed == [1_000, 2_000, 3_000]
    assert len({item.line_item_id for item in result["line_items"]}) == 3
