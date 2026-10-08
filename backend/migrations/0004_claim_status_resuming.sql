-- Resume holds the row in RESUMING until finalize saves the docket.
-- The original CHECK is inline on claims.status (claims_status_check).
DO $$
DECLARE
    constraint_name text;
BEGIN
    SELECT con.conname INTO constraint_name
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'claims'
      AND con.contype = 'c'
      AND pg_get_constraintdef(con.oid) ILIKE '%AWAITING_HUMAN_REVIEW%';
    IF constraint_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE claims DROP CONSTRAINT %I', constraint_name);
    END IF;
END $$;

ALTER TABLE claims ADD CONSTRAINT claims_status_check CHECK (
    status IN (
        'INTAKE', 'BENCHMARKING', 'COMPLIANCE_REVIEW', 'EVALUATING',
        'AWAITING_HUMAN_REVIEW', 'RESUMING', 'CERTIFIED', 'REJECTED', 'FAILED'
    )
);
