"""Align product listings into a comparison grid.

Spec keys are canonicalised so "Weight" and "mass" share a row. Prices are
normalised for ranking only when they share a currency.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from app.services.product_price import NormalizedPrice, parse_price

TOKEN_RE = re.compile(r"[a-z0-9]+")

SPEC_ALIASES: dict[str, tuple[str, ...]] = {
    "layout": ("size", "form factor", "percent layout", "keyboard size"),
    "connectivity": ("connection", "wireless", "bluetooth", "interface"),
    "switches": ("switch", "switch type"),
    "availability": ("stock", "in stock"),
    "shipping": ("delivery", "postage"),
    "weight": ("mass", "wt"),
}


def canonicalize_spec_key(key: str) -> str:
    tokens = " ".join(TOKEN_RE.findall(key.casefold()))
    if not tokens:
        return key.strip() or "spec"
    for canonical, aliases in SPEC_ALIASES.items():
        labels = (canonical,) + aliases
        for label in labels:
            if tokens == label or label in tokens or tokens in label:
                return canonical
    return tokens


@dataclass(frozen=True, slots=True)
class ComparedProduct:
    id: UUID
    name: str
    source_url: str
    page_title: str
    price: NormalizedPrice
    specs: dict[str, str]


@dataclass(frozen=True, slots=True)
class ProductComparison:
    columns: list[ComparedProduct]
    spec_keys: list[str]
    lowest_price_ids: list[UUID]
    price_note: str | None


def compare_products(
    listings: list[tuple[UUID, str, str, str, str | None, dict[str, str]]],
) -> ProductComparison:
    columns = [
        ComparedProduct(
            id=entry_id,
            name=name,
            source_url=source_url,
            page_title=page_title,
            price=parse_price(price),
            specs={
                canonicalize_spec_key(key): value
                for key, value in (specs or {}).items()
                if str(value).strip()
            },
        )
        for entry_id, name, source_url, page_title, price, specs in listings
    ]

    keys: list[str] = []
    seen: set[str] = set()
    for column in columns:
        for key in column.specs:
            if key not in seen:
                seen.add(key)
                keys.append(key)

    lowest_ids, note = _lowest_price_ids(columns)
    return ProductComparison(
        columns=columns,
        spec_keys=keys,
        lowest_price_ids=lowest_ids,
        price_note=note,
    )


def _lowest_price_ids(columns: list[ComparedProduct]) -> tuple[list[UUID], str | None]:
    comparable = [column for column in columns if column.price.comparable]
    if len(comparable) < 2:
        return [], None

    currencies = {column.price.currency for column in comparable}
    if len(currencies) > 1:
        return [], "Prices use different currencies and were not ranked."

    lowest = min(column.price.amount or Decimal("Infinity") for column in comparable)
    winners = [
        column.id
        for column in comparable
        if column.price.amount is not None and column.price.amount == lowest
    ]
    return winners, None


def render_csv(comparison: ProductComparison) -> str:
    output = io.StringIO()
    headers = ["Name", "Price", "Amount", "Currency", "Lowest", "Source", *comparison.spec_keys]
    writer = csv.writer(output)
    writer.writerow(headers)
    lowest = set(comparison.lowest_price_ids)
    for column in comparison.columns:
        row = [
            column.name,
            column.price.raw or "",
            f"{column.price.amount:.2f}" if column.price.amount is not None else "",
            column.price.currency or "",
            "yes" if column.id in lowest else "",
            column.source_url,
        ]
        for key in comparison.spec_keys:
            row.append(column.specs.get(key, ""))
        writer.writerow(row)
    return output.getvalue()
