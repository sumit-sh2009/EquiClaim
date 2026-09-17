"""`MRFBenchmark` — internal, cents-exact benchmark derived from ingested
CMS Machine-Readable Files, used to compute the Qualifying Payment Amount
(QPA) proxy for a given CPT/HCPCS code at a given hospital.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, model_validator

from app.schemas.cms_mrf import CodeType


class MRFBenchmark(BaseModel):
    """Benchmark pricing for one CPT/HCPCS code at one hospital.

    `median_negotiated_cents` is the QPA proxy: the geographic median of
    in-network payer-specific negotiated rates for this code, computed by
    the MRF ingestion pipeline's `mrf_qpa_medians` materialized view.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    benchmark_id: str
    hospital_ccn: str
    cpt_hcpcs_code: str
    code_type: CodeType
    gross_charge_cents: int | None = None
    discounted_cash_cents: int | None = None
    median_negotiated_cents: int | None = None
    payer_count_sampled: int = 0
    source_file_url: str
    source_publish_date: date

    @model_validator(mode="after")
    def require_at_least_one_price(self) -> MRFBenchmark:
        prices = (
            self.gross_charge_cents,
            self.discounted_cash_cents,
            self.median_negotiated_cents,
        )
        if all(p is None for p in prices):
            raise ValueError(
                "at least one of gross_charge_cents, discounted_cash_cents, "
                "median_negotiated_cents must be populated"
            )
        for p in prices:
            if p is not None and p < 0:
                raise ValueError("charge cents fields must be >= 0")
        return self
