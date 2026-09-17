-- EquiClaim application schema (migration 0001).
--
-- This is intentionally separate from the `checkpoints` / `checkpoint_writes` /
-- `checkpoint_blobs` / `checkpoint_migrations` tables owned by
-- `AsyncPostgresSaver.setup()` — those are LangGraph-internal and are never
-- created or altered here. Same physical database, same connection pool,
-- disjoint table namespace.
--
-- All monetary columns are BIGINT cents. Never NUMERIC/FLOAT for money.

CREATE TABLE IF NOT EXISTS tenants (
    tenant_id   TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS hospitals (
    hospital_ccn        TEXT PRIMARY KEY,
    npi                 TEXT,
    name                TEXT NOT NULL,
    state               TEXT,
    mrf_source_url      TEXT,
    mrf_last_ingested_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS mrf_line_items (
    id                          BIGSERIAL PRIMARY KEY,
    hospital_ccn                TEXT NOT NULL REFERENCES hospitals (hospital_ccn) ON DELETE CASCADE,
    cpt_hcpcs_code               TEXT NOT NULL,
    code_type                   TEXT NOT NULL,
    description                 TEXT,
    gross_charge_cents          BIGINT,
    discounted_cash_cents       BIGINT,
    payer_name                  TEXT,
    plan_name                   TEXT,
    negotiated_dollar_cents     BIGINT,
    negotiated_percentage       NUMERIC(7, 4),
    negotiated_algorithm        TEXT,
    source_publish_date         DATE,
    ingested_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT mrf_line_items_nonneg CHECK (
        (gross_charge_cents IS NULL OR gross_charge_cents >= 0) AND
        (discounted_cash_cents IS NULL OR discounted_cash_cents >= 0) AND
        (negotiated_dollar_cents IS NULL OR negotiated_dollar_cents >= 0)
    )
);

CREATE INDEX IF NOT EXISTS ix_mrf_line_items_hospital_code
    ON mrf_line_items (hospital_ccn, cpt_hcpcs_code);

CREATE TABLE IF NOT EXISTS claims (
    claim_id     TEXT PRIMARY KEY,
    tenant_id    TEXT NOT NULL REFERENCES tenants (tenant_id) ON DELETE CASCADE,
    thread_id    TEXT NOT NULL UNIQUE,
    hospital_ccn TEXT REFERENCES hospitals (hospital_ccn),
    status       TEXT NOT NULL DEFAULT 'INTAKE' CHECK (
        status IN (
            'INTAKE', 'BENCHMARKING', 'COMPLIANCE_REVIEW', 'EVALUATING',
            'AWAITING_HUMAN_REVIEW', 'CERTIFIED', 'REJECTED', 'FAILED'
        )
    ),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_claims_tenant_status ON claims (tenant_id, status);

CREATE TABLE IF NOT EXISTS claim_documents (
    document_id       TEXT PRIMARY KEY,
    claim_id          TEXT NOT NULL REFERENCES claims (claim_id) ON DELETE CASCADE,
    file_ref          TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    content_type      TEXT NOT NULL,
    document_type     TEXT NOT NULL CHECK (document_type IN ('BILL', 'EOB', 'ITEMIZED_STATEMENT')),
    uploaded_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_claim_documents_claim ON claim_documents (claim_id);

CREATE TABLE IF NOT EXISTS audit_dockets (
    docket_id          TEXT PRIMARY KEY,
    claim_id           TEXT NOT NULL UNIQUE REFERENCES claims (claim_id) ON DELETE CASCADE,
    docket_json        JSONB NOT NULL,
    total_billed_cents BIGINT NOT NULL CHECK (total_billed_cents >= 0),
    total_disputed_cents BIGINT NOT NULL CHECK (total_disputed_cents >= 0),
    certified_at       TIMESTAMPTZ,
    human_decision     TEXT CHECK (human_decision IN ('PENDING', 'APPROVED', 'REJECTED', 'EDITED')),
    human_decided_at   TIMESTAMPTZ
);
