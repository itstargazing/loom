"""Breakthrough feature unit tests (no live DB or model provider)."""

from app.ai.stub_client import _hashed_embedding
from app.services.capture_text import capture_snippet, normalize_snippet
from app.services.classification_cache import cache_key
from app.services.embeddings import cosine_similarity


def test_normalize_treats_rehighlights_as_the_same():
    a = normalize_snippet("  Positional Encoding.  ")
    b = normalize_snippet("positional encoding")
    assert a == b


def test_cache_key_is_stable_for_near_identical_text():
    left = cache_key(user_id="dev-user", event_type="highlight_selected", snippet="Hello World!")
    right = cache_key(user_id="dev-user", event_type="highlight_selected", snippet="hello world")
    assert left == right
    other = cache_key(user_id="dev-user", event_type="text_copied", snippet="hello world")
    assert left != other


def test_capture_snippet_prefers_highlight_text():
    assert capture_snippet("highlight_selected", {"text": "term", "context": "A term."}) == "term"
    assert capture_snippet("page_opened", {"fullText": "body"}) == "body"


def test_hashed_embeddings_rank_similar_text_higher():
    query = _hashed_embedding("positional encoding in transformers", dimensions=64)
    close = _hashed_embedding("positional encoding in transformers", dimensions=64)
    far = _hashed_embedding("grocery list milk eggs", dimensions=64)
    assert cosine_similarity(query, close) > cosine_similarity(query, far)


def test_digest_grouping_labels_cover_pending():
    from app.services.digest import CATEGORY_GROUP_LABELS

    assert "pending" in CATEGORY_GROUP_LABELS
    assert CATEGORY_GROUP_LABELS["glossary_term"] == "Glossary"


def test_stub_classifies_deadline_shaped_highlights():
    from app.ai.stub_client import _classify_selection

    items = _classify_selection(
        "Final paper due December 12, 2026",
        "Syllabus: Final paper due December 12, 2026 at 11:59pm.",
        "https://courses.example.edu/cs101",
        "CS 101 Syllabus",
    )
    categories = [item.category for item in items]
    assert "deadline" in categories
    deadline = next(item for item in items if item.category == "deadline")
    assert deadline.fields.deadline_date
    assert "paper" in (deadline.fields.deadline_title or "").lower() or "Final" in (
        deadline.fields.deadline_title or ""
    )


def test_lexical_score_ranks_keyword_overlap():
    from app.services.embeddings import lexical_score

    query = "What did I save about positional encoding?"
    close = lexical_score(query, "We inject positional encoding to give token order.")
    far = lexical_score(query, "Grocery list: milk, eggs, bread.")
    assert close > far
    assert close >= 0.15


def test_stub_brief_is_a_markdown_document():
    from app.ai.stub_client import _stub_brief

    empty = _stub_brief("Topic: Midterm\nCaptured material:\n(no related captures)")
    assert empty.startswith("# Midterm")
    assert "What's been read" in empty
    assert "0 sources" in empty

    filled = _stub_brief(
        "Topic: positional encoding\nCaptured material:\n"
        "[1] Attention Is All You Need (https://arxiv.org/abs/1706.03762)\n"
        "We inject positional encoding to give the model token order."
    )
    assert filled.startswith("# positional encoding")
    assert "Attention Is All You Need" in filled
    assert "What's still looks thin" in filled or "What still looks thin" in filled
