"""The retry-once-on-invalid-output behaviour, driven by scripted fake clients."""

import json

import pytest

from app.ai.base import AIClient, AIClientError, JsonCompletion, JsonCompletionRequest
from app.ai.stub_client import StubAIClient
from app.services.classification import MAX_ATTEMPTS, classify_event

VALID_RESPONSE = json.dumps(
    {
        "classifications": [
            {
                "category": "glossary_term",
                "confidence": 0.82,
                "reason": "Unfamiliar technical term with a definition nearby.",
                "fields": {
                    "term": "positional encoding",
                    "definition": "Signal injected to convey token order.",
                    "quote": None,
                    "author": None,
                    "work_title": None,
                    "publisher": None,
                    "published_date": None,
                    "deadline_title": None,
                    "deadline_date": None,
                    "deadline_kind": None,
                    "claim": None,
                    "topic": None,
                    "passage": None,
                    "reading_heading": None,
                    "reading_dwell_ms": None,
                    "product_name": None,
                    "price": None,
                    "specs": None,
                    "job_title": None,
                    "company": None,
                    "salary": None,
                    "requirements": None,
                    "application_deadline": None,
                    "clause_text": None,
                    "flag_reason": None,
                    "risk_level": None,
                },
            }
        ]
    }
)

#  Valid JSON, but glossary_term is missing its mandatory definition.
SCHEMA_VIOLATING_RESPONSE = json.dumps(
    {
        "classifications": [
            {
                "category": "glossary_term",
                "confidence": 0.9,
                "reason": "a term",
                "fields": {"term": "positional encoding"},
            }
        ]
    }
)


class ScriptedClient(AIClient):
    """Returns queued responses in order, recording each request it received."""

    provider = "scripted"
    model = "scripted-v1"

    def __init__(self, *responses: str | Exception) -> None:
        self._responses = list(responses)
        self.requests: list[JsonCompletionRequest] = []

    async def complete_json(self, request: JsonCompletionRequest) -> JsonCompletion:
        self.requests.append(request)
        response = self._responses.pop(0)

        if isinstance(response, Exception):
            raise response

        return JsonCompletion(text=response, provider=self.provider, model=self.model)


async def test_valid_first_attempt(highlight_event):
    client = ScriptedClient(VALID_RESPONSE)
    outcome = await classify_event(highlight_event, client)

    assert outcome.succeeded
    assert outcome.attempts == 1
    assert outcome.result.categories == ["glossary_term"]
    assert outcome.result.classifications[0].fields.term == "positional encoding"
    assert outcome.error is None


async def test_malformed_json_recovers_on_retry(highlight_event):
    client = ScriptedClient("not json at all {", VALID_RESPONSE)
    outcome = await classify_event(highlight_event, client)

    assert outcome.succeeded
    assert outcome.attempts == 2
    assert len(client.requests) == 2


async def test_schema_violation_recovers_on_retry(highlight_event):
    client = ScriptedClient(SCHEMA_VIOLATING_RESPONSE, VALID_RESPONSE)
    outcome = await classify_event(highlight_event, client)

    assert outcome.succeeded
    assert outcome.attempts == 2


async def test_retry_prompt_carries_the_error_and_prior_output(highlight_event):
    client = ScriptedClient(SCHEMA_VIOLATING_RESPONSE, VALID_RESPONSE)
    await classify_event(highlight_event, client)

    retry_prompt = client.requests[1].user
    assert "did not satisfy the required schema" in retry_prompt
    assert "positional encoding" in retry_prompt
    # The original event must still be present, or the model has nothing to fix.
    assert "Classify this capture event." in retry_prompt


async def test_gives_up_after_two_attempts(highlight_event):
    client = ScriptedClient("still not json", "also not json")
    outcome = await classify_event(highlight_event, client)

    assert not outcome.succeeded
    assert outcome.attempts == MAX_ATTEMPTS
    assert len(client.requests) == MAX_ATTEMPTS
    assert "not valid JSON" in outcome.error
    # Raw output is kept so the prompt can be debugged afterwards.
    assert outcome.raw_text == "also not json"


async def test_provider_error_does_not_retry(highlight_event):
    """A transport failure is not a schema problem; the queue retries instead."""
    client = ScriptedClient(AIClientError("connection reset"), VALID_RESPONSE)
    outcome = await classify_event(highlight_event, client)

    assert not outcome.succeeded
    assert outcome.attempts == 1
    assert len(client.requests) == 1
    assert "connection reset" in outcome.error


async def test_strict_schema_is_sent_to_the_provider(highlight_event):
    client = ScriptedClient(VALID_RESPONSE)
    await classify_event(highlight_event, client)

    request = client.requests[0]
    assert request.schema_name == "event_classification"
    assert request.json_schema["type"] == "object"
    assert request.temperature == 0.0
    # The structured context is what lets non-prompt providers work.
    assert request.context["eventType"] == "highlight_selected"


async def test_latency_is_recorded(highlight_event):
    outcome = await classify_event(highlight_event, ScriptedClient(VALID_RESPONSE))
    assert outcome.latency_ms >= 0


@pytest.mark.parametrize(
    "event_type,payload,expected",
    [
        (
            "highlight_selected",
            {"text": "idempotency", "context": "Requests must be idempotent."},
            "glossary_term",
        ),
        (
            "text_copied",
            {
                "text": (
                    "According to the study, 42 percent of respondents reported "
                    "improved outcomes across the sampled population."
                )
            },
            "citation",
        ),
        (
            "upload_field_detected",
            {"fieldLabel": "Resume"},
            "none",
        ),
    ],
)
async def test_stub_client_produces_valid_output(event_type, payload, expected):
    """The offline path must satisfy the same validation as the cloud path."""
    from app.services.classification import ClassifiableEvent

    event = ClassifiableEvent(
        event_type=event_type,
        source_url="https://example.com/paper",
        page_title="Example",
        occurred_at="2026-08-28T10:00:00+00:00",
        payload=payload,
    )

    outcome = await classify_event(event, StubAIClient())

    assert outcome.succeeded, outcome.error
    assert expected in outcome.result.categories
    assert outcome.attempts == 1


async def test_stub_client_skips_sensitive_content():
    from app.services.classification import ClassifiableEvent

    event = ClassifiableEvent(
        event_type="text_copied",
        source_url="https://example.com/login",
        page_title="Sign in",
        occurred_at="2026-08-28T10:00:00+00:00",
        payload={"text": "my password is hunter2 and the api_key is sk-abc123"},
    )

    outcome = await classify_event(event, StubAIClient())

    assert outcome.succeeded
    assert outcome.result.is_none


async def test_stub_glossary_definition_uses_the_containing_sentence():
    from app.services.classification import ClassifiableEvent

    event = ClassifiableEvent(
        event_type="highlight_selected",
        source_url="https://arxiv.org/abs/1706.03762",
        page_title="Attention Is All You Need",
        occurred_at="2026-08-28T10:00:00+00:00",
        payload={
            "text": "positional encoding",
            "context": (
                "Earlier work used recurrence. We inject positional encoding "
                "to convey token order. Later layers attend over it."
            ),
        },
    )

    outcome = await classify_event(event, StubAIClient())
    definition = outcome.result.classifications[0].fields.definition

    assert "We inject positional encoding" in definition
    assert "Earlier work" not in definition


async def test_stub_does_not_treat_a_punctuated_sentence_as_a_term():
    from app.services.classification import ClassifiableEvent

    event = ClassifiableEvent(
        event_type="highlight_selected",
        source_url="https://example.com/essay",
        page_title="Essay",
        occurred_at="2026-08-28T10:00:00+00:00",
        payload={"text": "This is worth noting.", "context": "A paragraph of prose."},
    )

    outcome = await classify_event(event, StubAIClient())
    assert "glossary_term" not in outcome.result.categories


async def test_stub_skips_casual_copies_as_citations():
    from app.services.classification import ClassifiableEvent

    event = ClassifiableEvent(
        event_type="text_copied",
        source_url="https://chat.example.com/thread",
        page_title="Chat",
        occurred_at="2026-08-28T10:00:00+00:00",
        payload={"text": "ok thanks, see you tomorrow after class"},
    )

    outcome = await classify_event(event, StubAIClient())
    assert "citation" not in outcome.result.categories


async def test_stub_citation_pulls_author_and_work_from_the_page():
    from app.services.classification import ClassifiableEvent

    event = ClassifiableEvent(
        event_type="text_copied",
        source_url="https://www.nature.com/articles/s41586-024-00001",
        page_title="Global temperature trends",
        occurred_at="2026-08-28T10:00:00+00:00",
        payload={
            "text": (
                "According to Hansen et al, global average temperatures rose by "
                "1.2 degrees Celsius relative to the pre-industrial baseline."
            )
        },
    )

    outcome = await classify_event(event, StubAIClient())
    item = next(
        entry
        for entry in outcome.result.classifications
        if entry.category == "citation"
    )
    assert item.fields.author == "Hansen et al."
    assert item.fields.work_title == "Global temperature trends"
    assert item.fields.publisher == "nature.com"
