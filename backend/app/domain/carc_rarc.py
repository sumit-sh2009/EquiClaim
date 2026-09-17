"""CARC (Claim Adjustment Reason Code) / RARC (Remittance Advice Remark Code)
reference data.

Source of truth for the full, authoritative lists is the X12 external code
list (https://x12.org/codes/claim-adjustment-reason-codes and
.../remittance-advice-remark-codes), which changes quarterly and is
maintained by the Washington Publishing Company. EquiClaim ships a curated
subset covering the codes most frequently implicated in No Surprises Act /
balance-billing disputes and NCCI unbundling denials; anything outside this
set still round-trips through `DenialMapping` with a generic description
rather than failing intake, but is flagged in `errors` so a human/future
sync job can extend the table.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CarcInfo:
    description: str
    # Group code this CARC is most commonly reported under (informational default;
    # the actual EOB-reported group code always wins if present in the source document).
    typical_group_code: str


CARC_CODES: dict[str, CarcInfo] = {
    "1": CarcInfo("Deductible amount.", "PR"),
    "2": CarcInfo("Coinsurance amount.", "PR"),
    "3": CarcInfo("Co-payment amount.", "PR"),
    "16": CarcInfo("Claim/service lacks information needed for adjudication.", "CO"),
    "18": CarcInfo("Exact duplicate claim/service.", "CO"),
    "22": CarcInfo(
        "This care may be covered by another payer per coordination of benefits.", "OA"
    ),
    "23": CarcInfo(
        "The impact of prior payer(s) adjudication, including payments and/or adjustments.",
        "OA",
    ),
    "24": CarcInfo(
        "Charges are covered under a capitation agreement/managed care plan.", "CO"
    ),
    "29": CarcInfo("The time limit for filing has expired.", "CO"),
    "45": CarcInfo(
        "Charge exceeds fee schedule/maximum allowable or contracted/legislated fee "
        "arrangement. (NOTE: this CARC directly implicates the QPA cap under the No "
        "Surprises Act when applied to emergency or protected out-of-network services.)",
        "CO",
    ),
    "49": CarcInfo("This is a non-covered service because it is a routine exam.", "PR"),
    "50": CarcInfo(
        "These are non-covered services because this is not deemed a medical necessity.",
        "PR",
    ),
    "96": CarcInfo("Non-covered charge(s).", "PR"),
    "97": CarcInfo(
        "The benefit for this service is included in the payment/allowance for another "
        "service/procedure that has already been adjudicated. (NCCI bundling indicator.)",
        "CO",
    ),
    "109": CarcInfo(
        "Claim/service not covered by this payer/contractor. You must send the claim/"
        "service to the correct payer/contractor.",
        "OA",
    ),
    "119": CarcInfo("Benefit maximum for this time period or occurrence has been reached.", "PR"),
    "151": CarcInfo(
        "Payment adjusted because the payer deems the information submitted does not "
        "support this many/frequency of services.",
        "CO",
    ),
    "197": CarcInfo(
        "Precertification/authorization/notification/pre-treatment absent.", "CO"
    ),
    "198": CarcInfo("Precertification/authorization exceeded.", "CO"),
    "204": CarcInfo(
        "This service/equipment/drug is not covered under the patient's current benefit "
        "plan.",
        "PR",
    ),
    "236": CarcInfo(
        "This procedure or procedure/modifier combination is not compatible with another "
        "procedure or procedure/modifier combination provided on the same day. (NCCI PTP "
        "edit — direct unbundling signal.)",
        "CO",
    ),
    "245": CarcInfo(
        "Provider performance program withhold.", "CO"
    ),
    "A1": CarcInfo("Claim/Service denied.", "CO"),
    "B7": CarcInfo(
        "This provider was not certified/eligible to be paid for this procedure/service "
        "on this date of service.",
        "CO",
    ),
}

# A representative subset of RARCs relevant to balance-billing/NSA disputes.
RARC_CODES: dict[str, str] = {
    "N130": "Consult plan benefit documents/guidelines for information about restrictions "
    "for this service.",
    "N362": "The number of Days or Units of Service exceeds our acceptable maximum.",
    "N418": "Misrouted claim. See the payer's claim submission instructions.",
    "N522": "Duplicate of a claim processed, or to be processed, as a crossover claim.",
    "N657": "This should be billed with the appropriate code for these services.",
    "N822": (
        "Missing procedure modifier(s). Required for No Surprises Act QPA-based "
        "cost-sharing calculation."
    ),
    "MA130": "Your claim contains incomplete and/or invalid information.",
}


def describe_carc(code: str) -> str:
    """Return a human-readable description for a CARC code, or a safe fallback."""
    info = CARC_CODES.get(code.strip().upper())
    return info.description if info else f"Unrecognized/unmapped CARC code {code!r}."


def describe_rarc(code: str) -> str:
    """Return a human-readable description for a RARC code, or a safe fallback."""
    return RARC_CODES.get(code.strip().upper(), f"Unrecognized/unmapped RARC code {code!r}.")


def infer_group_code(carc_code: str) -> str:
    """Best-effort default group code for a CARC when the source document omits one."""
    info = CARC_CODES.get(carc_code.strip().upper())
    return info.typical_group_code if info else "CO"
