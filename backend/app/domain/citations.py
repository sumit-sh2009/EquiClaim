"""Statutory citation allow-list.

Every legal citation attached to a `ComplianceFinding` or surfaced in an
`AuditDocket` MUST match one of these real, verifiable CFR sections. This is
enforced twice, defense-in-depth: (1) at the Pydantic schema boundary
(`ComplianceFinding.citation` validator) so a malformed citation can never
even be constructed, and (2) again by the `ActuarialEvaluatorNode` before a
docket is certified, so a hallucinated statute can never survive a full
audit pass. Nothing outside this set may ever be cited in a certified
docket — this is how EquiClaim prevents an LLM from inventing law.
"""

from __future__ import annotations

# No Surprises Act — Requirements Related to Surprise Billing (45 CFR Part 149)
NSA_CITATIONS = frozenset(
    {
        "45 CFR 149.110",  # Preemption of State law
        "45 CFR 149.120",  # Balance billing in cases of emergency services
        "45 CFR 149.130",  # Balance billing for non-emergency services at certain facilities
        "45 CFR 149.140",  # Balance billing for air ambulance services
        "45 CFR 149.410",  # Methodology for calculating qualifying payment amount (QPA)
        "45 CFR 149.420",  # Independent dispute resolution (IDR) process
        "45 CFR 149.440",  # Good faith estimate requirements
        "45 CFR 149.450",  # Patient-provider dispute resolution
    }
)

# Hospital Price Transparency (45 CFR Part 180)
PRICE_TRANSPARENCY_CITATIONS = frozenset(
    {
        "45 CFR 180.20",  # Requirements related to display of standard charges
        "45 CFR 180.40",  # Machine-readable file requirements
        "45 CFR 180.50",  # Standard charge disclosure — machine-readable file contents
        "45 CFR 180.60",  # Standard charge disclosure — consumer-friendly display
        "45 CFR 180.90",  # Monitoring and enforcement
    }
)

# National Correct Coding Initiative unbundling (statutory basis: Social Security Act § 1833(e);
# CMS program authority) — cited by narrative reference, not a CFR part, but tracked here too so
# the same allow-list mechanism covers every rule_type.
NCCI_CITATIONS = frozenset(
    {
        "NCCI PTP Edits — CMS Medicare NCCI Policy Manual Ch. I.A",
    }
)

ALLOWED_CITATIONS: frozenset[str] = (
    NSA_CITATIONS | PRICE_TRANSPARENCY_CITATIONS | NCCI_CITATIONS
)


def is_allowed_citation(citation: str) -> bool:
    """Return True iff `citation` is byte-for-byte in the statutory allow-list."""
    return citation in ALLOWED_CITATIONS
