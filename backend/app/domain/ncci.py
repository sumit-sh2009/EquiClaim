"""National Correct Coding Initiative (NCCI) Procedure-to-Procedure (PTP)
edits — a curated seed table used to detect improper "unbundling" (billing
a comprehensive procedure's bundled components as separate, additional
line items on the same date of service).

The full CMS NCCI PTP edit file (Column 1 / Column 2 / Modifier Indicator)
is published quarterly at
https://www.cms.gov/medicare/coding-billing/national-correct-coding-initiative-ncci-edits
and contains tens of thousands of pairs. This module ships a small,
representative seed set plus the exact lookup contract
(`find_ptp_edit`) so swapping in the full CMS file later (Phase 3/4
ingestion extension) requires no changes to `NoSurprisesActComplianceWorker`.

Modifier indicator semantics (CMS-official):
  - `0`: the edit cannot be bypassed by any modifier — billing both codes on
    the same date is *always* improper unbundling.
  - `1`: the edit *can* be bypassed with an appropriate NCCI-associated
    modifier (e.g. `-59`) if clinical circumstances justify it.
  - `9`: the edit is not applicable (informational placeholder in the CMS file).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PtpEdit:
    column1_code: str  # the comprehensive/primary code
    column2_code: str  # the component code bundled into column1
    modifier_indicator: int  # 0, 1, or 9 — see module docstring
    rationale: str


# Seed table — representative pairs commonly implicated in ED/inpatient unbundling disputes.
_PTP_EDITS: list[PtpEdit] = [
    PtpEdit("99284", "99283", 0, "Lower-level E/M service is bundled into the billed higher level."),
    PtpEdit("29881", "29870", 0, "Diagnostic arthroscopy is bundled into surgical arthroscopy same joint."),
    PtpEdit("36415", "99284", 1, "Routine venipuncture is bundled into the E/M visit absent a modifier."),
    PtpEdit("71046", "71045", 0, "Single-view chest X-ray is bundled into the 2-view study."),
    PtpEdit("80053", "80048", 0, "Basic metabolic panel is a component of the comprehensive panel."),
]

_INDEX: dict[tuple[str, str], PtpEdit] = {
    (edit.column1_code, edit.column2_code): edit for edit in _PTP_EDITS
}


def find_ptp_edit(code_a: str, code_b: str) -> PtpEdit | None:
    """Return the PTP edit for an unordered pair of codes billed same-day, if any."""
    return _INDEX.get((code_a, code_b)) or _INDEX.get((code_b, code_a))


def is_unbundling_violation(code_a: str, code_b: str) -> PtpEdit | None:
    """Return the edit iff billing both codes together is *always* improper (indicator 0)."""
    edit = find_ptp_edit(code_a, code_b)
    if edit is not None and edit.modifier_indicator == 0:
        return edit
    return None
