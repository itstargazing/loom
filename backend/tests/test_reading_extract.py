"""Dwell extraction and document assembly."""

from datetime import UTC, datetime

from app.services.reading_compile import (
    CompiledPassage,
    order_passages,
    render_markdown,
)
from app.services.reading_extract import extract_dwell_passages
from app.services.reading_pdf import render_pdf


def test_sections_below_threshold_are_ignored():
    extracted = extract_dwell_passages(
        {
            "sections": [
                {"heading": "Intro", "excerpt": "A brief opening.", "dwellMs": 1_200},
                {
                    "heading": "The core argument",
                    "excerpt": "Attention is a scarce resource.",
                    "dwellMs": 42_000,
                },
            ]
        },
        threshold_ms=3_000,
    )
    assert len(extracted) == 1
    assert extracted[0].heading == "The core argument"
    assert extracted[0].dwell_ms == 42_000


def test_source_order_groups_by_url():
    earlier = datetime(2026, 1, 1, tzinfo=UTC)
    later = datetime(2026, 1, 2, tzinfo=UTC)
    passages = [
        CompiledPassage("2", "b", None, "https://b.example", "B", 4_000, later),
        CompiledPassage("1", "a", "H", "https://a.example", "A", 5_000, earlier),
        CompiledPassage("3", "a2", None, "https://a.example", "A", 6_000, earlier),
    ]
    ordered = order_passages(passages, order="source")
    assert [item.id for item in ordered] == ["1", "3", "2"]


def test_explicit_entry_order_wins():
    now = datetime.now(UTC)
    passages = [
        CompiledPassage("1", "a", None, "https://a.example", "A", 1, now),
        CompiledPassage("2", "b", None, "https://b.example", "B", 1, now),
    ]
    ordered = order_passages(passages, entry_ids=["2", "1"])
    assert [item.id for item in ordered] == ["2", "1"]


def test_markdown_includes_headings_and_sources():
    now = datetime.now(UTC)
    md = render_markdown(
        [
            CompiledPassage(
                "1",
                "Attention is scarce.",
                "The core argument",
                "https://example.com/essay",
                "On Attention",
                42_000,
                now,
            )
        ]
    )
    assert "# Reading compilation" in md
    assert "## On Attention" in md
    assert "### The core argument" in md
    assert "Attention is scarce." in md


def test_pdf_starts_with_header():
    pdf = render_pdf("Title", "Hello world\nSecond line")
    assert pdf.startswith(b"%PDF-1.4")
    assert b"%%EOF" in pdf
