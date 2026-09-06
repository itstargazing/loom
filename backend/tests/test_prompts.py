"""Prompt rendering: truncation and payload trimming keep context bounded."""

import json

from app.prompts.classify_event import (
    MAX_TEXT_CHARS,
    SYSTEM_PROMPT,
    build_repair_prompt,
    build_user_prompt,
)
from app.schemas.classification import SkillCategory


def _render(event_type: str, payload: dict) -> str:
    return build_user_prompt(
        event_type=event_type,
        source_url="https://example.com",
        page_title="Example",
        occurred_at="2026-08-28T10:00:00+00:00",
        payload=payload,
    )


def test_system_prompt_tells_glossary_apart_from_a_sentence():
    assert "one to five words" in SYSTEM_PROMPT
    assert "ordinary sentence" in SYSTEM_PROMPT
    for category in SkillCategory.__args__:
        assert category in SYSTEM_PROMPT, f"{category} is undocumented in the prompt"


def test_system_prompt_tells_citations_apart_from_casual_copies():
    assert "casual conversational" in SYSTEM_PROMPT
    assert "password" in SYSTEM_PROMPT
    assert "author" in SYSTEM_PROMPT
    assert "published_date" in SYSTEM_PROMPT


def test_system_prompt_asks_for_the_most_important_deadline_on_a_page():
    assert "soonest or most important" in SYSTEM_PROMPT
    assert "every other date-like mention" in SYSTEM_PROMPT


def test_user_prompt_is_valid_json_after_the_header():
    prompt = _render("text_copied", {"text": "hello", "context": "greeting"})
    body = prompt.split("\n\n", 1)[1]

    event = json.loads(body)
    assert event["eventType"] == "text_copied"
    assert event["payload"]["text"] == "hello"


def test_long_selection_text_is_truncated():
    prompt = _render("highlight_selected", {"text": "x" * (MAX_TEXT_CHARS * 2)})

    assert "truncated" in prompt
    assert len(prompt) < MAX_TEXT_CHARS * 2


def test_page_text_is_truncated():
    prompt = _render("page_opened", {"fullText": "y" * (MAX_TEXT_CHARS * 3)})
    assert "truncated" in prompt


def test_dwell_sections_are_capped_and_trimmed():
    payload = {
        "sections": [
            {"heading": f"H{index}", "excerpt": "z" * 2_000, "dwellMs": index}
            for index in range(30)
        ]
    }
    event = json.loads(_render("scroll_dwell", payload).split("\n\n", 1)[1])

    assert len(event["payload"]["sections"]) == 10
    assert all(len(section["excerpt"]) < 1_200 for section in event["payload"]["sections"])


def test_short_text_is_not_annotated_as_truncated():
    prompt = _render("highlight_selected", {"text": "brief", "context": "short"})
    assert "truncated" not in prompt


def test_unknown_event_type_passes_payload_through():
    """An unrecognised type must not crash prompt rendering."""
    event = json.loads(_render("something_new", {"arbitrary": "value"}).split("\n\n", 1)[1])
    assert event["payload"] == {"arbitrary": "value"}


def test_repair_prompt_handles_empty_previous_output():
    repair = build_repair_prompt("original prompt", "", "response was empty")

    assert "original prompt" in repair
    assert "(empty response)" in repair
    assert "response was empty" in repair
