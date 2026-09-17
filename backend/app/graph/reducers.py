"""Custom LangGraph state-channel reducers.

The official Evaluator-Optimizer sample (docs.langchain.com/oss/python/langgraph/workflows-agents)
has no built-in de-duplication: it uses plain `operator.add` for list
channels. That is wrong for EquiClaim's `mrf_benchmarks` /
`compliance_findings` / `line_items` / `denial_mappings` channels, because
the evaluator-optimizer loop re-invokes a worker node up to
`evaluator_max_iterations` times — a naive append would leave stale/duplicate
entries from earlier, rejected passes sitting alongside the corrected ones.

These reducers implement **upsert** semantics instead: a worker's return
value replaces any existing item with the same identity key, and appends
anything new. Combined with LangGraph's `Annotated[list[T], reducer]`
channel mechanism, this gives correction-in-place across retries while still
being a pure, side-effect-free function LangGraph can call on every step.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


def _make_upsert_reducer(key_fn: Callable[[Any], Any]) -> Callable[[list[T], list[T]], list[T]]:
    """Build a reducer that merges `right` into `left`, keyed by `key_fn`."""

    def reducer(left: list[T] | None, right: list[T] | None) -> list[T]:
        left = list(left or [])
        right = list(right or [])
        by_key: dict[Any, T] = {key_fn(item): item for item in left}
        for item in right:
            by_key[key_fn(item)] = item
        return list(by_key.values())

    return reducer


# --- Concrete reducers, one per EquiClaimState list channel ---

upsert_line_items = _make_upsert_reducer(lambda item: item.line_item_id)
upsert_denial_mappings = _make_upsert_reducer(lambda item: item.denial_id)
upsert_mrf_benchmarks = _make_upsert_reducer(
    lambda item: (item.hospital_ccn, item.cpt_hcpcs_code)
)
upsert_compliance_findings = _make_upsert_reducer(lambda item: item.finding_id)


def append_unique(left: list[str] | None, right: list[str] | None) -> list[str]:
    """Append-only reducer for `eval_feedback` / `errors` audit-trail channels.

    Unlike `operator.add`, this still de-duplicates exact repeats (e.g. the
    same warning surfacing on two consecutive evaluator passes) without
    losing the historical ordering that makes the trail useful in the
    final docket's verification log.
    """
    left = list(left or [])
    right = list(right or [])
    seen = set(left)
    merged = list(left)
    for item in right:
        if item not in seen:
            merged.append(item)
            seen.add(item)
    return merged
