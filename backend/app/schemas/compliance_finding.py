"""`ComplianceFinding` — a statutory or coding-integrity violation flagged
against a specific claim line item, with a mandatory citation.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from app.domain.citations import is_allowed_citation

RuleType = Literal[
    "NSA_BALANCE_BILL_PROHIBITED",
    "NCCI_UNBUNDLING",
    "QPA_EXCEEDED",
    "MRF_PRICE_GOUGING",
]

ConfidenceLevel = Literal["HIGH", "MEDIUM", "LOW"]


class ComplianceFinding(BaseModel):
    """One flagged violation, always paired with a verifiable statutory citation."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    finding_id: str
    line_item_id: str
    rule_type: RuleType
    citation: str
    narrative: str
    disputed_amount_cents: int
    confidence: ConfidenceLevel = "MEDIUM"

    @model_validator(mode="after")
    def citation_must_be_allow_listed(self) -> ComplianceFinding:
        if not is_allowed_citation(self.citation):
            raise ValueError(
                f"citation {self.citation!r} is not in the statutory allow-list "
                "(app.domain.citations.ALLOWED_CITATIONS) — refusing to construct "
                "a ComplianceFinding with an unverifiable/hallucinated citation"
            )
        if self.disputed_amount_cents < 0:
            raise ValueError("disputed_amount_cents must be >= 0")
        return self
