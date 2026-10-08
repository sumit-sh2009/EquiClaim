"""End-to-end integration test of the compiled EquiClaim `StateGraph`.

This is simultaneously:

  1. **The Phase 1 gate** — proves the `interrupt_before=["finalize_docket"]`
     pause/resume mechanics work against a real `AsyncPostgresSaver`
     (`graph.ainvoke` pauses before `finalize_docket`; `graph.aupdate_state`
     + a second `graph.ainvoke(None, config)` resumes to `END`).
  2. **A full Phase 2-5 regression test** — the fixture bill/EOB pair is
     hand-constructed so every invariant should pass on the *first*
     evaluator pass against the ingested `fixtures/example_mrf_tall.csv`
     data. The `ingested_hospital` fixture loads that file when the hospital
     is not already present.

Requires a live Postgres reachable via `backend/.env` (`EQUICLAIM_DATABASE_URL`).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from psycopg_pool import AsyncConnectionPool

from app.graph.state import initial_state
from app.ingestion.mrf_ingest import ingest_file
from app.repositories.mrf_repository import MrfRepository
from app.schemas.claim import SourceDocument

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
HOSPITAL_CCN = "450123"


@pytest.fixture
def thread_id() -> str:
    return str(uuid.uuid4())


async def _ensure_hospital_ingested(pool: AsyncConnectionPool) -> None:
    repo = MrfRepository(pool)
    existing = await repo.get_hospital(hospital_ccn=HOSPITAL_CCN)
    if existing is not None:
        return
    await ingest_file(
        pool=pool,
        hospital_ccn=HOSPITAL_CCN,
        hospital_name="Example Regional Medical Center",
        file_path=FIXTURES / "example_mrf_tall.csv",
    )


def _source_documents(claim_id: str) -> list[SourceDocument]:
    now = datetime.now(UTC)
    return [
        SourceDocument(
            document_id=str(uuid.uuid4()),
            claim_id=claim_id,
            document_type="BILL",
            file_ref=str(FIXTURES / "sample_bill.json"),
            original_filename="sample_bill.json",
            content_type="application/json",
            uploaded_at=now,
        ),
        SourceDocument(
            document_id=str(uuid.uuid4()),
            claim_id=claim_id,
            document_type="EOB",
            file_ref=str(FIXTURES / "sample_eob.json"),
            original_filename="sample_eob.json",
            content_type="application/json",
            uploaded_at=now,
        ),
    ]


@pytest.mark.asyncio
async def test_graph_pauses_before_finalize_docket_then_certifies_on_first_pass(
    pool: AsyncConnectionPool, graph, thread_id: str
) -> None:
    await _ensure_hospital_ingested(pool)

    claim_id = thread_id
    state = initial_state(
        claim_id=claim_id, thread_id=thread_id, tenant_id="tenant-test", hospital_ccn=HOSPITAL_CCN
    )
    state["source_documents"] = _source_documents(claim_id)

    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 50}
    await graph.ainvoke(state, config)

    snapshot = await graph.aget_state(config)

    # --- Phase 1 gate: graph paused exactly before finalize_docket ---
    assert snapshot.next == ("finalize_docket",)

    values = snapshot.values
    assert values["eval_status"] == "CERTIFIED"
    assert values["eval_iteration"] == 1, (
        "fixture data was hand-reconciled to pass every invariant on the first pass; "
        f"got feedback: {values['eval_feedback']}"
    )
    assert values["audit_docket"] is None  # not yet assembled — that happens in finalize_docket

    findings_by_rule = {}
    for f in values["compliance_findings"]:
        findings_by_rule.setdefault(f.rule_type, []).append(f)

    # li1 (99284, emergency/OON): patient_responsibility 118000 - qpa 32000 = 86000
    # li2 (36415, emergency/OON): patient_responsibility 3700 - qpa 800 = 2900
    qpa_findings = {f.line_item_id: f for f in findings_by_rule.get("QPA_EXCEEDED", [])}
    assert len(qpa_findings) == 2
    li1_id = f"{claim_id}:li:1"
    li2_id = f"{claim_id}:li:2"
    li4_id = f"{claim_id}:li:4"
    assert qpa_findings[li1_id].disputed_amount_cents == 86_000
    assert qpa_findings[li1_id].citation == "45 CFR 149.120"
    assert qpa_findings[li2_id].disputed_amount_cents == 2_900

    # li4 (71045) is the NCCI-bundled component of li3 (71046).
    ncci_findings = findings_by_rule.get("NCCI_UNBUNDLING", [])
    assert len(ncci_findings) == 1
    assert ncci_findings[0].line_item_id == li4_id
    assert ncci_findings[0].disputed_amount_cents == 11_000

    # --- Resume past the HITL interrupt ---
    await graph.aupdate_state(
        config,
        {
            "human_decision": "APPROVED",
            "human_reviewer": "test-reviewer@equiclaim.example",
            "human_notes": "Approved in integration test.",
        },
    )
    await graph.ainvoke(None, config)

    final_snapshot = await graph.aget_state(config)
    assert final_snapshot.next == ()  # graph reached END

    docket = final_snapshot.values["audit_docket"]
    assert docket is not None
    assert docket.claim_id == claim_id
    assert docket.human_approval.decision == "APPROVED"
    assert docket.human_approval.approved_by == "test-reviewer@equiclaim.example"
    assert docket.total_billed_cents == 150_000 + 4_500 + 18_000 + 11_000
    assert docket.total_disputed_cents == 86_000 + 2_900 + 11_000
    assert "45 CFR 149.120" in docket.statutory_citations
    assert any("NCCI" in c for c in docket.statutory_citations)
    assert "FORMAL DISPUTE NOTICE" in docket.dispute_notice_text


@pytest.mark.asyncio
async def test_graph_finalize_docket_archives_on_rejection(
    pool: AsyncConnectionPool, graph, thread_id: str
) -> None:
    await _ensure_hospital_ingested(pool)

    claim_id = thread_id
    state = initial_state(
        claim_id=claim_id, thread_id=thread_id, tenant_id="tenant-test", hospital_ccn=HOSPITAL_CCN
    )
    state["source_documents"] = _source_documents(claim_id)
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 50}

    await graph.ainvoke(state, config)
    await graph.aupdate_state(config, {"human_decision": "REJECTED"})
    await graph.ainvoke(None, config)

    final_snapshot = await graph.aget_state(config)
    docket = final_snapshot.values["audit_docket"]
    assert docket.human_approval.decision == "REJECTED"
