"""Tenant authentication.

Dev/Phase-6 implementation: a single shared bearer secret plus a caller-
supplied `X-Tenant-Id` header establishes tenant scoping for every request.
This intentionally does *not* trust the tenant id alone (any caller must
also present the shared secret) but does **not** yet provide per-tenant
isolation of secrets — see `app/core/security.py`'s Phase 8 upgrade note
below and `tests/test_security.py`.

Phase 8 hardening (implemented): per-tenant hashed API keys stored in the
`tenant_api_keys` table (see `migrations/0003_tenant_api_keys.sql`), so a
leaked/rotated key only affects one tenant. The shared-secret path remains
as a `local`/`development` environment fallback only and is refused outside
that environment.
"""

from __future__ import annotations

import hashlib
import hmac

from fastapi import Depends, Header, HTTPException, Request, status

from app.core.config import Settings, get_settings
from app.repositories.tenant_keys_repository import TenantApiKeyRepository


def hash_api_key(raw_key: str) -> str:
    """SHA-256 hash of a raw API key — never store raw keys at rest."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


async def require_tenant(
    request: Request,
    authorization: str | None = Header(default=None),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
    settings: Settings = Depends(get_settings),
) -> str:
    """Resolve and authorize the calling tenant for a request.

    Returns the authenticated `tenant_id`, or raises 401/403.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()

    # Development fallback: a single shared secret, refused outside dev/local.
    if settings.environment in ("development", "test") and hmac.compare_digest(
        token, settings.api_shared_secret
    ):
        if not x_tenant_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "X-Tenant-Id header required")
        request.state.tenant_id = x_tenant_id
        return x_tenant_id

    # Production path: hashed per-tenant API key lookup.
    repo = TenantApiKeyRepository(request.app.state.pool)
    tenant_id = await repo.resolve_tenant_for_key(hash_api_key(token))
    if tenant_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key")
    if x_tenant_id and x_tenant_id != tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "X-Tenant-Id does not match API key tenant")
    request.state.tenant_id = tenant_id
    return tenant_id
