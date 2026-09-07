"""Provider-agnostic AI client interface.

Nothing outside ``app/ai`` should import a vendor SDK or know which provider is
configured. Services depend on :class:`AIClient` so the provider can be swapped
— including for the fully on-device path in Phase 14.
"""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class JsonCompletionRequest:
    """A request for a single JSON object matching ``json_schema``."""

    system: str
    user: str
    schema_name: str
    json_schema: dict[str, Any]
    temperature: float = 0.0
    max_output_tokens: int | None = None
    #  Structured view of the same input, for providers that do not consume
    #  prompts at all (the heuristic stub, and on-device inference later).
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class JsonCompletion:
    """Raw provider output. Validation is the caller's responsibility."""

    text: str
    provider: str
    model: str


class AIClientError(RuntimeError):
    """Raised when the provider could not be reached or returned an error."""


@dataclass(slots=True)
class TextCompletionRequest:
    system: str
    user: str
    temperature: float = 0.2
    max_output_tokens: int | None = None


class AIClient(ABC):
    provider: str
    model: str

    @abstractmethod
    async def complete_json(self, request: JsonCompletionRequest) -> JsonCompletion:
        """Return the provider's raw response text for a JSON-schema request."""

    async def complete_text(self, request: TextCompletionRequest) -> JsonCompletion:
        """Freeform completion used for Ask answers and research briefs."""
        wrapped = JsonCompletionRequest(
            system=request.system,
            user=request.user,
            schema_name="text_completion",
            json_schema={
                "type": "object",
                "additionalProperties": False,
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
            temperature=request.temperature,
            max_output_tokens=request.max_output_tokens,
        )
        completion = await self.complete_json(wrapped)
        try:
            parsed = json.loads(completion.text)
            text = str(parsed.get("text") or completion.text)
        except (json.JSONDecodeError, AttributeError, TypeError):
            text = completion.text
        return JsonCompletion(text=text, provider=completion.provider, model=completion.model)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise AIClientError(f"{self.provider} does not provide embeddings")

    async def aclose(self) -> None:
        """Release any held connections."""
