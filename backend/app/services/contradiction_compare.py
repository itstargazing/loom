"""Decide whether two claims on one topic conflict.

Uses the configured AI client for a targeted comparison. The stub provider
applies number/negation heuristics so the pipeline works offline.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.ai import AIClient, AIClientError, JsonCompletionRequest
from app.prompts.compare_claims import COMPARISON_SCHEMA, SYSTEM_PROMPT, user_prompt

logger = logging.getLogger(__name__)

NUMBER_RE = re.compile(
    r"(?<![A-Za-z])([+-]?\d+(?:\.\d+)?)\s*(%|percent|degrees?|°|celsius|fahrenheit)?",
    re.IGNORECASE,
)
NEGATION_RE = re.compile(
    r"\b(no|not|never|none|without|didn'?t|doesn'?t|isn'?t|aren'?t|wasn'?t|weren'?t)\b",
    re.IGNORECASE,
)


class ClaimComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conflicts: bool
    explanation: str = ""
    confidence: float = Field(ge=0.0, le=1.0)


@dataclass(frozen=True, slots=True)
class ComparisonInput:
    topic: str
    claim_a: str
    claim_b: str
    source_a_url: str
    source_b_url: str


def _numbers(text: str) -> list[tuple[float, str]]:
    found: list[tuple[float, str]] = []
    for match in NUMBER_RE.finditer(text):
        value = float(match.group(1))
        unit = (match.group(2) or "").casefold()
        if unit.startswith("percent"):
            unit = "%"
        elif unit.startswith("degree") or unit in {"°", "celsius", "fahrenheit"}:
            unit = "deg"
        found.append((value, unit))
    return found


def compare_locally(payload: ComparisonInput) -> ClaimComparison:
    """Heuristic comparison used by the stub provider and as a fallback."""
    if payload.claim_a.strip().casefold() == payload.claim_b.strip().casefold():
        return ClaimComparison(
            conflicts=False,
            explanation="The claims are the same statement.",
            confidence=0.9,
        )

    numbers_a = _numbers(payload.claim_a)
    numbers_b = _numbers(payload.claim_b)
    if numbers_a and numbers_b:
        for value_a, unit_a in numbers_a:
            for value_b, unit_b in numbers_b:
                if unit_a != unit_b and unit_a and unit_b:
                    continue
                if abs(value_a - value_b) < 1e-9:
                    continue
                #  Relative difference large enough to matter for reported figures.
                scale = max(abs(value_a), abs(value_b), 1.0)
                if abs(value_a - value_b) / scale >= 0.05:
                    unit_label = f" {unit_a}" if unit_a else ""
                    return ClaimComparison(
                        conflicts=True,
                        explanation=(
                            f"The sources report different figures on {payload.topic}: "
                            f"{value_a:g}{unit_label} versus {value_b:g}{unit_label}."
                        ),
                        confidence=0.7,
                    )

    neg_a = bool(NEGATION_RE.search(payload.claim_a))
    neg_b = bool(NEGATION_RE.search(payload.claim_b))
    if neg_a != neg_b and len(payload.claim_a.split()) >= 6 and len(payload.claim_b.split()) >= 6:
        return ClaimComparison(
            conflicts=True,
            explanation=(
                f"One source affirms and the other denies a claim about {payload.topic}."
            ),
            confidence=0.55,
        )

    return ClaimComparison(
        conflicts=False,
        explanation="No clear factual conflict was detected.",
        confidence=0.4,
    )


async def compare_claims(client: AIClient, payload: ComparisonInput) -> ClaimComparison:
    """Run the provider comparison; fall back to heuristics on failure."""
    if client.provider == "stub":
        return compare_locally(payload)

    request = JsonCompletionRequest(
        system=SYSTEM_PROMPT,
        user=user_prompt(
            topic=payload.topic,
            claim_a=payload.claim_a,
            claim_b=payload.claim_b,
            source_a=payload.source_a_url,
            source_b=payload.source_b_url,
        ),
        schema_name="claim_comparison",
        json_schema=COMPARISON_SCHEMA,
        temperature=0.0,
        max_output_tokens=400,
        context={
            "kind": "claim_comparison",
            "topic": payload.topic,
            "claimA": payload.claim_a,
            "claimB": payload.claim_b,
            "sourceAUrl": payload.source_a_url,
            "sourceBUrl": payload.source_b_url,
        },
    )
    try:
        completion = await client.complete_json(request)
        data = json.loads(completion.text)
        return ClaimComparison.model_validate(data)
    except (AIClientError, ValidationError, json.JSONDecodeError, KeyError) as error:
        logger.warning("Claim comparison failed (%s); using local heuristic", error)
        return compare_locally(payload)
