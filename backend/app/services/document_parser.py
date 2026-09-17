"""Document parsing / extraction tool interface for `IntakeForensicWorker`.

EquiClaim deliberately separates two concerns that real-world OCR pipelines
conflate:

  1. **Extraction** (out of scope for this module): turning a scanned/photo
     bill into structured text or JSON. In production this is a call to a
     vision-capable OCR tool exposed over MCP (Model Context Protocol) —
     see the `DocumentParser` Protocol below, which is the seam a FastMCP
     tool client would implement.
  2. **Normalization** (`IntakeForensicWorker`, `app/graph/nodes/intake.py`):
     turning extracted records into cents-exact `ClaimLineItem` /
     `DenialMapping` domain objects with CPT/CARC/RARC enrichment.

This module ships two concrete `DocumentParser` implementations so the graph
is runnable end-to-end without a live OCR service:

  - `StructuredJsonDocumentParser` — parses a defined JSON schema, which is
    exactly the shape a real OCR/extraction MCP tool would emit. This is the
    primary, production-realistic path.
  - `PlaintextLineItemParser` — a regression-friendly regex fallback for
    plain-text itemized bills/EOBs (e.g. text already extracted by a
    generic OCR pass with no structured schema).

Swapping in a real MCP-backed vision OCR tool later means implementing
`DocumentParser` against that tool's client — no changes to
`IntakeForensicWorker` are required.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Protocol


@dataclass
class RawLineItem:
    """Extraction-layer line item, before cents conversion / code enrichment."""

    external_ref: str
    description: str
    code: str | None
    units: int = 1
    billed_amount_dollars: float = 0.0
    allowed_amount_dollars: float | None = None
    patient_responsibility_dollars: float | None = None
    service_date: str | None = None
    place_of_service: str | None = None
    is_emergency: bool = False
    is_out_of_network: bool | None = None


@dataclass
class RawDenial:
    """Extraction-layer CARC/RARC adjustment, before enrichment."""

    line_item_ref: str
    carc_code: str
    rarc_code: str | None = None
    group_code: str | None = None
    adjustment_amount_dollars: float = 0.0


@dataclass
class ParsedDocument:
    line_items: list[RawLineItem] = field(default_factory=list)
    denials: list[RawDenial] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class DocumentParser(Protocol):
    """Seam for pluggable document extraction (JSON fixture, OCR/MCP tool, ...)."""

    def parse(self, *, raw_text: str, document_type: str) -> ParsedDocument: ...


class StructuredJsonDocumentParser:
    """Parses the normalized JSON schema emitted by an upstream extraction step.

    Expected BILL/ITEMIZED_STATEMENT shape::

        {
          "line_items": [
            {"ref": "1", "description": "ER visit level 4", "code": "99284",
             "units": 1, "billed_amount": 1250.00, "service_date": "2026-01-15",
             "place_of_service": "23", "is_emergency": true, "is_out_of_network": true}
          ]
        }

    Expected EOB shape::

        {
          "line_items": [
            {"ref": "1", "allowed_amount": 320.00, "patient_responsibility": 930.00}
          ],
          "denials": [
            {"line_item_ref": "1", "carc_code": "45", "rarc_code": "N822",
             "group_code": "CO", "adjustment_amount": 930.00}
          ]
        }
    """

    def parse(self, *, raw_text: str, document_type: str) -> ParsedDocument:
        payload = json.loads(raw_text)
        result = ParsedDocument()

        for idx, raw in enumerate(payload.get("line_items", [])):
            result.line_items.append(
                RawLineItem(
                    external_ref=str(raw.get("ref", idx)),
                    description=raw.get("description", "Unknown service"),
                    code=raw.get("code"),
                    units=int(raw.get("units", 1)),
                    billed_amount_dollars=float(raw.get("billed_amount", 0.0)),
                    allowed_amount_dollars=_maybe_float(raw.get("allowed_amount")),
                    patient_responsibility_dollars=_maybe_float(
                        raw.get("patient_responsibility")
                    ),
                    service_date=raw.get("service_date"),
                    place_of_service=raw.get("place_of_service"),
                    is_emergency=bool(raw.get("is_emergency", False)),
                    is_out_of_network=raw.get("is_out_of_network"),
                )
            )

        for raw in payload.get("denials", []):
            result.denials.append(
                RawDenial(
                    line_item_ref=str(raw.get("line_item_ref", "")),
                    carc_code=str(raw["carc_code"]),
                    rarc_code=raw.get("rarc_code"),
                    group_code=raw.get("group_code"),
                    adjustment_amount_dollars=float(raw.get("adjustment_amount", 0.0)),
                )
            )

        return result


def _maybe_float(value: object) -> float | None:
    return float(value) if value is not None else None


class PlaintextLineItemParser:
    """Regex fallback for plain-text OCR output with no structured schema.

    Bill line format:   ``<code>  <description>  $<amount>``
        e.g. ``99284  Emergency room visit level 4   $1,250.00``
    EOB line format:    ``<code>  CARC:<code>  [RARC:<code>]  GROUP:<code>  AMOUNT:$<amount>``
        e.g. ``99284  CARC:45  RARC:N822  GROUP:CO  AMOUNT:$930.00``
    """

    _BILL_LINE = re.compile(
        r"^(?P<code>[A-Za-z0-9]{4,6})\s+(?P<description>.+?)\s+\$(?P<amount>[\d,]+\.\d{2})\s*$"
    )
    _EOB_LINE = re.compile(
        r"^(?P<code>[A-Za-z0-9]{4,6})\s+CARC:(?P<carc>\S+)"
        r"(?:\s+RARC:(?P<rarc>\S+))?"
        r"\s+GROUP:(?P<group>\S+)"
        r"\s+AMOUNT:\$(?P<amount>[\d,]+\.\d{2})\s*$"
    )

    def parse(self, *, raw_text: str, document_type: str) -> ParsedDocument:
        result = ParsedDocument()
        for line in raw_text.splitlines():
            line = line.strip()
            if not line:
                continue
            if document_type == "EOB":
                match = self._EOB_LINE.match(line)
                if match:
                    result.denials.append(
                        RawDenial(
                            line_item_ref=match["code"],
                            carc_code=match["carc"],
                            rarc_code=match["rarc"],
                            group_code=match["group"],
                            adjustment_amount_dollars=float(match["amount"].replace(",", "")),
                        )
                    )
                    continue
            match = self._BILL_LINE.match(line)
            if match:
                result.line_items.append(
                    RawLineItem(
                        external_ref=match["code"],
                        description=match["description"].strip(),
                        code=match["code"],
                        billed_amount_dollars=float(match["amount"].replace(",", "")),
                        service_date=None,
                    )
                )
                continue
            result.warnings.append(f"Unparsed line in {document_type} document: {line!r}")
        return result


def get_document_parser(*, content_type: str) -> DocumentParser:
    """Select a parser based on the uploaded document's content type."""
    if "json" in content_type:
        return StructuredJsonDocumentParser()
    return PlaintextLineItemParser()


def coerce_service_date(raw: str | None, *, fallback: date) -> date:
    """Best-effort ISO-date coercion with a safe fallback (e.g. claim intake date)."""
    if not raw:
        return fallback
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return fallback
