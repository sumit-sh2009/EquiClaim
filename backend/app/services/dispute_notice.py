"""Formal dispute-notice text rendering.

Produces the plain-text body of the court/arbitration-ready dispute letter
embedded in `AuditDocket.dispute_notice_text`. Deliberately template-based
(no LLM call) so the letter's legal citations and dollar figures are
byte-for-byte reproductions of the certified, evaluator-verified state —
nothing here can introduce drift between what was proven and what is sent.
"""

from __future__ import annotations

from datetime import datetime

from app.schemas.audit_docket import LineItemFinding


def render_dispute_notice(
    *,
    claim_id: str,
    line_item_findings: list[LineItemFinding],
    statutory_citations: list[str],
    total_billed_cents: int,
    total_disputed_cents: int,
    generated_at: datetime,
) -> str:
    disputed = [f for f in line_item_findings if f.disputed_amount_cents > 0]
    lines: list[str] = [
        "FORMAL DISPUTE NOTICE",
        "=" * 60,
        f"Claim reference: {claim_id}",
        f"Generated: {generated_at.isoformat()}",
        "",
        (
            f"This notice is issued by EquiClaim following an automated forensic audit "
            f"of the above claim. Of ${total_billed_cents / 100:,.2f} in total billed "
            f"charges, ${total_disputed_cents / 100:,.2f} is disputed as unlawful or "
            "erroneous under the statutory authorities cited below."
        ),
        "",
        "DISPUTED LINE ITEMS",
        "-" * 60,
    ]
    for finding in disputed:
        item = finding.line_item
        lines.append(
            f"- {item.description} (code {item.cpt_hcpcs_code or 'N/A'}, "
            f"service date {item.service_date.isoformat()}): "
            f"disputed ${finding.disputed_amount_cents / 100:,.2f} of "
            f"${item.billed_amount_cents / 100:,.2f} billed."
        )
        cf = finding.compliance_finding
        if cf is not None:
            lines.append(f"    Basis: {cf.citation} — {cf.narrative}")

    lines += [
        "",
        "STATUTORY AUTHORITIES CITED",
        "-" * 60,
    ]
    lines.extend(f"- {citation}" for citation in sorted(set(statutory_citations)))

    lines += [
        "",
        (
            "The undersigned requests recalculation of patient responsibility in "
            "accordance with the cited authorities, and reserves all rights to invoke "
            "the Federal Independent Dispute Resolution (IDR) process under 45 CFR "
            "§ 149.420 if this dispute is not resolved within the statutory response "
            "window."
        ),
    ]
    return "\n".join(lines)
