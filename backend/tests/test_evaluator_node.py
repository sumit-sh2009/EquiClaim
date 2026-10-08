"""Unit tests for `ActuarialEvaluatorNode` — no DB required.

Covers defect detection and the graceful (non-`GraphRecursionError`)
`manual_escalation` exit. Workers recompute the same inputs, so a defect
fails the claim immediately instead of looping.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.graph.nodes.evaluator import build_evaluator_node
from app.schemas.claim_line_item import ClaimLineItem


def _line_item(**overrides: object) -> ClaimLineItem:
    defaults: dict[str, object] = dict(
        line_item_id="li_1",
        claim_id="claim_1",
        description="Emergency room visit level 4",
        cpt_hcpcs_code="99284",
        code_type="CPT",
        units=1,
        billed_amount_cents=150_000,
        allowed_amount_cents=32_000,
        patient_responsibility_cents=118_000,
        service_date=date(2026, 1, 15),
        is_emergency=True,
        is_out_of_network=True,
    )
    defaults.update(overrides)
    return ClaimLineItem(**defaults)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_evaluator_certifies_when_all_invariants_pass() -> None:
    node = build_evaluator_node(max_iterations=3)
    state = {
        "claim_id": "claim_1",
        "line_items": [_line_item()],
        "denial_mappings": [],
        "mrf_benchmarks": [],
        "compliance_findings": [],
        "eval_iteration": 0,
    }
    result = await node(state)
    assert result["eval_status"] == "CERTIFIED"
    assert result["eval_route_hint"] == "finalize_docket"
    assert result["eval_iteration"] == 1


@pytest.mark.asyncio
async def test_evaluator_detects_reconciliation_defect_and_routes_to_mrf_worker() -> None:
    node = build_evaluator_node(max_iterations=3)
    # allowed(32000) + patient_responsibility(118000) != billed(150000) -> off by 1 cent.
    bad_item = _line_item(patient_responsibility_cents=118_001)
    state = {
        "claim_id": "claim_1",
        "line_items": [bad_item],
        "denial_mappings": [],
        "mrf_benchmarks": [],
        "compliance_findings": [],
        "eval_iteration": 0,
    }
    result = await node(state)
    assert result["eval_status"] == "FAILED"
    assert result["eval_route_hint"] == "manual_escalation"
    assert any("RECONCILIATION" in fb for fb in result["eval_feedback"])
    assert "line_items" not in result
    assert bad_item.billed_amount_cents == 150_000
    assert bad_item.patient_responsibility_cents == 118_001


@pytest.mark.asyncio
async def test_evaluator_escalates_gracefully_after_max_iterations() -> None:
    node = build_evaluator_node(max_iterations=3)
    bad_item = _line_item(patient_responsibility_cents=118_001)
    state = {
        "claim_id": "claim_1",
        "line_items": [bad_item],
        "denial_mappings": [],
        "mrf_benchmarks": [],
        "compliance_findings": [],
        "eval_iteration": 2,  # this call becomes iteration 3 == max_iterations
    }
    result = await node(state)
    assert result["eval_iteration"] == 3
    assert result["eval_status"] == "FAILED"
    assert result["eval_route_hint"] == "manual_escalation"


@pytest.mark.asyncio
async def test_evaluator_detects_missing_ncci_finding() -> None:
    node = build_evaluator_node(max_iterations=3)
    col1 = _line_item(
        line_item_id="li_col1",
        cpt_hcpcs_code="71046",
        billed_amount_cents=18_000,
        allowed_amount_cents=18_000,
        patient_responsibility_cents=0,
        is_emergency=False,
        is_out_of_network=False,
    )
    col2 = _line_item(
        line_item_id="li_col2",
        cpt_hcpcs_code="71045",
        billed_amount_cents=11_000,
        allowed_amount_cents=11_000,
        patient_responsibility_cents=0,
        is_emergency=False,
        is_out_of_network=False,
    )
    state = {
        "claim_id": "claim_1",
        "line_items": [col1, col2],
        "denial_mappings": [],
        "mrf_benchmarks": [],
        "compliance_findings": [],  # NoSurprisesActComplianceWorker "forgot" the NCCI finding
        "eval_iteration": 0,
    }
    result = await node(state)
    assert result["eval_status"] == "FAILED"
    assert result["eval_route_hint"] == "manual_escalation"
    assert any("NCCI_UNBUNDLING" in fb for fb in result["eval_feedback"])
    assert col2.billed_amount_cents == 11_000
