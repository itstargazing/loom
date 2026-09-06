"""Provider-agnostic AI client interface.

Nothing outside ``app/ai`` should import a vendor SDK or know which provider is
configured. Services depend on :class:`AIClient` so the provider can be swapped
— including for the fully on-device path in Phase 14.
"""

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


class AIClient(ABC):
    provider: str
    model: str

    @abstractmethod
    async def complete_json(self, request: JsonCompletionRequest) -> JsonCompletion:
        """Return the provider's raw response text for a JSON-schema request."""

    async def aclose(self) -> None:
        """Release any held connections."""
