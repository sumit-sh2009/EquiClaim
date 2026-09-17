"""`DenialMapping` — a CARC/RARC denial or adjustment reason tied to a line item."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

GroupCode = Literal["CO", "PR", "OA", "PI"]
"""Claim Adjustment Group Codes: Contractual Obligation, Patient Responsibility,
Other Adjustment, Payer Initiated reduction."""


class DenialMapping(BaseModel):
    """One CARC/RARC adjustment reason extracted from an EOB, linked to a line item."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    denial_id: str
    line_item_id: str
    carc_code: str
    carc_description: str
    rarc_code: str | None = None
    rarc_description: str | None = None
    group_code: GroupCode
    adjustment_amount_cents: int
    is_upheld_by_evaluator: bool = False

    @model_validator(mode="after")
    def validate_non_negative(self) -> DenialMapping:
        if self.adjustment_amount_cents < 0:
            raise ValueError("adjustment_amount_cents must be >= 0")
        return self
