"""`MRFBenchmarkWorker` — Phase 3.

For every distinct CPT/HCPCS code present on the claim's `line_items`,
looks up the pre-computed geographic median negotiated rate (the QPA proxy)
from `mrf_qpa_medians`, plus the gross/cash charge extremes, and emits one
`MRFBenchmark` per code. Requires database access, so it is built via a
factory function that closes over the shared `AsyncConnectionPool` (the
same pool backing the LangGraph checkpointer — see `app/db/pool.py`) rather
than being a bare module-level function; this keeps LangGraph nodes free of
global state while still allowing dependency injection of the pool at graph
build time (`app/graph/graph.py`).

On evaluator retry for a math defect, this worker is simply re-invoked with
the same `line_items`/`hospital_ccn` — since the upstream data hasn't
changed, the practical "correction" comes from the evaluator's feedback
prompting a different downstream interpretation in `NoSurprisesActComplianceWorker`.
If a future revision adds LLM-driven re-interpretation of ambiguous codes,
this is the seam where `state["eval_feedback"]` would be consulted.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import date
from typing import Any

from psycopg_pool import AsyncConnectionPool

from app.graph.state import EquiClaimState
from app.repositories.mrf_repository import MrfRepository, QpaMedianRow
from app.schemas.mrf_benchmark import MRFBenchmark

logger = logging.getLogger(__name__)

NodeFn = Callable[[EquiClaimState], Awaitable[dict[str, Any]]]


def _benchmark_from_median(
    *, hospital_ccn: str, code: str, median: QpaMedianRow, source_file_url: str
) -> MRFBenchmark | None:
    prices = (
        median.max_gross_charge_cents,
        median.min_discounted_cash_cents,
        median.median_negotiated_cents,
    )
    if all(p is None for p in prices):
        return None
    return MRFBenchmark(
        benchmark_id=f"{hospital_ccn}:{code}",
        hospital_ccn=hospital_ccn,
        cpt_hcpcs_code=code,
        code_type="CPT" if code.isdigit() else "HCPCS",
        gross_charge_cents=median.max_gross_charge_cents,
        discounted_cash_cents=median.min_discounted_cash_cents,
        median_negotiated_cents=median.median_negotiated_cents,
        payer_count_sampled=median.payer_count_sampled,
        source_file_url=source_file_url,
        source_publish_date=date.today(),
    )


def build_mrf_benchmark_worker(pool: AsyncConnectionPool) -> NodeFn:
    """Factory: bind the shared connection pool to a fresh `MRFBenchmarkWorker` node fn."""
    repo = MrfRepository(pool)

    async def mrf_benchmark_worker(state: EquiClaimState) -> dict[str, Any]:
        claim_id = state["claim_id"]
        hospital_ccn = state.get("hospital_ccn")
        codes = sorted(
            {item.cpt_hcpcs_code for item in state.get("line_items", []) if item.cpt_hcpcs_code}
        )

        if not hospital_ccn:
            return {
                "mrf_benchmarks": [],
                "errors": [f"claim {claim_id}: no hospital_ccn set, cannot benchmark against MRF data"],
            }
        if not codes:
            return {"mrf_benchmarks": [], "errors": []}

        hospital = await repo.get_hospital(hospital_ccn=hospital_ccn)
        source_file_url = hospital.mrf_source_url if hospital else "unknown"

        medians = await repo.get_qpa_medians_bulk(hospital_ccn=hospital_ccn, cpt_hcpcs_codes=codes)

        benchmarks: list[MRFBenchmark] = []
        errors: list[str] = []
        for code in codes:
            median = medians.get(code)
            if median is None:
                errors.append(
                    f"No MRF benchmark data found for hospital={hospital_ccn} code={code}"
                )
                continue
            benchmark = _benchmark_from_median(
                hospital_ccn=hospital_ccn,
                code=code,
                median=median,
                source_file_url=source_file_url or "unknown",
            )
            if benchmark is None:
                errors.append(f"MRF row for {hospital_ccn}/{code} had no usable price fields")
                continue
            benchmarks.append(benchmark)

        logger.info(
            "mrf_benchmark_worker: claim=%s hospital=%s benchmarks=%d errors=%d",
            claim_id,
            hospital_ccn,
            len(benchmarks),
            len(errors),
        )
        return {"mrf_benchmarks": benchmarks, "errors": errors}

    return mrf_benchmark_worker
