"""Orchestration helpers bridging the FastAPI routers and the compiled
LangGraph graph: starting a run, resuming past the HITL interrupt, and
mapping raw graph state into the `ClaimStatus` enum surfaced over the API.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.graph.graph import (
    NODE_ESCALATE,
    NODE_EVALUATOR,
    NODE_FINALIZE,
    NODE_INTAKE,
    NODE_MRF_BENCHMARK,
    NODE_NSA_COMPLIANCE,
)
from app.repositories.claims_repository import ClaimsRepository
from app.schemas.claim import ClaimStatus

logger = logging.getLogger(__name__)


def _thread_config(thread_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": thread_id}}


def derive_claim_status(
    *, next_nodes: tuple[str, ...], eval_status: str | None, human_decision: str | None
) -> ClaimStatus:
    """Map raw LangGraph `next` + evaluator state into the public `ClaimStatus` enum."""
    if not next_nodes:
        if human_decision == "APPROVED":
            return "CERTIFIED"
        if human_decision == "REJECTED":
            return "REJECTED"
        if eval_status == "FAILED":
            return "FAILED"
        return "CERTIFIED"
    if NODE_FINALIZE in next_nodes:
        return "AWAITING_HUMAN_REVIEW"
    if NODE_ESCALATE in next_nodes:
        return "FAILED"
    if NODE_EVALUATOR in next_nodes:
        return "EVALUATING"
    if NODE_NSA_COMPLIANCE in next_nodes:
        return "COMPLIANCE_REVIEW"
    if NODE_MRF_BENCHMARK in next_nodes:
        return "BENCHMARKING"
    if NODE_INTAKE in next_nodes:
        return "INTAKE"
    return "INTAKE"


@dataclass
class StatusSnapshot:
    status: ClaimStatus
    eval_status: str | None
    eval_iteration: int | None
    next_nodes: list[str]
    errors: list[str]
    eval_feedback: list[str]


async def run_claim_graph(
    *,
    graph: Any,
    thread_id: str,
    initial_state: dict[str, Any],
    settings: Any,
    claims_repo: ClaimsRepository,
    claim_id: str,
) -> None:
    """Kick off a brand-new claim audit run (invoked as a background task)."""
    config = {**_thread_config(thread_id), "recursion_limit": settings.graph_recursion_limit}
    try:
        await graph.ainvoke(initial_state, config)
    except Exception:  # noqa: BLE001 - surfaced via status polling, not re-raised to caller
        logger.exception("claim run failed for thread_id=%s", thread_id)
        await claims_repo.update_status(claim_id=claim_id, status="FAILED")


async def resume_claim_graph(
    *,
    graph: Any,
    thread_id: str,
    decision: str,
    reviewer: str | None,
    notes: str | None,
    settings: Any,
    claims_repo: ClaimsRepository,
    claim_id: str,
) -> bool:
    """Resume a claim paused at the `finalize_docket` HITL interrupt.

    Returns True only after the docket row is saved. The caller sets
    ``CERTIFIED`` or ``REJECTED`` from the checkpoint after that. A failure
    leaves the claim ``FAILED`` and does not report a decision.
    """
    config = {**_thread_config(thread_id), "recursion_limit": settings.graph_recursion_limit}
    await graph.aupdate_state(
        config,
        {"human_decision": decision, "human_reviewer": reviewer, "human_notes": notes},
    )
    try:
        await graph.ainvoke(None, config)
        final_state = await graph.aget_state(config)
        docket = final_state.values.get("audit_docket") if final_state else None
        if docket is None:
            await claims_repo.update_status(claim_id=claim_id, status="FAILED")
            return False
        await claims_repo.save_docket(docket=docket)
        return True
    except Exception:  # noqa: BLE001
        logger.exception("claim resume failed for thread_id=%s", thread_id)
        await claims_repo.update_status(claim_id=claim_id, status="FAILED")
        return False


async def get_status_snapshot(*, graph: Any, thread_id: str) -> StatusSnapshot | None:
    """Read the current checkpointed state for a thread without advancing it."""
    config = _thread_config(thread_id)
    state = await graph.aget_state(config)
    if state is None or not state.values:
        return None
    values = state.values
    next_nodes = tuple(state.next)
    eval_status = values.get("eval_status")
    human_decision = values.get("human_decision")
    status = derive_claim_status(
        next_nodes=next_nodes, eval_status=eval_status, human_decision=human_decision
    )
    return StatusSnapshot(
        status=status,
        eval_status=eval_status,
        eval_iteration=values.get("eval_iteration"),
        next_nodes=list(next_nodes),
        errors=values.get("errors", []),
        eval_feedback=values.get("eval_feedback", []),
    )


async def sync_claim_status(
    *, claims_repo: ClaimsRepository, claim_id: str, snapshot: StatusSnapshot
) -> None:
    """Persist the derived status onto the `claims` row so list views don't need the graph."""
    await claims_repo.update_status(claim_id=claim_id, status=snapshot.status)
