"""Parse free-text product prices without throwing away the original string.

The listing stores what the page wrote. Comparison converts that into an
amount and currency when it can; mixed currencies are not ranked against
each other.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

CURRENCY_SYMBOLS: dict[str, str] = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "¥": "JPY",
}

CURRENCY_CODES = {
    "usd": "USD",
    "eur": "EUR",
    "gbp": "GBP",
    "jpy": "JPY",
    "cad": "CAD",
    "aud": "AUD",
}

#  $385.00 | USD 385 | 1,299.00 EUR | €12,50 | 385
PRICE_RE = re.compile(
    r"""
    (?:
        (?P<sym>[$€£¥])\s*(?P<amount_sym>\d(?:[\d.,]*\d)?)
        |
        (?P<code_pre>USD|EUR|GBP|JPY|CAD|AUD)\s*(?P<amount_pre>\d(?:[\d.,]*\d)?)
        |
        (?P<amount_post>\d(?:[\d.,]*\d)?)\s*(?P<code_post>USD|EUR|GBP|JPY|CAD|AUD)
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


@dataclass(frozen=True, slots=True)
class NormalizedPrice:
    raw: str | None
    amount: Decimal | None
    currency: str | None

    @property
    def comparable(self) -> bool:
        return self.amount is not None and self.currency is not None


def _parse_amount(text: str) -> Decimal | None:
    cleaned = text.strip()
    if not cleaned:
        return None
    #  European thousands/decimal: 1.299,00 vs US 1,299.00
    if cleaned.count(",") == 1 and cleaned.count(".") == 0:
        if len(cleaned.split(",")[-1]) in {1, 2}:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif cleaned.count(",") > 0 and cleaned.count(".") == 1:
        cleaned = cleaned.replace(",", "")
    elif cleaned.count(".") > 1 and "," not in cleaned:
        cleaned = cleaned.replace(".", "")
    else:
        cleaned = cleaned.replace(",", "")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def parse_price(raw: str | None) -> NormalizedPrice:
    if raw is None or not str(raw).strip():
        return NormalizedPrice(raw=raw, amount=None, currency=None)

    text = str(raw).strip()
    match = PRICE_RE.search(text)
    if not match:
        return NormalizedPrice(raw=text, amount=None, currency=None)

    if match.group("sym"):
        currency = CURRENCY_SYMBOLS[match.group("sym")]
        amount = _parse_amount(match.group("amount_sym"))
    elif match.group("code_pre"):
        currency = CURRENCY_CODES[match.group("code_pre").casefold()]
        amount = _parse_amount(match.group("amount_pre"))
    else:
        currency = CURRENCY_CODES[match.group("code_post").casefold()]
        amount = _parse_amount(match.group("amount_post"))

    return NormalizedPrice(raw=text, amount=amount, currency=currency)
