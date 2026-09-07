"""Classifies a raw capture event into skill categories.

Phase 3.1 scope: this decides *what* an event is and records that decision
against the event. It deliberately writes nothing into the typed skill stores —
that is the router's job in Phase 3.2.
"""

import json
import logging
import time
from dataclasses import dataclass

from pydantic import ValidationError

from app.ai.base import AIClient, AIClientError, JsonCompletionRequest
from app.prompts.classify_event import (
    SCHEMA_NAME,
    SYSTEM_PROMPT,
    build_repair_prompt,
    build_user_prompt,
)
from app.schemas.classification import ClassificationResult, classification_json_schema

logger = logging.getLogger(__name__)

#  One retry, per the design: a second attempt fixes most schema slips, and
#  further attempts mostly burn tokens.
MAX_ATTEMPTS = 2


@dataclass(slots=True)
class ClassificationOutcome:
    result: ClassificationResult | None
    attempts: int
    provider: str
    model: str
    latency_ms: int
    error: str | None
    #  Kept for prompt iteration when validation fails, and for receipts on success.
    raw_text: str | None
    cached: bool = False

    @property
    def succeeded(self) -> bool:
        return self.result is not None


@dataclass(slots=True)
class ClassifiableEvent:
    """The subset of a capture event the classifier needs."""

    event_type: str
    source_url: str
    page_title: str
    occurred_at: str
    payload: dict


def _validate(text: str) -> ClassificationResult:
    """Parse and validate provider output, raising ValueError on any problem."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(f"response was not valid JSON: {error}") from error

    try:
        return ClassificationResult.model_validate(data)
    except ValidationError as error:
        raise ValueError(f"response did not match the schema: {error}") from error


async def classify_event(event: ClassifiableEvent, client: AIClient) -> ClassificationOutcome:
    """Classify one event, retrying once if the output fails validation."""
    base_user_prompt = build_user_prompt(
        event_type=event.event_type,
        source_url=event.source_url,
        page_title=event.page_title,
        occurred_at=event.occurred_at,
        payload=event.payload,
    )
    json_schema = classification_json_schema()

    started = time.perf_counter()
    user_prompt = base_user_prompt
    last_error: str | None = None
    last_text: str | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        request = JsonCompletionRequest(
            system=SYSTEM_PROMPT,
            user=user_prompt,
            schema_name=SCHEMA_NAME,
            json_schema=json_schema,
            context={
                "eventType": event.event_type,
                "sourceUrl": event.source_url,
                "pageTitle": event.page_title,
                "occurredAt": event.occurred_at,
                "payload": event.payload,
            },
        )

        try:
            completion = await client.complete_json(request)
        except AIClientError as error:
            # A provider outage is not a schema problem, so retrying the same
            # call immediately would not help; leave it to the queue.
            return ClassificationOutcome(
                result=None,
                attempts=attempt,
                provider=client.provider,
                model=client.model,
                latency_ms=int((time.perf_counter() - started) * 1000),
                error=str(error),
                raw_text=None,
            )

        last_text = completion.text

        try:
            result = _validate(completion.text)
        except ValueError as error:
            last_error = str(error)
            logger.warning(
                "Classification attempt %s/%s failed validation: %s",
                attempt,
                MAX_ATTEMPTS,
                last_error,
            )
            # Show the model its own broken output and the exact error.
            user_prompt = build_repair_prompt(
                base_user_prompt, completion.text, last_error
            )
            continue

        return ClassificationOutcome(
            result=result,
            attempts=attempt,
            provider=completion.provider,
            model=completion.model,
            latency_ms=int((time.perf_counter() - started) * 1000),
            error=None,
            raw_text=completion.text,
        )

    return ClassificationOutcome(
        result=None,
        attempts=MAX_ATTEMPTS,
        provider=client.provider,
        model=client.model,
        latency_ms=int((time.perf_counter() - started) * 1000),
        error=last_error,
        raw_text=last_text,
    )
