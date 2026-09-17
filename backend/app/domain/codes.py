"""CPT / HCPCS procedural code classification helpers.

CPT codes are 5-digit numerics (AMA-owned); HCPCS Level II codes are one
letter followed by 4 digits (CMS-owned). This is a deliberately narrow,
deterministic classifier — it is not a full code-set validator, only enough
to route a normalized code string to the correct `CodeType` literal for
`ClaimLineItem.code_type` / MRF lookups.
"""

from __future__ import annotations

import re

from app.schemas.cms_mrf import CodeType

_CPT_RE = re.compile(r"^\d{5}$")
_HCPCS_RE = re.compile(r"^[A-Va-v]\d{4}$")
_NDC_RE = re.compile(r"^\d{4,5}-\d{3,4}-\d{1,2}$")


def normalize_code(raw: str) -> str:
    """Strip whitespace/punctuation noise from an OCR-extracted code string."""
    return raw.strip().upper().replace(" ", "")


def infer_code_type(raw_code: str) -> CodeType | None:
    """Infer the CMS `CodeType` for a normalized procedure code, or None if unknown."""
    code = normalize_code(raw_code)
    if _CPT_RE.match(code):
        return "CPT"
    if _HCPCS_RE.match(code):
        return "HCPCS"
    if _NDC_RE.match(code):
        return "NDC"
    return None
