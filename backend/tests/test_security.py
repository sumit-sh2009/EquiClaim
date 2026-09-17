"""Auth + tenant-isolation tests — Phase 8 hardening.

Covers the `require_tenant` dependency (`app/core/security.py`) directly,
plus an end-to-end proof that one tenant can never read/act on another
tenant's claim through the `/claims` API, even with a valid credential.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from psycopg_pool import AsyncConnectionPool

from app.core.config import get_settings
from app.core.security import hash_api_key
from app.main import app
from app.repositories.claims_repository import ClaimsRepository
from app.repositories.tenant_keys_repository import TenantApiKeyRepository

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"

TENANT_A_HEADERS = {
    "Authorization": f"Bearer {get_settings().api_shared_secret}",
    "X-Tenant-Id": "tenant-security-a",
}
TENANT_B_HEADERS = {
    "Authorization": f"Bearer {get_settings().api_shared_secret}",
    "X-Tenant-Id": "tenant-security-b",
}


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def test_missing_authorization_header_is_401(client: TestClient) -> None:
    resp = client.get("/claims")
    assert resp.status_code == 401


def test_malformed_authorization_header_is_401(client: TestClient) -> None:
    resp = client.get("/claims", headers={"Authorization": "Basic notabearer"})
    assert resp.status_code == 401


def test_wrong_bearer_token_is_401(client: TestClient) -> None:
    resp = client.get(
        "/claims", headers={"Authorization": "Bearer wrong-secret", "X-Tenant-Id": "tenant-x"}
    )
    assert resp.status_code == 401


def test_dev_shared_secret_without_tenant_header_is_400(client: TestClient) -> None:
    resp = client.get(
        "/claims", headers={"Authorization": f"Bearer {get_settings().api_shared_secret}"}
    )
    assert resp.status_code == 400


def test_request_id_header_is_echoed(client: TestClient) -> None:
    resp = client.get("/claims", headers={**TENANT_A_HEADERS, "X-Request-Id": "abc-123"})
    assert resp.status_code == 200
    assert resp.headers["X-Request-Id"] == "abc-123"


def test_missing_request_id_is_generated(client: TestClient) -> None:
    resp = client.get("/claims", headers=TENANT_A_HEADERS)
    assert resp.status_code == 200
    assert resp.headers.get("X-Request-Id")


def test_tenant_cannot_see_other_tenants_claims(client: TestClient) -> None:
    bill_bytes = (FIXTURES / "sample_bill.json").read_bytes()

    create_resp = client.post(
        "/claims",
        headers=TENANT_A_HEADERS,
        files=[("files", ("sample_bill.json", bill_bytes, "application/json"))],
        data={"document_types": ["BILL"]},
    )
    assert create_resp.status_code == 202, create_resp.text
    claim_id = create_resp.json()["claim_id"]

    # Owning tenant can see it in the ledger and read its status.
    own_list = client.get("/claims", headers=TENANT_A_HEADERS).json()
    assert any(c["claim_id"] == claim_id for c in own_list["claims"])
    own_status = client.get(f"/claims/{claim_id}/status", headers=TENANT_A_HEADERS)
    assert own_status.status_code == 200

    # A different tenant, even with a structurally valid credential, gets a
    # 404 rather than any information leak — not a 403, so tenant B cannot
    # even confirm the claim id exists.
    other_status = client.get(f"/claims/{claim_id}/status", headers=TENANT_B_HEADERS)
    assert other_status.status_code == 404

    other_resume = client.post(
        f"/claims/{claim_id}/resume", headers=TENANT_B_HEADERS, json={"decision": "APPROVED"}
    )
    assert other_resume.status_code == 404

    other_docket = client.get(f"/claims/{claim_id}/docket", headers=TENANT_B_HEADERS)
    assert other_docket.status_code == 404

    other_list = client.get("/claims", headers=TENANT_B_HEADERS).json()
    assert all(c["claim_id"] != claim_id for c in other_list["claims"])


async def test_tenant_api_key_hash_lookup_and_revocation(pool: AsyncConnectionPool) -> None:
    """`TenantApiKeyRepository` never stores raw keys and honors revocation."""
    tenant_id = f"tenant-key-test-{uuid.uuid4()}"
    await ClaimsRepository(pool).ensure_tenant(tenant_id=tenant_id)

    keys_repo = TenantApiKeyRepository(pool)
    raw_key = f"sk-{uuid.uuid4()}"
    key_id = await keys_repo.issue_key(tenant_id=tenant_id, key_hash=hash_api_key(raw_key))

    assert await keys_repo.resolve_tenant_for_key(hash_api_key(raw_key)) == tenant_id
    assert await keys_repo.resolve_tenant_for_key(hash_api_key("some-other-key")) is None

    await keys_repo.revoke_key(key_id=key_id)
    assert await keys_repo.resolve_tenant_for_key(hash_api_key(raw_key)) is None
