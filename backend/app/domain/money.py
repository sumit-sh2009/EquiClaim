"""Dollar-to-cent conversion for the forensic boundary.

The domain stores money as integer cents. Binary floats are not used for
that conversion: ``round(float * 100)`` is half-even and can miss a cent
(``1.005`` becomes ``1.00``). Amounts are parsed as :class:`decimal.Decimal`
and quantized with half-up rounding, which is the usual currency rule.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

_CENT = Decimal("1")


def dollars_to_cents(amount: Decimal | str | int | float | None) -> int | None:
    """Convert a dollar amount to integer cents.

    Strings are preferred. A float is accepted only as a last resort and is
    re-parsed from its shortest decimal representation before rounding.
    """
    if amount is None:
        return None
    if isinstance(amount, bool) or not isinstance(amount, (Decimal, str, int, float)):
        raise TypeError(f"money amount must be numeric, got {type(amount).__name__}")
    if isinstance(amount, str):
        text = amount.strip().replace(",", "").removeprefix("$")
        if not text:
            return None
        raw: Decimal | str | int = text
    elif isinstance(amount, float):
        raw = format(amount, "f")
    else:
        raw = amount
    try:
        dollars = raw if isinstance(raw, Decimal) else Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError(f"invalid money amount {amount!r}") from exc
    if not dollars.is_finite():
        raise ValueError(f"money amount must be finite, got {amount!r}")
    cents = (dollars * 100).quantize(_CENT, rounding=ROUND_HALF_UP)
    return int(cents)
