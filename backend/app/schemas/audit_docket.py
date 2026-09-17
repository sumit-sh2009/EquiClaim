"""`AuditDocket` — the certified, court/arbitration-ready output of a fully
audited claim, plus its nested finding, certification, and human-approval
records.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, model_validator

from app.schemas.claim import HumanDecision
from app.schemas.claim_line_item import ClaimLineItem
from app.schemas.compliance_finding import ComplianceFinding
from app.schemas.denial_mapping import DenialMapping
from app.schemas.mrf_benchmark import MRFBenchmark


class LineItemFinding(BaseModel):
    """One line item plus every artifact that supports its disputed amount.

    `disputed_amount_cents` must trace to at least one of `denial_mapping`
    or `mrf_benchmark` (the evaluator's provenance invariant) — enforced
    here so a `LineItemFinding` can never be constructed without evidence.
    """

    model_config = ConfigDict(extra="forbid")

    line_item: ClaimLineItem
    denial_mapping: DenialMapping | None = None
    mrf_benchmark: MRFBenchmark | None = None
    compliance_finding: ComplianceFinding | None = None
    disputed_amount_cents: int

    @model_validator(mode="after")
    def disputed_amount_must_trace_to_evidence(self) -> LineItemFinding:
        if self.disputed_amount_cents < 0:
            raise ValueError("disputed_amount_cents must be >= 0")
        no_evidence = self.denial_mapping is None and self.mrf_benchmark is None
        if self.disputed_amount_cents > 0 and no_evidence:
            raise ValueError(
                "a non-zero disputed_amount_cents must trace to at least one "
                "DenialMapping or MRFBenchmark source record (provenance invariant)"
            )
        return self


class EvaluatorCertification(BaseModel):
    """Record of the evaluator-optimizer loop's final pass."""

    model_config = ConfigDict(extra="forbid")

    iteration_count: int
    passed_checks: list[str]
    certified_at: datetime

    @model_validator(mode="after")
    def iteration_within_cap(self) -> EvaluatorCertification:
        if self.iteration_count < 1:
            raise ValueError("iteration_count must be >= 1")
        return self


class HumanApproval(BaseModel):
    """The Human-in-the-Loop decision recorded at the `finalize_docket` interrupt."""

    model_config = ConfigDict(extra="forbid")

    decision: HumanDecision
    approved_by: str | None = None
    decided_at: datetime
    notes: str | None = None


class AuditDocket(BaseModel):
    """The final, certified, statute-cited dispute package for one claim."""

    model_config = ConfigDict(extra="forbid")

    docket_id: str
    claim_id: str
    generated_at: datetime
    line_item_findings: list[LineItemFinding]
    total_billed_cents: int
    total_disputed_cents: int
    statutory_citations: list[str]
    evaluator_certification: EvaluatorCertification
    human_approval: HumanApproval | None = None
    dispute_notice_text: str

    @model_validator(mode="after")
    def totals_reconcile(self) -> AuditDocket:
        computed_disputed = sum(f.disputed_amount_cents for f in self.line_item_findings)
        if computed_disputed != self.total_disputed_cents:
            raise ValueError(
                f"total_disputed_cents ({self.total_disputed_cents}) does not equal the sum "
                f"of line_item_findings disputed amounts ({computed_disputed}) — "
                "cent-exact reconciliation failed"
            )
        if self.total_billed_cents < 0 or self.total_disputed_cents < 0:
            raise ValueError("totals must be >= 0")
        return self
