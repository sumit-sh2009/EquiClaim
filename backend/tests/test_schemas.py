"""Unit tests for the Pydantic v2 data contracts in `app.schemas`.

These tests exist primarily to lock in the cent-exact-arithmetic and
statutory-citation invariants described in the architectural blueprint —
i.e. that it is *impossible* to construct a model instance that violates
them, not just that the "happy path" works.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from app.domain.citations import ALLOWED_CITATIONS
from app.schemas import (
    AuditDocket,
    ClaimLineItem,
    CmsMrfTallChargeSlice,
    ComplianceFinding,
    DenialMapping,
    EvaluatorCertification,
    LineItemFinding,
    MRFBenchmark,
)

# --------------------------------------------------------------------------
# ClaimLineItem
# --------------------------------------------------------------------------


def make_line_item(**overrides: object) -> ClaimLineItem:
    defaults: dict[str, object] = dict(
        line_item_id="li_1",
        claim_id="claim_1",
        description="Emergency room visit, level 4",
        cpt_hcpcs_code="99284",
        code_type="CPT",
        units=1,
        billed_amount_cents=250_00,
        service_date=date(2026, 1, 15),
        is_emergency=True,
    )
    defaults.update(overrides)
    return ClaimLineItem(**defaults)  # type: ignore[arg-type]


def test_claim_line_item_valid_construction() -> None:
    item = make_line_item()
    assert item.billed_amount_cents == 25_000
    assert item.units == 1


def test_claim_line_item_rejects_negative_billed_amount() -> None:
    with pytest.raises(ValidationError):
        make_line_item(billed_amount_cents=-1)


def test_claim_line_item_rejects_zero_units() -> None:
    with pytest.raises(ValidationError):
        make_line_item(units=0)


def test_claim_line_item_rejects_negative_patient_responsibility() -> None:
    with pytest.raises(ValidationError):
        make_line_item(patient_responsibility_cents=-500)


def test_claim_line_item_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        make_line_item(unexpected_field="nope")


# --------------------------------------------------------------------------
# DenialMapping
# --------------------------------------------------------------------------


def test_denial_mapping_rejects_negative_adjustment() -> None:
    with pytest.raises(ValidationError):
        DenialMapping(
            denial_id="d_1",
            line_item_id="li_1",
            carc_code="45",
            carc_description="Charge exceeds fee schedule/maximum allowable",
            group_code="CO",
            adjustment_amount_cents=-100,
        )


def test_denial_mapping_valid() -> None:
    denial = DenialMapping(
        denial_id="d_1",
        line_item_id="li_1",
        carc_code="45",
        carc_description="Charge exceeds fee schedule/maximum allowable",
        group_code="CO",
        adjustment_amount_cents=1500,
    )
    assert denial.adjustment_amount_cents == 1500


# --------------------------------------------------------------------------
# MRFBenchmark
# --------------------------------------------------------------------------


def test_mrf_benchmark_requires_at_least_one_price() -> None:
    with pytest.raises(ValidationError):
        MRFBenchmark(
            benchmark_id="b_1",
            hospital_ccn="450123",
            cpt_hcpcs_code="99284",
            code_type="CPT",
            source_file_url="https://example.org/mrf.json",
            source_publish_date=date(2026, 1, 1),
        )


def test_mrf_benchmark_valid_with_one_price() -> None:
    benchmark = MRFBenchmark(
        benchmark_id="b_1",
        hospital_ccn="450123",
        cpt_hcpcs_code="99284",
        code_type="CPT",
        median_negotiated_cents=32_000,
        source_file_url="https://example.org/mrf.json",
        source_publish_date=date(2026, 1, 1),
    )
    assert benchmark.median_negotiated_cents == 32_000


def test_mrf_benchmark_rejects_negative_price() -> None:
    with pytest.raises(ValidationError):
        MRFBenchmark(
            benchmark_id="b_1",
            hospital_ccn="450123",
            cpt_hcpcs_code="99284",
            code_type="CPT",
            median_negotiated_cents=-1,
            source_file_url="https://example.org/mrf.json",
            source_publish_date=date(2026, 1, 1),
        )


# --------------------------------------------------------------------------
# CMS ingestion boundary
# --------------------------------------------------------------------------


def test_cms_tall_slice_requires_code_and_type_together() -> None:
    with pytest.raises(ValidationError):
        CmsMrfTallChargeSlice.model_validate({"code|1": "99284"})


def test_cms_tall_slice_parses_pipe_headers_and_converts_to_cents() -> None:
    row = {
        "code|1": "99284",
        "code|1|type": "CPT",
        "standard_charge|gross": "1250.55",
        "standard_charge|negotiated_dollar": "320.00",
    }
    slice_ = CmsMrfTallChargeSlice.model_validate(row)
    assert slice_.code_1_type == "CPT"
    assert slice_.to_cents(slice_.standard_charge_gross) == 125_055
    assert slice_.to_cents(slice_.standard_charge_negotiated_dollar) == 32_000
    assert slice_.to_cents(None) is None


# --------------------------------------------------------------------------
# ComplianceFinding — citation allow-list
# --------------------------------------------------------------------------


def test_compliance_finding_rejects_hallucinated_citation() -> None:
    with pytest.raises(ValidationError):
        ComplianceFinding(
            finding_id="f_1",
            line_item_id="li_1",
            rule_type="QPA_EXCEEDED",
            citation="45 CFR 999.999",  # does not exist
            narrative="Fabricated citation.",
            disputed_amount_cents=1000,
        )


def test_compliance_finding_accepts_allow_listed_citation() -> None:
    citation = "45 CFR 149.410"
    assert citation in ALLOWED_CITATIONS
    finding = ComplianceFinding(
        finding_id="f_1",
        line_item_id="li_1",
        rule_type="QPA_EXCEEDED",
        citation=citation,
        narrative="Patient responsibility exceeds the QPA for this emergency service.",
        disputed_amount_cents=5000,
    )
    assert finding.citation == citation


# --------------------------------------------------------------------------
# AuditDocket — cent-exact totals + provenance
# --------------------------------------------------------------------------


def _certification() -> EvaluatorCertification:
    return EvaluatorCertification(
        iteration_count=1,
        passed_checks=["reconciliation", "qpa_cap", "citation_allow_list"],
        certified_at=datetime.now(UTC),
    )


def test_line_item_finding_rejects_disputed_amount_without_evidence() -> None:
    with pytest.raises(ValidationError):
        LineItemFinding(
            line_item=make_line_item(),
            disputed_amount_cents=100,  # non-zero but no denial_mapping/mrf_benchmark
        )


def test_line_item_finding_allows_zero_disputed_without_evidence() -> None:
    finding = LineItemFinding(line_item=make_line_item(), disputed_amount_cents=0)
    assert finding.disputed_amount_cents == 0


def test_audit_docket_rejects_mismatched_totals() -> None:
    benchmark = MRFBenchmark(
        benchmark_id="b_1",
        hospital_ccn="450123",
        cpt_hcpcs_code="99284",
        code_type="CPT",
        median_negotiated_cents=20_000,
        source_file_url="https://example.org/mrf.json",
        source_publish_date=date(2026, 1, 1),
    )
    line_item_finding = LineItemFinding(
        line_item=make_line_item(),
        mrf_benchmark=benchmark,
        disputed_amount_cents=5_000,
    )
    with pytest.raises(ValidationError):
        AuditDocket(
            docket_id="dk_1",
            claim_id="claim_1",
            generated_at=datetime.now(UTC),
            line_item_findings=[line_item_finding],
            total_billed_cents=25_000,
            total_disputed_cents=9_999,  # wrong on purpose — must equal 5_000
            statutory_citations=["45 CFR 149.410"],
            evaluator_certification=_certification(),
            dispute_notice_text="...",
        )


def test_audit_docket_accepts_reconciled_totals() -> None:
    benchmark = MRFBenchmark(
        benchmark_id="b_1",
        hospital_ccn="450123",
        cpt_hcpcs_code="99284",
        code_type="CPT",
        median_negotiated_cents=20_000,
        source_file_url="https://example.org/mrf.json",
        source_publish_date=date(2026, 1, 1),
    )
    line_item_finding = LineItemFinding(
        line_item=make_line_item(),
        mrf_benchmark=benchmark,
        disputed_amount_cents=5_000,
    )
    docket = AuditDocket(
        docket_id="dk_1",
        claim_id="claim_1",
        generated_at=datetime.now(UTC),
        line_item_findings=[line_item_finding],
        total_billed_cents=25_000,
        total_disputed_cents=5_000,
        statutory_citations=["45 CFR 149.410"],
        evaluator_certification=_certification(),
        dispute_notice_text="Formal dispute notice text.",
    )
    assert docket.total_disputed_cents == 5_000


def test_line_item_finding_rejects_dispute_above_billed() -> None:
    with pytest.raises(ValidationError, match="billed_amount_cents"):
        LineItemFinding(
            line_item=make_line_item(billed_amount_cents=25_000),
            mrf_benchmark=MRFBenchmark(
                benchmark_id="b_1",
                hospital_ccn="450123",
                cpt_hcpcs_code="99284",
                code_type="CPT",
                median_negotiated_cents=20_000,
                source_file_url="https://example.org/mrf.json",
                source_publish_date=date(2026, 1, 1),
            ),
            disputed_amount_cents=25_001,
        )
