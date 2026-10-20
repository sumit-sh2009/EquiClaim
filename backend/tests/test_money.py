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


def test_multi_currency_symbol_stripping_and_parsing() -> None:
    from app.domain.money import convert_currency, detect_currency, format_money, parse_money

    # Detect currency
    assert detect_currency("$1,500.00") == "USD"
    assert detect_currency("€1,200.00") == "EUR"
    assert detect_currency("£450.50") == "GBP"
    assert detect_currency("CA$180.00") == "CAD"
    assert detect_currency("₹2,500.00") == "INR"
    assert detect_currency("¥15,000") == "JPY"
    assert detect_currency("100.00 EUR") == "EUR"

    # dollars_to_cents with symbols
    assert dollars_to_cents("€100.50") == 10050
    assert dollars_to_cents("£45.00") == 4500
    assert dollars_to_cents("₹1,250.75") == 125075
    assert dollars_to_cents("CA$99.99") == 9999
    assert dollars_to_cents("¥500", currency="JPY") == 500

    # parse_money
    assert parse_money("€75.50") == (7550, "EUR")
    assert parse_money("£120.00") == (12000, "GBP")
    assert parse_money("$500.00") == (50000, "USD")
    assert parse_money("₹50.00") == (5000, "INR")

    # convert_currency
    # 100.00 USD (10000 cents) -> EUR at 0.92 = 9200 cents (92.00 EUR)
    assert convert_currency(10000, "USD", "EUR") == 9200
    # 100.00 USD -> GBP at 0.79 = 7900 cents (79.00 GBP)
    assert convert_currency(10000, "USD", "GBP") == 7900
    # 100.00 USD -> JPY at 155 = 15500 yen
    assert convert_currency(10000, "USD", "JPY") == 15500
    # Convert same currency returns identical
    assert convert_currency(12345, "EUR", "EUR") == 12345

    # format_money
    assert format_money(125055, "USD") == "$1,250.55"
    assert format_money(115000, "EUR") == "€1,150.00"
    assert format_money(98750, "GBP") == "£987.50"
    assert format_money(15500, "JPY") == "¥15,500"
    assert format_money(250000, "INR") == "₹2,500.00"


def test_plaintext_parser_handles_multi_currency() -> None:
    from app.services.document_parser import PlaintextLineItemParser

    parser = PlaintextLineItemParser()
    eur_bill = (
        "99284  Emergency room visit level 4   €1,250.00\n"
        "36415  Routine venipuncture   £45.00\n"
        "71046  Chest X-ray, 2 views   CA$180.00\n"
    )
    parsed = parser.parse(raw_text=eur_bill, document_type="BILL")
    assert len(parsed.line_items) == 3
    assert parsed.line_items[0].billed_amount_dollars == Decimal("1250.00")
    assert parsed.line_items[1].billed_amount_dollars == Decimal("45.00")
    assert parsed.line_items[2].billed_amount_dollars == Decimal("180.00")

