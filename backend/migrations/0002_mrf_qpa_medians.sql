-- Materialized view: geographic median in-network negotiated rate per
-- (hospital_ccn, cpt_hcpcs_code) — this is the QPA proxy consumed by the
-- MRFBenchmarkWorker. Refresh after every MRF ingestion batch:
--   REFRESH MATERIALIZED VIEW CONCURRENTLY mrf_qpa_medians;

CREATE MATERIALIZED VIEW IF NOT EXISTS mrf_qpa_medians AS
SELECT
    hospital_ccn,
    cpt_hcpcs_code,
    (percentile_cont(0.5) WITHIN GROUP (
        ORDER BY negotiated_dollar_cents
    ))::BIGINT AS median_negotiated_cents,
    count(*) FILTER (WHERE negotiated_dollar_cents IS NOT NULL) AS payer_count_sampled,
    max(gross_charge_cents) AS max_gross_charge_cents,
    min(discounted_cash_cents) AS min_discounted_cash_cents
FROM mrf_line_items
WHERE negotiated_dollar_cents IS NOT NULL
GROUP BY hospital_ccn, cpt_hcpcs_code;

CREATE UNIQUE INDEX IF NOT EXISTS ux_mrf_qpa_medians_hospital_code
    ON mrf_qpa_medians (hospital_ccn, cpt_hcpcs_code);
