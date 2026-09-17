"""`finalize_docket` (the Human-in-the-Loop interrupt target) and
`manual_escalation` (the graceful evaluator-loop-exhausted terminal node).

**HITL wiring.** The compiled graph sets `interrupt_before=["finalize_docket"]`
(see `app/graph/graph.py`), so execution pauses *before* this node ever
runs, once `ActuarialEvaluatorNode` reaches `CERTIFIED`. The API layer's
`/claims/{id}/resume` endpoint (Phase 6) performs:

    await graph.aupdate_state(config, {"human_decision": "APPROVED", ...})
    await graph.ainvoke(None, config)

which resumes the graph and runs `finalize_docket` for the first time. This
single node therefore branches internally on `human_decision`:

  - `APPROVED` -> assemble and persist the full, certified `AuditDocket`.
  - `REJECTED` -> still assemble the docket (it is a true, valuable record
    of what the audit found) but mark it archived/unfiled via
    `human_approval.decision`; the API layer never surfaces a REJECTED
    docket as a certified filing.

This keeps the graph to a single interrupt point rather than branching
*before* the interrupt (which would require two different
`interrupt_before` targets and complicate the resume contract).
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from app.graph.state import EquiClaimState
from app.schemas.audit_docket import (
    AuditDocket,
    EvaluatorCertification,
    HumanApproval,
    LineItemFinding,
)
from app.schemas.claim_line_item import ClaimLineItem
from app.schemas.compliance_finding import ComplianceFinding
from app.schemas.denial_mapping import DenialMapping
from app.schemas.mrf_benchmark import MRFBenchmark
from app.services.dispute_notice import render_dispute_notice

logger = logging.getLogger(__name__)

_PASSED_CHECKS = [
    "reconciliation",
    "non_negativity",
    "qpa_cap",
    "ncci_unbundling",
    "citation_allow_list",
    "provenance",
]


def _assemble_line_item_findings(
    line_items: list[ClaimLineItem],
    findings: list[ComplianceFinding],
    denials: list[DenialMapping],
    benchmarks: list[MRFBenchmark],
) -> list[LineItemFinding]:
    findings_by_item: dict[str, list[ComplianceFinding]] = {}
    for f in findings:
        findings_by_item.setdefault(f.line_item_id, []).append(f)
    denials_by_item: dict[str, list[DenialMapping]] = {}
    for d in denials:
        denials_by_item.setdefault(d.line_item_id, []).append(d)
    benchmarks_by_code = {b.cpt_hcpcs_code: b for b in benchmarks}

    line_item_findings: list[LineItemFinding] = []
    for item in line_items:
        item_findings = findings_by_item.get(item.line_item_id, [])
        disputed_total = sum(f.disputed_amount_cents for f in item_findings)
        line_item_findings.append(
            LineItemFinding(
                line_item=item,
                denial_mapping=next(iter(denials_by_item.get(item.line_item_id, [])), None),
                mrf_benchmark=benchmarks_by_code.get(item.cpt_hcpcs_code or ""),
                compliance_finding=item_findings[0] if item_findings else None,
                disputed_amount_cents=disputed_total,
            )
        )
    return line_item_findings


def _build_audit_docket(state: EquiClaimState, *, decision: str) -> AuditDocket:
    claim_id = state["claim_id"]
    line_items = state.get("line_items", [])
    findings = state.get("compliance_findings", [])
    denials = state.get("denial_mappings", [])
    benchmarks = state.get("mrf_benchmarks", [])
    now = datetime.now(UTC)

    line_item_findings = _assemble_line_item_findings(line_items, findings, denials, benchmarks)
    total_billed = sum(item.billed_amount_cents for item in line_items)
    total_disputed = sum(lif.disputed_amount_cents for lif in line_item_findings)
    statutory_citations = sorted({f.citation for f in findings})

    dispute_notice_text = render_dispute_notice(
        claim_id=claim_id,
        line_item_findings=line_item_findings,
        statutory_citations=statutory_citations,
        total_billed_cents=total_billed,
        total_disputed_cents=total_disputed,
        generated_at=now,
    )

    return AuditDocket(
        docket_id=str(uuid.uuid4()),
        claim_id=claim_id,
        generated_at=now,
        line_item_findings=line_item_findings,
        total_billed_cents=total_billed,
        total_disputed_cents=total_disputed,
        statutory_citations=statutory_citations,
        evaluator_certification=EvaluatorCertification(
            iteration_count=state.get("eval_iteration", 1),
            passed_checks=_PASSED_CHECKS,
            certified_at=now,
        ),
        human_approval=HumanApproval(
            decision=decision,  # type: ignore[arg-type]
            approved_by=state.get("human_reviewer"),
            decided_at=now,
            notes=state.get("human_notes"),
        ),
        dispute_notice_text=dispute_notice_text,
    )


async def finalize_docket(state: EquiClaimState) -> dict[str, Any]:
    """Assemble the final `AuditDocket` after the HITL interrupt has been resumed."""
    claim_id = state["claim_id"]
    decision = state.get("human_decision") or "PENDING"

    if decision not in ("APPROVED", "REJECTED", "EDITED"):
        logger.warning(
            "finalize_docket: claim=%s resumed with unexpected human_decision=%r; "
            "treating as REJECTED for safety",
            claim_id,
            decision,
        )
        decision = "REJECTED"

    docket = _build_audit_docket(state, decision=decision)
    logger.info(
        "finalize_docket: claim=%s decision=%s total_disputed_cents=%d",
        claim_id,
        decision,
        docket.total_disputed_cents,
    )
    return {"audit_docket": docket}


async def manual_escalation(state: EquiClaimState) -> dict[str, Any]:
    """Graceful terminal node reached when the evaluator-optimizer loop is exhausted."""
    claim_id = state["claim_id"]
    feedback = state.get("eval_feedback", [])
    message = (
        f"Claim {claim_id} could not be automatically certified after "
        f"{state.get('eval_iteration', 0)} evaluator iteration(s). Manual review required. "
        f"Last feedback: {feedback[-1] if feedback else 'none'}"
    )
    logger.warning("manual_escalation: %s", message)
    return {"errors": [message]}
