"""`NoSurprisesActComplianceWorker` — Phase 4.

Pure function of state (no DB access — `mrf_benchmarks` were already
resolved by `MRFBenchmarkWorker`). Cross-references `line_items`,
`denial_mappings`, and `mrf_benchmarks` against:

  - **No Surprises Act QPA cap** (45 CFR § 149.410/.120/.130): for
    emergency or protected out-of-network line items, patient
    responsibility may not exceed the Qualifying Payment Amount (QPA)
    proxy — the geographic median in-network negotiated rate.
  - **NCCI unbundling** (`app.domain.ncci`): same-date-of-service CPT pairs
    matching a Procedure-to-Procedure edit with modifier indicator 0.
  - **MRF price-gouging** (45 CFR § 180.50): billed amounts wildly in
    excess of the hospital's own published gross charge, evidencing
    inflated or fabricated line-item pricing.

Every `ComplianceFinding` constructed here carries a citation drawn
exclusively from `app.domain.citations.ALLOWED_CITATIONS` — the Pydantic
model itself refuses construction otherwise, so this worker cannot emit a
hallucinated statute even if its own logic has a bug.
"""

from __future__ import annotations

import logging
from itertools import combinations
from typing import Any

from app.domain.ncci import is_unbundling_violation
from app.graph.state import EquiClaimState
from app.schemas.claim_line_item import ClaimLineItem
from app.schemas.compliance_finding import ComplianceFinding
from app.schemas.denial_mapping import DenialMapping
from app.schemas.mrf_benchmark import MRFBenchmark

logger = logging.getLogger(__name__)

# Billed-vs-gross-charge multiplier past which we flag price-gouging risk.
_GROSS_CHARGE_GOUGING_MULTIPLIER = 1.5


def _finding_id(claim_id: str, rule_type: str, line_item_id: str, suffix: str = "") -> str:
    return f"{claim_id}:cf:{rule_type}:{line_item_id}{(':' + suffix) if suffix else ''}"


def _qpa_exceeded_findings(
    claim_id: str,
    line_items: list[ClaimLineItem],
    benchmarks_by_code: dict[str, MRFBenchmark],
    denials_by_line_item: dict[str, list[DenialMapping]],
) -> list[ComplianceFinding]:
    findings: list[ComplianceFinding] = []
    for item in line_items:
        if not (item.is_emergency or item.is_out_of_network):
            continue
        if item.patient_responsibility_cents is None or item.patient_responsibility_cents <= 0:
            continue

        benchmark = benchmarks_by_code.get(item.cpt_hcpcs_code or "")
        if benchmark is not None and benchmark.median_negotiated_cents is not None:
            qpa = benchmark.median_negotiated_cents
            if item.patient_responsibility_cents > qpa:
                overage = item.patient_responsibility_cents - qpa
                citation = "45 CFR 149.120" if item.is_emergency else "45 CFR 149.130"
                findings.append(
                    ComplianceFinding(
                        finding_id=_finding_id(claim_id, "QPA_EXCEEDED", item.line_item_id),
                        line_item_id=item.line_item_id,
                        rule_type="QPA_EXCEEDED",
                        citation=citation,
                        narrative=(
                            f"Patient responsibility of {item.patient_responsibility_cents} "
                            f"cents exceeds the Qualifying Payment Amount proxy of {qpa} cents "
                            f"(geographic median in-network rate for {item.cpt_hcpcs_code}) by "
                            f"{overage} cents, in violation of the No Surprises Act balance-"
                            "billing cap for emergency/protected out-of-network services."
                        ),
                        disputed_amount_cents=overage,
                        confidence="HIGH",
                    )
                )
                continue  # QPA-quantified finding supersedes the provisional one below

        # No MRF benchmark available for this code — flag as provisionally protected
        # balance billing (full patient responsibility disputed) rather than silently
        # skipping the invariant, since absent MRF data is itself a transparency failure.
        pr_denials = [d for d in denials_by_line_item.get(item.line_item_id, []) if d.group_code == "PR"]
        if pr_denials:
            findings.append(
                ComplianceFinding(
                    finding_id=_finding_id(claim_id, "NSA_BALANCE_BILL_PROHIBITED", item.line_item_id),
                    line_item_id=item.line_item_id,
                    rule_type="NSA_BALANCE_BILL_PROHIBITED",
                    citation="45 CFR 149.410",
                    narrative=(
                        "Emergency/protected out-of-network line item carries patient "
                        "responsibility but no Qualifying Payment Amount benchmark could be "
                        "resolved (hospital MRF data unavailable or not yet ingested for this "
                        "code) — the full patient-responsibility amount is provisionally "
                        "disputed pending QPA calculation."
                    ),
                    disputed_amount_cents=item.patient_responsibility_cents,
                    confidence="MEDIUM",
                )
            )
    return findings


def _ncci_unbundling_findings(
    claim_id: str, line_items: list[ClaimLineItem]
) -> list[ComplianceFinding]:
    findings: list[ComplianceFinding] = []
    by_date: dict[Any, list[ClaimLineItem]] = {}
    for item in line_items:
        if item.cpt_hcpcs_code:
            by_date.setdefault(item.service_date, []).append(item)

    for _service_date, items in by_date.items():
        for item_a, item_b in combinations(items, 2):
            edit = is_unbundling_violation(item_a.cpt_hcpcs_code or "", item_b.cpt_hcpcs_code or "")
            if edit is None:
                continue
            # The component (column2) code is the one improperly billed as separate.
            component_item = item_b if edit.column2_code == item_b.cpt_hcpcs_code else item_a
            allowed = component_item.allowed_amount_cents
            # ``0`` is a real allowed amount. A truthiness check would dispute
            # the full billed charge after the payer already adjusted it to zero.
            disputed = component_item.billed_amount_cents if allowed is None else allowed
            findings.append(
                ComplianceFinding(
                    finding_id=_finding_id(
                        claim_id, "NCCI_UNBUNDLING", component_item.line_item_id, edit.column1_code
                    ),
                    line_item_id=component_item.line_item_id,
                    rule_type="NCCI_UNBUNDLING",
                    citation="NCCI PTP Edits — CMS Medicare NCCI Policy Manual Ch. I.A",
                    narrative=(
                        f"CPT {edit.column2_code} is a component of CPT {edit.column1_code} "
                        f"under an NCCI Procedure-to-Procedure edit with modifier indicator 0 "
                        f"(no bypass permitted). {edit.rationale}"
                    ),
                    disputed_amount_cents=disputed,
                    confidence="HIGH",
                )
            )
    return findings


def _price_gouging_findings(
    claim_id: str, line_items: list[ClaimLineItem], benchmarks_by_code: dict[str, MRFBenchmark]
) -> list[ComplianceFinding]:
    findings: list[ComplianceFinding] = []
    for item in line_items:
        benchmark = benchmarks_by_code.get(item.cpt_hcpcs_code or "")
        if benchmark is None or benchmark.gross_charge_cents is None:
            continue
        threshold = benchmark.gross_charge_cents * _GROSS_CHARGE_GOUGING_MULTIPLIER
        if item.billed_amount_cents > threshold:
            excess = item.billed_amount_cents - benchmark.gross_charge_cents
            findings.append(
                ComplianceFinding(
                    finding_id=_finding_id(claim_id, "MRF_PRICE_GOUGING", item.line_item_id),
                    line_item_id=item.line_item_id,
                    rule_type="MRF_PRICE_GOUGING",
                    citation="45 CFR 180.50",
                    narrative=(
                        f"Billed amount of {item.billed_amount_cents} cents exceeds "
                        f"{_GROSS_CHARGE_GOUGING_MULTIPLIER}x the hospital's own MRF-published "
                        f"gross charge of {benchmark.gross_charge_cents} cents for "
                        f"{item.cpt_hcpcs_code}, evidencing a discrepancy with the hospital's "
                        "own required price-transparency disclosure."
                    ),
                    disputed_amount_cents=excess,
                    confidence="MEDIUM",
                )
            )
    return findings


async def nsa_compliance_worker(state: EquiClaimState) -> dict[str, Any]:
    """Audit `line_items`/`denial_mappings`/`mrf_benchmarks` for statutory violations."""
    claim_id = state["claim_id"]
    line_items = state.get("line_items", [])
    benchmarks_by_code = {b.cpt_hcpcs_code: b for b in state.get("mrf_benchmarks", [])}
    denials_by_line_item: dict[str, list[DenialMapping]] = {}
    for denial in state.get("denial_mappings", []):
        denials_by_line_item.setdefault(denial.line_item_id, []).append(denial)

    findings: list[ComplianceFinding] = []
    findings.extend(_qpa_exceeded_findings(claim_id, line_items, benchmarks_by_code, denials_by_line_item))
    findings.extend(_ncci_unbundling_findings(claim_id, line_items))
    findings.extend(_price_gouging_findings(claim_id, line_items, benchmarks_by_code))

    logger.info(
        "nsa_compliance_worker: claim=%s findings=%d (qpa/nsa=%d, ncci=%d, gouging=%d)",
        claim_id,
        len(findings),
        sum(1 for f in findings if f.rule_type in ("QPA_EXCEEDED", "NSA_BALANCE_BILL_PROHIBITED")),
        sum(1 for f in findings if f.rule_type == "NCCI_UNBUNDLING"),
        sum(1 for f in findings if f.rule_type == "MRF_PRICE_GOUGING"),
    )
    return {"compliance_findings": findings}
