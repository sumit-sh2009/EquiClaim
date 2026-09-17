"""`ActuarialEvaluatorNode` — Phase 5 (the "evaluator" in the
evaluator-optimizer reflection loop).

Independently re-verifies every mathematical and statutory invariant the
mandate requires, **before** a docket is ever allowed to reach the
Human-in-the-Loop interrupt. On any defect it appends structured feedback to
`eval_feedback`, increments `eval_iteration`, and sets `eval_route_hint` to
send control back to the worker responsible for that class of defect:

  - Reconciliation / QPA-cap / provenance defects -> `mrf_benchmark_worker`
    (bad or missing benchmark data is the most common root cause).
  - Statutory citation / NCCI-coverage defects -> `nsa_compliance_worker`.

If `eval_iteration` reaches `evaluator_max_iterations` (mandate: 3) without
reaching `CERTIFIED`, the loop is broken deliberately and gracefully —
`eval_status` is forced to `FAILED` and `eval_route_hint` points at
`manual_escalation`, never at raising `GraphRecursionError`. The graph's
`recursion_limit` config (default 50, see `Settings.graph_recursion_limit`)
remains as an independent, coarser backstop beneath this app-level cap, and
`remaining_steps` (LangGraph's own managed channel) provides a third,
official layer of defense-in-depth per the reference sheet.

Mathematical invariants enforced:
  1. **Reconciliation** — for every line item with all three of billed/
     allowed/patient-responsibility populated:
     `billed == allowed + sum(adjustments) + patient_responsibility` (exact
     integer-cents equality, zero tolerance).
  2. **Non-negativity** — re-verified independently of the Pydantic
     validators that already forbid it at construction time.
  3. **QPA cap** — every emergency/OON line item whose patient
     responsibility exceeds its MRF benchmark median must have a matching,
     correctly-quantified `QPA_EXCEEDED` finding.
  4. **NCCI unbundling** — every same-date CPT pair matching a modifier-
     indicator-0 PTP edit must have a matching `NCCI_UNBUNDLING` finding.

Statutory invariants enforced:
  5. **Citation allow-list** — defense-in-depth re-check of
     `app.domain.citations.is_allowed_citation` over every finding (the
     Pydantic model already forbids construction of a bad citation, but the
     evaluator re-verifies independently rather than trusting the worker).
  6. **Provenance** — every finding with `disputed_amount_cents > 0` must
     trace to at least one `MRFBenchmark` or `DenialMapping` source record.
"""

from __future__ import annotations

import logging
from itertools import combinations
from typing import Any, Literal

from app.domain.citations import is_allowed_citation
from app.domain.ncci import is_unbundling_violation
from app.graph.state import EquiClaimState
from app.schemas.claim_line_item import ClaimLineItem
from app.schemas.compliance_finding import ComplianceFinding
from app.schemas.denial_mapping import DenialMapping
from app.schemas.mrf_benchmark import MRFBenchmark

logger = logging.getLogger(__name__)

RouteHint = Literal["mrf_benchmark_worker", "nsa_compliance_worker", "finalize_docket", "manual_escalation"]


def _check_reconciliation(
    line_items: list[ClaimLineItem], denials_by_item: dict[str, list[DenialMapping]]
) -> list[str]:
    defects: list[str] = []
    for item in line_items:
        if item.allowed_amount_cents is None or item.patient_responsibility_cents is None:
            continue
        adjustments = sum(d.adjustment_amount_cents for d in denials_by_item.get(item.line_item_id, []))
        expected = item.allowed_amount_cents + adjustments + item.patient_responsibility_cents
        if expected != item.billed_amount_cents:
            defects.append(
                f"RECONCILIATION: line_item {item.line_item_id} billed={item.billed_amount_cents} "
                f"but allowed({item.allowed_amount_cents}) + adjustments({adjustments}) + "
                f"patient_responsibility({item.patient_responsibility_cents}) = {expected}. "
                "MRFBenchmarkWorker must re-verify the source amounts."
            )
    return defects


def _check_non_negativity(
    line_items: list[ClaimLineItem],
    denials: list[DenialMapping],
    benchmarks: list[MRFBenchmark],
    findings: list[ComplianceFinding],
) -> list[str]:
    defects: list[str] = []
    for item in line_items:
        if item.billed_amount_cents < 0:
            defects.append(f"NON_NEGATIVITY: line_item {item.line_item_id} billed_amount_cents < 0")
    for denial in denials:
        if denial.adjustment_amount_cents < 0:
            defects.append(f"NON_NEGATIVITY: denial {denial.denial_id} adjustment_amount_cents < 0")
    for benchmark in benchmarks:
        if (benchmark.median_negotiated_cents or 0) < 0:
            defects.append(f"NON_NEGATIVITY: benchmark {benchmark.benchmark_id} negative price")
    for finding in findings:
        if finding.disputed_amount_cents < 0:
            defects.append(f"NON_NEGATIVITY: finding {finding.finding_id} disputed_amount_cents < 0")
    return defects


def _check_qpa_invariant(
    line_items: list[ClaimLineItem],
    benchmarks_by_code: dict[str, MRFBenchmark],
    findings: list[ComplianceFinding],
) -> list[str]:
    defects: list[str] = []
    findings_by_line_item = {f.line_item_id: f for f in findings if f.rule_type == "QPA_EXCEEDED"}
    for item in line_items:
        if not (item.is_emergency or item.is_out_of_network):
            continue
        if item.patient_responsibility_cents is None:
            continue
        benchmark = benchmarks_by_code.get(item.cpt_hcpcs_code or "")
        if benchmark is None or benchmark.median_negotiated_cents is None:
            continue
        qpa = benchmark.median_negotiated_cents
        if item.patient_responsibility_cents <= qpa:
            continue
        expected_overage = item.patient_responsibility_cents - qpa
        finding = findings_by_line_item.get(item.line_item_id)
        if finding is None:
            defects.append(
                f"QPA_CAP: line_item {item.line_item_id} exceeds QPA by {expected_overage} cents "
                "but no QPA_EXCEEDED finding was recorded. NoSurprisesActComplianceWorker must "
                "re-run."
            )
        elif finding.disputed_amount_cents != expected_overage:
            defects.append(
                f"QPA_CAP: line_item {item.line_item_id} QPA_EXCEEDED finding disputes "
                f"{finding.disputed_amount_cents} cents but exact overage is {expected_overage}."
            )
    return defects


def _check_ncci_invariant(
    line_items: list[ClaimLineItem], findings: list[ComplianceFinding]
) -> list[str]:
    defects: list[str] = []
    ncci_line_items_flagged = {f.line_item_id for f in findings if f.rule_type == "NCCI_UNBUNDLING"}
    by_date: dict[Any, list[ClaimLineItem]] = {}
    for item in line_items:
        if item.cpt_hcpcs_code:
            by_date.setdefault(item.service_date, []).append(item)
    for _date, items in by_date.items():
        for item_a, item_b in combinations(items, 2):
            edit = is_unbundling_violation(item_a.cpt_hcpcs_code or "", item_b.cpt_hcpcs_code or "")
            if edit is None:
                continue
            component_item = item_b if edit.column2_code == item_b.cpt_hcpcs_code else item_a
            if component_item.line_item_id not in ncci_line_items_flagged:
                defects.append(
                    f"NCCI_UNBUNDLING: {edit.column1_code}/{edit.column2_code} pair on "
                    f"{component_item.service_date} was not flagged for line_item "
                    f"{component_item.line_item_id}. NoSurprisesActComplianceWorker must re-run."
                )
    return defects


def _check_citations(findings: list[ComplianceFinding]) -> list[str]:
    return [
        f"CITATION: finding {f.finding_id} cites {f.citation!r}, which is not in the statutory "
        "allow-list — NoSurprisesActComplianceWorker must re-run with a verified citation."
        for f in findings
        if not is_allowed_citation(f.citation)
    ]


def _check_provenance(
    findings: list[ComplianceFinding],
    benchmarks_by_code: dict[str, MRFBenchmark],
    denials_by_item: dict[str, list[DenialMapping]],
    line_items_by_id: dict[str, ClaimLineItem],
) -> list[str]:
    defects: list[str] = []
    for finding in findings:
        if finding.disputed_amount_cents <= 0:
            continue
        item = line_items_by_id.get(finding.line_item_id)
        has_benchmark = item is not None and item.cpt_hcpcs_code in benchmarks_by_code
        has_denial = bool(denials_by_item.get(finding.line_item_id))
        if not has_benchmark and not has_denial:
            defects.append(
                f"PROVENANCE: finding {finding.finding_id} disputes {finding.disputed_amount_cents} "
                "cents but traces to no MRFBenchmark or DenialMapping source record."
            )
    return defects


def build_evaluator_node(*, max_iterations: int):
    """Factory: bind `evaluator_max_iterations` (mandate default: 3) to the node fn."""

    async def actuarial_evaluator_node(state: EquiClaimState) -> dict[str, Any]:
        claim_id = state["claim_id"]
        iteration = state.get("eval_iteration", 0) + 1

        line_items = state.get("line_items", [])
        denials = state.get("denial_mappings", [])
        benchmarks = state.get("mrf_benchmarks", [])
        findings = state.get("compliance_findings", [])

        line_items_by_id = {i.line_item_id: i for i in line_items}
        denials_by_item: dict[str, list[DenialMapping]] = {}
        for d in denials:
            denials_by_item.setdefault(d.line_item_id, []).append(d)
        benchmarks_by_code = {b.cpt_hcpcs_code: b for b in benchmarks}

        math_defects = [
            *_check_reconciliation(line_items, denials_by_item),
            *_check_non_negativity(line_items, denials, benchmarks, findings),
            *_check_qpa_invariant(line_items, benchmarks_by_code, findings),
        ]
        statutory_defects = [
            *_check_ncci_invariant(line_items, findings),
            *_check_citations(findings),
            *_check_provenance(findings, benchmarks_by_code, denials_by_item, line_items_by_id),
        ]

        all_defects = math_defects + statutory_defects
        route_hint: RouteHint
        status: Literal["NEEDS_REVISION", "CERTIFIED", "FAILED"]

        if not all_defects:
            status = "CERTIFIED"
            route_hint = "finalize_docket"
            feedback = [
                f"[iteration {iteration}] CERTIFIED — all mathematical and statutory "
                "invariants passed."
            ]
        elif iteration >= max_iterations:
            status = "FAILED"
            route_hint = "manual_escalation"
            feedback = [
                f"[iteration {iteration}] FAILED — evaluator_max_iterations ({max_iterations}) "
                f"reached with {len(all_defects)} unresolved defect(s): " + "; ".join(all_defects)
            ]
        else:
            status = "NEEDS_REVISION"
            route_hint = "mrf_benchmark_worker" if math_defects else "nsa_compliance_worker"
            feedback = [f"[iteration {iteration}] NEEDS_REVISION ({route_hint}): {d}" for d in all_defects]

        logger.info(
            "actuarial_evaluator_node: claim=%s iteration=%d status=%s route=%s defects=%d",
            claim_id,
            iteration,
            status,
            route_hint,
            len(all_defects),
        )

        return {
            "eval_iteration": iteration,
            "eval_status": status,
            "eval_route_hint": route_hint,
            "eval_feedback": feedback,
        }

    return actuarial_evaluator_node


def route_after_evaluator(state: EquiClaimState) -> str:
    """Conditional-edge fn: route strictly by the evaluator's own `eval_route_hint`."""
    return state.get("eval_route_hint", "manual_escalation")
