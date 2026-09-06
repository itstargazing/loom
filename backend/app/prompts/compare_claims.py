"""Prompt and schema for pairwise claim comparison inside a topic cluster."""

from typing import Any

SYSTEM_PROMPT = """\
You compare two factual claims on the same topic from different sources.

Decide whether they state conflicting facts or figures (not mere differences of \
emphasis, wording, or time period). When they conflict, write a short plain-language \
explanation of the disagreement for a reader who has not seen the sources.

Return JSON matching the schema. Set conflicts to false when the claims agree, \
are about different aspects of the topic, or cannot be compared.
"""


def user_prompt(*, topic: str, claim_a: str, claim_b: str, source_a: str, source_b: str) -> str:
    return (
        f"Topic: {topic}\n\n"
        f"Claim A (from {source_a or 'unknown source'}):\n{claim_a}\n\n"
        f"Claim B (from {source_b or 'unknown source'}):\n{claim_b}\n"
    )


COMPARISON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "conflicts": {"type": "boolean"},
        "explanation": {"type": "string"},
        "confidence": {"type": "number"},
    },
    "required": ["conflicts", "explanation", "confidence"],
}
