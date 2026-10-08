"""Fixes from the backend review: re-ingest, orphaned runs, NCCI zero, dispute cap."""

from __future__ import annotations

import uuid
from datetime import date
from pathlib import Path

import pytest
from psycopg_pool import AsyncConnectionPool

from app.graph.nodes.finalize import _assemble_line_item_findings, _build_audit_docket
from app.graph.nodes.nsa_compliance import _ncci_unbundling_findings
from app.ingestion.mrf_ingest import DEMO_HOSPITAL_NAME, ingest_file
from app.repositories.claims_repository import ClaimsRepository
from app.repositories.mrf_repository import MrfRepository
from app.schemas.claim_line_item import ClaimLineItem
from app.schemas.compliance_finding import ComplianceFinding
from app.schemas.mrf_benchmark import MRFBenchmark

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
HOSPITAL_CCN = "450123"


def _line(**overrides: object) -> ClaimLineItem:
    defaults: dict[str, object] = dict(
        line_item_id="li_1",
        claim_id="claim_1",
        description="Chest x-ray",
        cpt_hcpcs_code="71045",
        code_type="CPT",
        units=1,
        billed_amount_cents=11_000,
        allowed_amount_cents=0,
        patient_responsibility_cents=0,
        service_date=date(2026, 1, 15),
        is_emergency=False,
        is_out_of_network=False,
    )
    defaults.update(overrides)
    return ClaimLineItem(**defaults)


def test_ncci_zero_allowed_does_not_dispute_the_billed_charge() -> None:
    findings = _ncci_unbundling_findings(
        "claim_1",
        [
            _line(
                line_item_id="li_col1",
                cpt_hcpcs_code="71046",
                billed_amount_cents=18_000,
                allowed_amount_cents=18_000,
            ),
            _line(line_item_id="li_col2", cpt_hcpcs_code="71045", allowed_amount_cents=0),
        ],
    )
    assert len(findings) == 1
    assert findings[0].disputed_amount_cents == 0


def test_stacked_findings_use_the_strongest_theory_capped_at_billed() -> None:
    item = _line(
        line_item_id="li_1",
        cpt_hcpcs_code="99284",
        billed_amount_cents=50_000,
        allowed_amount_cents=32_000,
        patient_responsibility_cents=18_000,
    )
    benchmark = MRFBenchmark(
        benchmark_id="b_1",
        hospital_ccn=HOSPITAL_CCN,
        cpt_hcpcs_code="99284",
        code_type="CPT",
        median_negotiated_cents=32_000,
        source_file_url="https://example.org/mrf.csv",
        source_publish_date=date(2026, 1, 1),
    )
    findings = [
        ComplianceFinding(
            finding_id="f_qpa",
            line_item_id="li_1",
            rule_type="QPA_EXCEEDED",
            citation="45 CFR 149.410",
            narrative="Patient share exceeds the QPA proxy.",
            disputed_amount_cents=80_000,
            confidence="HIGH",
        ),
        ComplianceFinding(
            finding_id="f_gouge",
            line_item_id="li_1",
            rule_type="MRF_PRICE_GOUGING",
            citation="45 CFR 180.50",
            narrative="Billed amount exceeds the published gross charge.",
            disputed_amount_cents=20_000,
            confidence="MEDIUM",
        ),
    ]
    assembled = _assemble_line_item_findings([item], findings, [], [benchmark])
    assert assembled[0].disputed_amount_cents == 50_000
    assert assembled[0].compliance_finding is not None
    assert assembled[0].compliance_finding.finding_id == "f_qpa"


def test_preview_docket_does_not_claim_certification_before_the_evaluator() -> None:
    docket = _build_audit_docket(
        {"claim_id": "claim_1", "eval_status": "FAILED", "eval_iteration": 1},
        decision="PENDING",
    )
    assert docket.evaluator_certification.passed_checks == []

    certified = _build_audit_docket(
        {"claim_id": "claim_1", "eval_status": "CERTIFIED", "eval_iteration": 1},
        decision="PENDING",
    )
    assert "reconciliation" in certified.evaluator_certification.passed_checks


@pytest.mark.asyncio
async def test_reingest_does_not_move_the_qpa_median(pool: AsyncConnectionPool) -> None:
    repo = MrfRepository(pool)
    file_path = FIXTURES / "example_mrf_tall.csv"
    first = await ingest_file(
        pool=pool,
        hospital_ccn=HOSPITAL_CCN,
        hospital_name=DEMO_HOSPITAL_NAME,
        file_path=file_path,
    )
    count_before = await repo.count_line_items(hospital_ccn=HOSPITAL_CCN)
    median_before = await repo.get_qpa_median(hospital_ccn=HOSPITAL_CCN, cpt_hcpcs_code="99284")
    second = await ingest_file(
        pool=pool,
        hospital_ccn=HOSPITAL_CCN,
        hospital_name=DEMO_HOSPITAL_NAME,
        file_path=file_path,
    )
    count_after = await repo.count_line_items(hospital_ccn=HOSPITAL_CCN)
    median_after = await repo.get_qpa_median(hospital_ccn=HOSPITAL_CCN, cpt_hcpcs_code="99284")

    assert first.inserted_rows == second.inserted_rows
    assert count_before == count_after == second.inserted_rows
    assert median_before is not None and median_after is not None
    assert median_before.median_negotiated_cents == median_after.median_negotiated_cents
    assert median_before.payer_count_sampled == median_after.payer_count_sampled


@pytest.mark.asyncio
async def test_orphan_sweep_fails_in_flight_runs_and_keeps_review(pool: AsyncConnectionPool) -> None:
    repo = ClaimsRepository(pool)
    tenant_id = f"tenant-orphan-{uuid.uuid4()}"
    await repo.ensure_tenant(tenant_id=tenant_id)

    intake = await repo.create_claim(
        claim_id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        thread_id=str(uuid.uuid4()),
        hospital_ccn=None,
    )
    waiting_id = str(uuid.uuid4())
    await repo.create_claim(
        claim_id=waiting_id,
        tenant_id=tenant_id,
        thread_id=str(uuid.uuid4()),
        hospital_ccn=None,
    )
    await repo.update_status(claim_id=waiting_id, status="AWAITING_HUMAN_REVIEW")
    resuming_id = str(uuid.uuid4())
    await repo.create_claim(
        claim_id=resuming_id,
        tenant_id=tenant_id,
        thread_id=str(uuid.uuid4()),
        hospital_ccn=None,
    )
    await repo.update_status(claim_id=resuming_id, status="RESUMING")

    failed = await repo.fail_orphaned_runs()
    assert failed >= 2
    intake_row = await repo.get_claim(claim_id=intake.claim_id, tenant_id=tenant_id)
    resuming_row = await repo.get_claim(claim_id=resuming_id, tenant_id=tenant_id)
    waiting = await repo.get_claim(claim_id=waiting_id, tenant_id=tenant_id)
    assert intake_row is not None and intake_row.status == "FAILED"
    assert resuming_row is not None and resuming_row.status == "FAILED"
    assert waiting is not None and waiting.status == "AWAITING_HUMAN_REVIEW"
