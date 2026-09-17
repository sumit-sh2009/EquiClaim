"""`EquiClaimState` — the single shared state object threaded through every
node of the EquiClaim `StateGraph`, checkpointed to Postgres after every
super-step by `AsyncPostgresSaver`.

Channel reducer legend:
  - **overwrite** (no `Annotated` wrapper): the last writer wins. Used for
    scalars/singletons that are set once or intentionally replaced wholesale.
  - **upsert** (`Annotated[list[T], upsert_*]`): merge-by-identity-key. Used
    for worker outputs that may be corrected across evaluator-optimizer
    retries, so retries replace stale entries instead of duplicating them.
  - **append** (`Annotated[list[str], append_unique]`): grows monotonically.
    Used only for the audit trail fields where history itself is the point.
"""

from __future__ import annotations

from typing import Annotated, Literal, TypedDict

from langgraph.managed.is_last_step import RemainingSteps

from app.graph.reducers import (
    append_unique,
    upsert_compliance_findings,
    upsert_denial_mappings,
    upsert_line_items,
    upsert_mrf_benchmarks,
)
from app.schemas.audit_docket import AuditDocket
from app.schemas.claim import HumanDecision, SourceDocument
from app.schemas.claim_line_item import ClaimLineItem
from app.schemas.compliance_finding import ComplianceFinding
from app.schemas.denial_mapping import DenialMapping
from app.schemas.mrf_benchmark import MRFBenchmark

EvalStatus = Literal["PENDING", "NEEDS_REVISION", "CERTIFIED", "FAILED"]


class EquiClaimState(TypedDict, total=False):
    """Shared state channels for the EquiClaim forensic audit graph."""

    # --- identity (overwrite; set once at graph start) ---
    claim_id: str
    thread_id: str
    tenant_id: str
    hospital_ccn: str | None

    # --- intake (overwrite; set once by IntakeForensicWorker) ---
    source_documents: list[SourceDocument]

    # --- worker outputs (upsert-by-key; corrected in place across retries) ---
    line_items: Annotated[list[ClaimLineItem], upsert_line_items]
    denial_mappings: Annotated[list[DenialMapping], upsert_denial_mappings]
    mrf_benchmarks: Annotated[list[MRFBenchmark], upsert_mrf_benchmarks]
    compliance_findings: Annotated[list[ComplianceFinding], upsert_compliance_findings]

    # --- evaluator-optimizer control (overwrite unless noted) ---
    eval_iteration: int
    eval_feedback: Annotated[list[str], append_unique]
    eval_status: EvalStatus
    eval_route_hint: str
    """Set by `ActuarialEvaluatorNode`; consumed verbatim by the conditional edge
    (`app.graph.graph.route_after_evaluator`) to decide which node runs next.
    One of: 'mrf_benchmark_worker' | 'nsa_compliance_worker' | 'finalize_docket'
    | 'manual_escalation'."""

    # --- output + HITL (overwrite) ---
    audit_docket: AuditDocket | None
    human_decision: HumanDecision | None
    human_reviewer: str | None
    human_notes: str | None

    # --- diagnostics (append) ---
    errors: Annotated[list[str], append_unique]

    # --- official LangGraph managed channel: proactive recursion defense-in-depth ---
    remaining_steps: RemainingSteps


def initial_state(
    *, claim_id: str, thread_id: str, tenant_id: str, hospital_ccn: str | None = None
) -> EquiClaimState:
    """Build the seed state for a brand-new claim audit run."""
    return EquiClaimState(
        claim_id=claim_id,
        thread_id=thread_id,
        tenant_id=tenant_id,
        hospital_ccn=hospital_ccn,
        source_documents=[],
        line_items=[],
        denial_mappings=[],
        mrf_benchmarks=[],
        compliance_findings=[],
        eval_iteration=0,
        eval_feedback=[],
        eval_status="PENDING",
        eval_route_hint="mrf_benchmark_worker",
        audit_docket=None,
        human_decision=None,
        human_reviewer=None,
        human_notes=None,
        errors=[],
    )
