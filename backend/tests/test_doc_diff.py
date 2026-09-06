"""Pure tests for document diff meaningfulness heuristics."""

from app.services.doc_diff import compute_diff, content_hash, normalize_for_compare


def test_identical_texts_are_not_meaningful():
    result = compute_diff("A", "hello world", "B", "hello world")
    assert result.is_meaningful is False
    assert result.summary == "Identical"


def test_whitespace_only_is_trivial():
    result = compute_diff(
        "A",
        "Hello   world.\n\nNext",
        "B",
        "Hello world. Next",
    )
    assert result.is_meaningful is False
    assert "Formatting" in result.summary


def test_content_change_is_meaningful():
    left = "The deadline is Friday.\nSubmit via portal."
    right = "The deadline is Monday.\nSubmit via portal.\nInclude the checklist."
    result = compute_diff("Draft A", left, "Draft B", right)
    assert result.is_meaningful is True
    assert "added" in result.summary
    assert "Draft A" in result.unified
    assert "Monday" in result.unified


def test_normalize_strips_punctuation_noise():
    assert normalize_for_compare("Hello, World!") == normalize_for_compare("hello world")


def test_content_hash_is_stable():
    assert content_hash("abc") == content_hash("abc")
    assert content_hash("abc") != content_hash("abd")
