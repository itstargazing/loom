"""OpenAI-compatible chat completions client.

Talks to the REST API directly with httpx rather than a vendor SDK, so any
OpenAI-compatible gateway works by changing ``AI_BASE_URL``.
"""

import logging
from typing import Any

import httpx

from app.ai.base import AIClient, AIClientError, JsonCompletion, JsonCompletionRequest

logger = logging.getLogger(__name__)


class OpenAICompatibleClient(AIClient):
    provider = "openai"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: float,
    ) -> None:
        self.model = model
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=timeout_seconds,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

    async def complete_json(self, request: JsonCompletionRequest) -> JsonCompletion:
        body: dict[str, Any] = {
            "model": self.model,
            "temperature": request.temperature,
            "messages": [
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.user},
            ],
            # Structured Outputs: the provider enforces the schema, which removes
            # most malformed-JSON failures before they reach our validator.
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": request.schema_name,
                    "strict": True,
                    "schema": request.json_schema,
                },
            },
        }
        if request.max_output_tokens is not None:
            body["max_tokens"] = request.max_output_tokens

        try:
            response = await self._client.post("/chat/completions", json=body)
        except httpx.HTTPError as error:
            raise AIClientError(f"Request to model provider failed: {error}") from error

        if response.status_code >= 400:
            raise AIClientError(
                f"Model provider returned HTTP {response.status_code}: {response.text[:500]}"
            )

        try:
            payload = response.json()
            choice = payload["choices"][0]
            text = choice["message"]["content"] or ""
        except (KeyError, IndexError, ValueError) as error:
            raise AIClientError(f"Unexpected provider response shape: {error}") from error

        # Hit when the model was cut off mid-object, which produces invalid JSON.
        if choice.get("finish_reason") == "length":
            logger.warning("Model output truncated by max_tokens")

        return JsonCompletion(
            text=text,
            provider=self.provider,
            model=payload.get("model", self.model),
        )

    async def aclose(self) -> None:
        await self._client.aclose()
