-- Phase 8 hardening: per-tenant hashed API keys (never store raw keys).
CREATE TABLE IF NOT EXISTS tenant_api_keys (
    key_id      TEXT PRIMARY KEY,
    tenant_id   TEXT NOT NULL REFERENCES tenants (tenant_id) ON DELETE CASCADE,
    key_hash    TEXT NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_tenant_api_keys_tenant ON tenant_api_keys (tenant_id);
