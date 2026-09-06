"""Price parsing, spec extraction, and comparison grids."""

from decimal import Decimal
from uuid import uuid4

from app.services.product_compare import canonicalize_spec_key, compare_products, render_csv
from app.services.product_extract import extract_product_price, extract_product_specs
from app.services.product_price import parse_price


def test_dollar_price_is_usd():
    parsed = parse_price("Price $385.00. In stock")
    assert parsed.currency == "USD"
    assert parsed.amount == Decimal("385.00")
    assert parsed.comparable


def test_euro_suffix_and_us_thousands():
    parsed = parse_price("1,299.00 EUR")
    assert parsed.currency == "EUR"
    assert parsed.amount == Decimal("1299.00")


def test_unparseable_price_stays_incomparable():
    parsed = parse_price("Call for pricing")
    assert not parsed.comparable
    assert parsed.raw == "Call for pricing"


def test_extracts_keyboard_specs_and_price():
    text = (
        "Price $385.00. In stock, free shipping. 60 percent layout, "
        "Bluetooth and USB-C, silenced Topre switches."
    )
    assert extract_product_price(text) == "$385.00"
    specs = extract_product_specs(text)
    assert specs["layout"] == "60%"
    assert specs["connectivity"] == "Bluetooth and USB-C"
    assert specs["switches"].lower() == "silenced topre"
    assert specs["availability"] == "In stock"
    assert specs["shipping"] == "Free shipping"


def test_spec_aliases_share_a_row():
    assert canonicalize_spec_key("Weight") == canonicalize_spec_key("mass")
    assert canonicalize_spec_key("Bluetooth") == "connectivity"


def test_compare_ranks_same_currency_and_leaves_gaps():
    cheap_id = uuid4()
    dear_id = uuid4()
    comparison = compare_products(
        [
            (dear_id, "HHKB", "https://a.example", "HHKB", "$385.00", {"layout": "60%"}),
            (
                cheap_id,
                "Keychron",
                "https://b.example",
                "Keychron",
                "$199.00",
                {"Layout": "75%", "switches": "Gateron"},
            ),
        ]
    )
    assert comparison.spec_keys == ["layout", "switches"]
    assert comparison.lowest_price_ids == [cheap_id]
    assert comparison.columns[1].specs["layout"] == "75%"
    assert "switches" not in comparison.columns[0].specs


def test_mixed_currencies_are_not_ranked():
    comparison = compare_products(
        [
            (uuid4(), "A", "https://a.example", "A", "$10", {}),
            (uuid4(), "B", "https://b.example", "B", "€10", {}),
        ]
    )
    assert comparison.lowest_price_ids == []
    assert comparison.price_note is not None


def test_csv_includes_aligned_spec_columns():
    comparison = compare_products(
        [
            (uuid4(), "A", "https://a.example", "A", "$10", {"layout": "60%"}),
            (uuid4(), "B", "https://b.example", "B", "$20", {"layout": "75%"}),
        ]
    )
    csv = render_csv(comparison)
    assert "Name,Price,Amount,Currency,Lowest,Source,layout" in csv
    assert "60%" in csv
    assert "yes" in csv
