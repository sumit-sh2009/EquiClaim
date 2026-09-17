"""`IntakeForensicWorker` — Phase 2.

Reads every `SourceDocument` attached to the claim (bills, itemized
statements, EOBs), runs each through the pluggable `DocumentParser` tool
interface (`app/services/document_parser.py`), and normalizes the extracted
records into cents-exact `ClaimLineItem` / `DenialMapping` domain objects:

  - Dollar amounts are converted to integer cents (`round(dollars * 100)`).
  - Procedure codes are classified into CPT/HCPCS/NDC via
    `app.domain.codes.infer_code_type`.
  - CARC/RARC codes are enriched with human-readable descriptions and a
    best-effort group code via `app.domain.carc_rarc`.

Bills/itemized statements are processed first to seed `ClaimLineItem`
records; EOBs are processed second and merged onto the matching line item
by procedure code (falling back to the EOB's own external ref), attaching
`allowed_amount_cents` / `patient_responsibility_cents` and emitting
`DenialMapping` records for every CARC/RARC adjustment.
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import Any

from app.domain.carc_rarc import describe_carc, describe_rarc, infer_group_code
from app.domain.codes import infer_code_type, normalize_code
from app.graph.state import EquiClaimState
from app.schemas.claim_line_item import ClaimLineItem
from app.schemas.denial_mapping import DenialMapping
from app.services.document_parser import (
    ParsedDocument,
    RawDenial,
    RawLineItem,
    coerce_service_date,
    get_document_parser,
)

logger = logging.getLogger(__name__)


def _cents(dollars: float | None) -> int | None:
    if dollars is None:
        return None
    return round(dollars * 100)


def _read_source_text(file_ref: str) -> str:
    return Path(file_ref).read_text(encoding="utf-8")


def _line_item_id(claim_id: str, external_ref: str) -> str:
    return f"{claim_id}:li:{normalize_code(external_ref) or external_ref}"


def _denial_id(claim_id: str, index: int, carc_code: str) -> str:
    return f"{claim_id}:dn:{index}:{carc_code}"


def _build_line_item(
    claim_id: str, raw: RawLineItem, fallback_date: date
) -> ClaimLineItem:
    code = normalize_code(raw.code) if raw.code else None
    return ClaimLineItem(
        line_item_id=_line_item_id(claim_id, raw.external_ref or (raw.code or "0")),
        claim_id=claim_id,
        description=raw.description,
        cpt_hcpcs_code=code,
        code_type=infer_code_type(code) if code else None,
        units=max(raw.units, 1),
        billed_amount_cents=_cents(raw.billed_amount_dollars) or 0,
        allowed_amount_cents=_cents(raw.allowed_amount_dollars),
        patient_responsibility_cents=_cents(raw.patient_responsibility_dollars),
        service_date=coerce_service_date(raw.service_date, fallback=fallback_date),
        place_of_service=raw.place_of_service,
        is_emergency=raw.is_emergency,
        is_out_of_network=raw.is_out_of_network,
    )


def _match_line_item_for_denial(
    denial: RawDenial, line_items: dict[str, ClaimLineItem], claim_id: str
) -> str | None:
    """Resolve a raw denial's `line_item_ref` (often a procedure code) to a line_item_id."""
    direct = line_items.get(_line_item_id(claim_id, denial.line_item_ref))
    if direct:
        return direct.line_item_id
    normalized_ref = normalize_code(denial.line_item_ref)
    for item in line_items.values():
        if item.cpt_hcpcs_code == normalized_ref:
            return item.line_item_id
    return None


async def intake_forensic_worker(state: EquiClaimState) -> dict[str, Any]:
    """Parse all source documents into normalized `ClaimLineItem`/`DenialMapping` records."""
    claim_id = state["claim_id"]
    documents = state.get("source_documents", [])
    fallback_date = date.today()

    line_items: dict[str, ClaimLineItem] = {
        item.line_item_id: item for item in state.get("line_items", [])
    }
    denials: list[DenialMapping] = []
    errors: list[str] = []

    bills = [d for d in documents if d.document_type in ("BILL", "ITEMIZED_STATEMENT")]
    eobs = [d for d in documents if d.document_type == "EOB"]

    # Pass 1 — bills/itemized statements seed the line items.
    for doc in bills:
        try:
            raw_text = _read_source_text(doc.file_ref)
            parsed: ParsedDocument = get_document_parser(content_type=doc.content_type).parse(
                raw_text=raw_text, document_type=doc.document_type
            )
        except (OSError, ValueError) as exc:
            errors.append(f"Failed to parse {doc.document_type} {doc.document_id}: {exc}")
            continue
        errors.extend(parsed.warnings)
        for raw_line in parsed.line_items:
            item = _build_line_item(claim_id, raw_line, fallback_date)
            line_items[item.line_item_id] = item

    # Pass 2 — EOBs merge allowed/patient-responsibility amounts and emit denials.
    denial_index = 0
    for doc in eobs:
        try:
            raw_text = _read_source_text(doc.file_ref)
            parsed = get_document_parser(content_type=doc.content_type).parse(
                raw_text=raw_text, document_type=doc.document_type
            )
        except (OSError, ValueError) as exc:
            errors.append(f"Failed to parse EOB {doc.document_id}: {exc}")
            continue
        errors.extend(parsed.warnings)

        for raw_line in parsed.line_items:
            target_id = _line_item_id(claim_id, raw_line.external_ref)
            existing = line_items.get(target_id)
            if existing is None:
                errors.append(
                    f"EOB references unknown line item {raw_line.external_ref!r}; skipping merge."
                )
                continue
            line_items[target_id] = existing.model_copy(
                update={
                    "allowed_amount_cents": _cents(raw_line.allowed_amount_dollars)
                    or existing.allowed_amount_cents,
                    "patient_responsibility_cents": _cents(
                        raw_line.patient_responsibility_dollars
                    )
                    or existing.patient_responsibility_cents,
                }
            )

        for raw_denial in parsed.denials:
            line_item_id = _match_line_item_for_denial(raw_denial, line_items, claim_id)
            if line_item_id is None:
                errors.append(
                    f"Could not resolve denial for ref {raw_denial.line_item_ref!r} "
                    "to any known line item."
                )
                continue
            group_code = raw_denial.group_code or infer_group_code(raw_denial.carc_code)
            denials.append(
                DenialMapping(
                    denial_id=_denial_id(claim_id, denial_index, raw_denial.carc_code),
                    line_item_id=line_item_id,
                    carc_code=raw_denial.carc_code,
                    carc_description=describe_carc(raw_denial.carc_code),
                    rarc_code=raw_denial.rarc_code,
                    rarc_description=describe_rarc(raw_denial.rarc_code)
                    if raw_denial.rarc_code
                    else None,
                    group_code=group_code if group_code in ("CO", "PR", "OA", "PI") else "OA",
                    adjustment_amount_cents=_cents(raw_denial.adjustment_amount_dollars) or 0,
                )
            )
            denial_index += 1

    logger.info(
        "intake_forensic_worker: claim=%s parsed line_items=%d denials=%d errors=%d",
        claim_id,
        len(line_items),
        len(denials),
        len(errors),
    )

    return {
        "line_items": list(line_items.values()),
        "denial_mappings": denials,
        "errors": errors,
    }
