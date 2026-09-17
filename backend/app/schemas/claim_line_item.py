"""`ClaimLineItem` — a single normalized procedure/service line extracted
from a bill or itemized statement by the `IntakeForensicWorker`.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, model_validator

from app.schemas.cms_mrf import CodeType


class ClaimLineItem(BaseModel):
    """One billed procedure/service line, cents-exact.

    All dollar amounts are integer cents. `allowed_amount_cents` and
    `patient_responsibility_cents` are optional at intake time (before the
    EOB has been reconciled against the bill) but are required for the
    evaluator's reconciliation invariant once both documents are parsed.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    line_item_id: str
    claim_id: str
    description: str
    cpt_hcpcs_code: str | None = None
    code_type: CodeType | None = None
    units: int = 1
    billed_amount_cents: int
    allowed_amount_cents: int | None = None
    patient_responsibility_cents: int | None = None
    service_date: date
    place_of_service: str | None = None
    is_emergency: bool = False
    is_out_of_network: bool | None = None

    @model_validator(mode="after")
    def validate_non_negative_and_units(self) -> ClaimLineItem:
        if self.billed_amount_cents < 0:
            raise ValueError("billed_amount_cents must be >= 0")
        if self.units < 1:
            raise ValueError("units must be >= 1")
        for field_name in ("allowed_amount_cents", "patient_responsibility_cents"):
            value = getattr(self, field_name)
            if value is not None and value < 0:
                raise ValueError(f"{field_name} must be >= 0")
        return self
