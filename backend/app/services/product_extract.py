"""Pull structured specs from a product page without inventing attributes."""

from __future__ import annotations

import re

from app.services.product_price import PRICE_RE

LAYOUT_RE = re.compile(r"(\d+)\s*(?:percent|%)\s*layout", re.IGNORECASE)
SWITCH_RE = re.compile(
    r"\b((?:silenced\s+)?(?:topre|gateron(?:\s+\w+)?|cherry(?:\s+\w+)?|kailh(?:\s+\w+)?|mx))\s+switches?\b",
    re.IGNORECASE,
)


def extract_product_specs(text: str) -> dict[str, str]:
    """Conservative heuristics so the stub (and compare UI) have something to align."""
    specs: dict[str, str] = {}
    lowered = text.casefold()

    layout = LAYOUT_RE.search(text)
    if layout:
        specs["layout"] = f"{layout.group(1)}%"

    if "bluetooth" in lowered and "usb-c" in lowered:
        specs["connectivity"] = "Bluetooth and USB-C"
    elif "bluetooth" in lowered:
        specs["connectivity"] = "Bluetooth"
    elif "usb-c" in lowered:
        specs["connectivity"] = "USB-C"

    switches = SWITCH_RE.search(text)
    if switches:
        specs["switches"] = switches.group(1).strip()

    if "in stock" in lowered:
        specs["availability"] = "In stock"
    elif "out of stock" in lowered:
        specs["availability"] = "Out of stock"

    if "free shipping" in lowered:
        specs["shipping"] = "Free shipping"
    elif "paid shipping" in lowered:
        specs["shipping"] = "Paid shipping"

    return specs


def extract_product_price(text: str) -> str | None:
    match = PRICE_RE.search(text)
    return match.group(0).strip() if match else None
