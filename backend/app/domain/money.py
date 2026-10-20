"""Multi-currency domain conversion and formatting for the forensic boundary.

The domain stores money as integer minor units (e.g. cents for USD/EUR/GBP,
yen for JPY). Binary floats are never used for conversion: ``round(float * 100)``
is half-even and can drop a cent (``1.005`` becomes ``1.00``). Amounts are parsed
as :class:`decimal.Decimal` and quantized with half-up rounding (``ROUND_HALF_UP``),
enforcing the statutory zero-tolerance money invariant across currencies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Mapping


@dataclass(frozen=True)
class CurrencyInfo:
    """Metadata and exchange specifications for a supported currency."""

    code: str
    symbol: str
    name: str
    decimals: int
    rate_to_usd: Decimal  # Amount of foreign currency per 1.00 USD


# Baseline reference exchange rates relative to USD (1.00 USD base).
DEFAULT_EXCHANGE_RATES: dict[str, Decimal] = {
    "USD": Decimal("1.00"),
    "EUR": Decimal("0.92"),
    "GBP": Decimal("0.79"),
    "CAD": Decimal("1.36"),
    "AUD": Decimal("1.52"),
    "INR": Decimal("83.50"),
    "JPY": Decimal("155.00"),
    "CHF": Decimal("0.90"),
    "NZD": Decimal("1.65"),
    "SGD": Decimal("1.35"),
}

SUPPORTED_CURRENCIES: dict[str, CurrencyInfo] = {
    "USD": CurrencyInfo(code="USD", symbol="$", name="US Dollar", decimals=2, rate_to_usd=DEFAULT_EXCHANGE_RATES["USD"]),
    "EUR": CurrencyInfo(code="EUR", symbol="€", name="Euro", decimals=2, rate_to_usd=DEFAULT_EXCHANGE_RATES["EUR"]),
    "GBP": CurrencyInfo(code="GBP", symbol="£", name="British Pound", decimals=2, rate_to_usd=DEFAULT_EXCHANGE_RATES["GBP"]),
    "CAD": CurrencyInfo(code="CAD", symbol="CA$", name="Canadian Dollar", decimals=2, rate_to_usd=DEFAULT_EXCHANGE_RATES["CAD"]),
    "AUD": CurrencyInfo(code="AUD", symbol="AU$", name="Australian Dollar", decimals=2, rate_to_usd=DEFAULT_EXCHANGE_RATES["AUD"]),
    "INR": CurrencyInfo(code="INR", symbol="₹", name="Indian Rupee", decimals=2, rate_to_usd=DEFAULT_EXCHANGE_RATES["INR"]),
    "JPY": CurrencyInfo(code="JPY", symbol="¥", name="Japanese Yen", decimals=0, rate_to_usd=DEFAULT_EXCHANGE_RATES["JPY"]),
    "CHF": CurrencyInfo(code="CHF", symbol="CHF", name="Swiss Franc", decimals=2, rate_to_usd=DEFAULT_EXCHANGE_RATES["CHF"]),
    "NZD": CurrencyInfo(code="NZD", symbol="NZ$", name="New Zealand Dollar", decimals=2, rate_to_usd=DEFAULT_EXCHANGE_RATES["NZD"]),
    "SGD": CurrencyInfo(code="SGD", symbol="SG$", name="Singapore Dollar", decimals=2, rate_to_usd=DEFAULT_EXCHANGE_RATES["SGD"]),
}

# Prefix symbols mapped to ISO codes
_SYMBOL_TO_CURRENCY: list[tuple[str, str]] = [
    ("CA$", "CAD"),
    ("AU$", "AUD"),
    ("NZ$", "NZD"),
    ("SG$", "SGD"),
    ("CHF", "CHF"),
    ("USD", "USD"),
    ("EUR", "EUR"),
    ("GBP", "GBP"),
    ("CAD", "CAD"),
    ("AUD", "AUD"),
    ("INR", "INR"),
    ("JPY", "JPY"),
    ("$", "USD"),
    ("€", "EUR"),
    ("£", "GBP"),
    ("¥", "JPY"),
    ("₹", "INR"),
]

_CENT = Decimal("1")


def detect_currency(raw_text: str, default: str = "USD") -> str:
    """Infer the ISO currency code from text prefixes, symbols, or suffix codes."""
    normalized = raw_text.strip().upper()
    for symbol, code in _SYMBOL_TO_CURRENCY:
        if raw_text.strip().startswith(symbol) or normalized.endswith(code):
            return code
    return default.upper()


def dollars_to_cents(
    amount: Decimal | str | int | float | None,
    currency: str = "USD",
) -> int | None:
    """Convert a major-unit monetary amount (dollars, euros, pounds, etc.) to integer minor units (cents).

    Strings are preferred. A float is accepted only as a last resort and is
    re-parsed from its shortest decimal representation before rounding.
    Any currency symbol ($, €, £, ¥, ₹, CA$, etc.) is cleanly stripped.
    """
    if amount is None:
        return None
    if isinstance(amount, bool) or not isinstance(amount, (Decimal, str, int, float)):
        raise TypeError(f"money amount must be numeric, got {type(amount).__name__}")

    cur_code = currency.upper()
    cur_info = SUPPORTED_CURRENCIES.get(cur_code, SUPPORTED_CURRENCIES["USD"])

    if isinstance(amount, str):
        text = amount.strip().replace(",", "")
        # Strip all known currency prefixes or suffixes
        for sym, _ in _SYMBOL_TO_CURRENCY:
            if text.startswith(sym):
                text = text[len(sym):].strip()
                break
        for code in SUPPORTED_CURRENCIES:
            if text.upper().endswith(code):
                text = text[:-len(code)].strip()
                break
            if text.upper().startswith(code):
                text = text[len(code):].strip()
                break
        if not text:
            return None
        raw: Decimal | str | int = text
    elif isinstance(amount, float):
        raw = format(amount, "f")
    else:
        raw = amount

    try:
        units = raw if isinstance(raw, Decimal) else Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError(f"invalid money amount {amount!r}") from exc

    if not units.is_finite():
        raise ValueError(f"money amount must be finite, got {amount!r}")

    scale = Decimal(10 ** cur_info.decimals)
    minor = (units * scale).quantize(_CENT, rounding=ROUND_HALF_UP)
    return int(minor)


def parse_money(
    amount: Decimal | str | int | float | None,
    default_currency: str = "USD",
) -> tuple[int | None, str]:
    """Parse an amount string/numeric, detecting its currency and returning (minor_units, currency_code).

    Examples::
        parse_money("$10.50") -> (1050, "USD")
        parse_money("€25.00") -> (2500, "EUR")
        parse_money("£100")   -> (10000, "GBP")
        parse_money("150.00", default_currency="CAD") -> (15000, "CAD")
    """
    if amount is None:
        return None, default_currency.upper()

    currency = default_currency.upper()
    if isinstance(amount, str):
        currency = detect_currency(amount, default=default_currency)

    minor = dollars_to_cents(amount, currency=currency)
    return minor, currency


def convert_currency(
    minor_amount: int,
    from_currency: str,
    to_currency: str,
    custom_rates: Mapping[str, Decimal] | None = None,
) -> int:
    """Convert an integer minor-unit amount between currencies using half-up rounding.

    Conversion formula:
        major_from = minor_amount / (10 ** decimals_from)
        usd_amount = major_from / rate_to_usd[from_currency]
        major_to   = usd_amount * rate_to_usd[to_currency]
        minor_to   = round_half_up(major_to * (10 ** decimals_to))
    """
    from_code = from_currency.upper()
    to_code = to_currency.upper()

    if from_code == to_code:
        return minor_amount

    from_info = SUPPORTED_CURRENCIES.get(from_code)
    to_info = SUPPORTED_CURRENCIES.get(to_code)

    if from_info is None:
        raise ValueError(f"unsupported source currency: {from_currency!r}")
    if to_info is None:
        raise ValueError(f"unsupported target currency: {to_currency!r}")

    rates = custom_rates or DEFAULT_EXCHANGE_RATES
    from_rate = Decimal(str(rates[from_code]))
    to_rate = Decimal(str(rates[to_code]))

    if from_rate <= Decimal("0") or to_rate <= Decimal("0"):
        raise ValueError("exchange rates must be positive")

    from_scale = Decimal(10 ** from_info.decimals)
    to_scale = Decimal(10 ** to_info.decimals)

    major_from = Decimal(minor_amount) / from_scale
    usd_amount = major_from / from_rate
    major_to = usd_amount * to_rate
    minor_to = (major_to * to_scale).quantize(_CENT, rounding=ROUND_HALF_UP)

    return int(minor_to)


def format_money(
    minor_amount: int,
    currency: str = "USD",
) -> str:
    """Format an integer minor-unit amount into a standard localized representation.

    Examples::
        format_money(125055, "USD") -> "$1,250.55"
        format_money(115000, "EUR") -> "€1,150.00"
        format_money(98750, "GBP")  -> "£987.50"
        format_money(15500, "JPY")  -> "¥15,500"
    """
    cur_code = currency.upper()
    cur_info = SUPPORTED_CURRENCIES.get(cur_code, SUPPORTED_CURRENCIES["USD"])

    scale = Decimal(10 ** cur_info.decimals)
    major = Decimal(minor_amount) / scale

    if cur_info.decimals == 0:
        formatted_num = f"{int(major):,}"
    else:
        formatted_num = f"{major:,.{cur_info.decimals}f}"

    return f"{cur_info.symbol}{formatted_num}"
