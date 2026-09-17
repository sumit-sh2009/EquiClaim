"""End-to-end API tests for `/claims` — Phase 6.

Uses Starlette's `TestClient`, which drives the real `lifespan` context
manager (so the pool/checkpointer/compiled graph are genuinely wired up
against the local Postgres instance) and executes `BackgroundTasks`
synchronously within each request/response cycle, so by the time a call
returns the corresponding graph step has already completed.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.core.config import get_settings
from app.ingestion.mrf_ingest import ingest_file
from app.main import app
from app.repositories.mrf_repository import MrfRepository

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
HOSPITAL_CCN = "450123"

AUTH_HEADERS = {
    "Authorization": f"Bearer {get_settings().api_shared_secret}",
    "X-Tenant-Id": "tenant-api-test",
}


async def _ensure_hospital_ingested() -> None:
    settings = get_settings()
    async with AsyncConnectionPool(
        conninfo=settings.database_url,
        min_size=1,
        max_size=2,
        kwargs={"autocommit": True, "row_factory": dict_row},
    ) as pool:
        repo = MrfRepository(pool)
        if await repo.get_hospital(hospital_ccn=HOSPITAL_CCN) is not None:
            return
        await ingest_file(
            pool=pool,
            hospital_ccn=HOSPITAL_CCN,
            hospital_name="Example Regional Medical Center",
            file_path=FIXTURES / "example_mrf_tall.csv",
        )


@pytest.fixture(scope="module")
def client() -> TestClient:
    asyncio.run(_ensure_hospital_ingested())
    with TestClient(app) as c:
        yield c


def test_create_claim_requires_auth(client: TestClient) -> None:
    resp = client.post("/claims", files=[], data={"document_types": []})
    assert resp.status_code == 401


def test_full_claim_lifecycle(client: TestClient) -> None:
    bill_bytes = (FIXTURES / "sample_bill.json").read_bytes()
    eob_bytes = (FIXTURES / "sample_eob.json").read_bytes()

    create_resp = client.post(
        "/claims",
        headers=AUTH_HEADERS,
        files=[
            ("files", ("sample_bill.json", bill_bytes, "application/json")),
            ("files", ("sample_eob.json", eob_bytes, "application/json")),
        ],
        data={"document_types": ["BILL", "EOB"], "hospital_ccn": HOSPITAL_CCN},
    )
    assert create_resp.status_code == 202, create_resp.text
    payload = create_resp.json()
    claim_id = payload["claim_id"]
    assert payload["status"] == "INTAKE"

    status_resp = client.get(f"/claims/{claim_id}/status", headers=AUTH_HEADERS)
    assert status_resp.status_code == 200, status_resp.text
    status_payload = status_resp.json()
    assert status_payload["status"] == "AWAITING_HUMAN_REVIEW"
    assert status_payload["eval_status"] == "CERTIFIED"
    assert status_payload["eval_iteration"] == 1

    list_resp = client.get("/claims", headers=AUTH_HEADERS)
    assert list_resp.status_code == 200
    assert any(c["claim_id"] == claim_id for c in list_resp.json()["claims"])

    resume_resp = client.post(
        f"/claims/{claim_id}/resume",
        headers=AUTH_HEADERS,
        json={"decision": "APPROVED", "reviewer": "reviewer@equiclaim.example"},
    )
    assert resume_resp.status_code == 200, resume_resp.text
    assert resume_resp.json()["status"] == "CERTIFIED"

    docket_resp = client.get(f"/claims/{claim_id}/docket", headers=AUTH_HEADERS)
    assert docket_resp.status_code == 200, docket_resp.text
    docket = docket_resp.json()
    assert docket["claim_id"] == claim_id
    assert docket["human_approval"]["decision"] == "APPROVED"
    assert docket["total_disputed_cents"] == 86_000 + 2_900 + 11_000


def test_double_resume_is_conflict(client: TestClient) -> None:
    """A claim already resumed (no longer `AWAITING_HUMAN_REVIEW`) must reject a second resume."""
    bill_bytes = (FIXTURES / "sample_bill.json").read_bytes()
    eob_bytes = (FIXTURES / "sample_eob.json").read_bytes()
    create_resp = client.post(
        "/claims",
        headers=AUTH_HEADERS,
        files=[
            ("files", ("sample_bill.json", bill_bytes, "application/json")),
            ("files", ("sample_eob.json", eob_bytes, "application/json")),
        ],
        data={"document_types": ["BILL", "EOB"], "hospital_ccn": HOSPITAL_CCN},
    )
    claim_id = create_resp.json()["claim_id"]

    first_resume = client.post(
        f"/claims/{claim_id}/resume", headers=AUTH_HEADERS, json={"decision": "APPROVED"}
    )
    assert first_resume.status_code == 200, first_resume.text

    second_resume = client.post(
        f"/claims/{claim_id}/resume", headers=AUTH_HEADERS, json={"decision": "APPROVED"}
    )
    assert second_resume.status_code == 409


def test_resume_unknown_claim_is_not_found(client: TestClient) -> None:
    resp = client.post(
        "/claims/00000000-0000-0000-0000-000000000000/resume",
        headers=AUTH_HEADERS,
        json={"decision": "APPROVED"},
    )
    assert resp.status_code == 404
