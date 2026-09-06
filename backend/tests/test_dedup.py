"""Dedup keys decide whether a capture is a new entry or a repeat sighting.

Too loose and distinct entries collapse into one; too strict and the same thing
is stored repeatedly. Both failures are silent, so the normalisation rules are
pinned here.
"""

from app.services.dedup import dedup_key, normalize


def test_case_and_whitespace_are_ignored():
    assert normalize("  Positional   ENCODING\n") == "positional encoding"


def test_punctuation_is_ignored():
    """Trailing periods and smart quotes must not create a second entry."""
    assert normalize("the model's output.") == normalize("The model s output")
    assert normalize("\u201cquoted\u201d") == normalize('"quoted"')


def test_unicode_variants_unify():
    # Fullwidth and ligature forms normalise to their plain equivalents.
    assert normalize("\uff41\uff42\uff43") == "abc"


def test_same_text_gives_the_same_key():
    assert dedup_key("Attention Is All You Need") == dedup_key(
        "  attention is all you need  "
    )


def test_different_text_gives_different_keys():
    assert dedup_key("recall") != dedup_key("precision")


def test_key_is_fixed_width_regardless_of_input_length():
    short = dedup_key("a")
    long = dedup_key("x" * 100_000)

    assert len(short) == len(long) == 32


def test_part_boundaries_are_respected():
    """('ab','c') and ('a','bc') are different entries and must not collide."""
    assert dedup_key("ab", "c") != dedup_key("a", "bc")


def test_none_parts_are_skipped():
    assert dedup_key("term", None) == dedup_key("term")


def test_empty_parts_are_distinct_from_missing_ones():
    # A present-but-empty field is not the same as an absent one.
    assert dedup_key("term", "") != dedup_key("term")
