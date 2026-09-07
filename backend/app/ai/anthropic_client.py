"""Anthropic Messages API client (Claude).

Uses a forced tool call so the model must return JSON matching our schema —
the same contract the OpenAI-compatible client meets with Structured Outputs.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.ai.base import (
    AIClient,
    AIClientError,
    JsonCompletion,
    JsonCompletionRequest,
    TextCompletionRequest,
)

logger = logging.getLogger(__name__)


class AnthropicClient(AIClient):
    provider = "claude"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: float,
    ) -> None:
        self.model = model
        self._client = httpx.AsyncClient(
            base_url="https://api.anthropic.com",
            timeout=timeout_seconds,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )

    async def complete_json(self, request: JsonCompletionRequest) -> JsonCompletion:
        body: dict[str, Any] = {
            "model": self.model,
            "max_tokens": request.max_output_tokens or 2000,
            "temperature": request.temperature,
            "system": request.system,
            "messages": [{"role": "user", "content": request.user}],
            "tools": [
                {
                    "name": request.schema_name[:64],
                    "description": "Return the structured result.",
                    "input_schema": request.json_schema,
                }
            ],
            "tool_choice": {"type": "tool", "name": request.schema_name[:64]},
        }
        payload = await self._post("/v1/messages", body)
        text = self._tool_input_text(payload)
        return JsonCompletion(text=text, provider=self.provider, model=payload.get("model", self.model))

    async def complete_text(self, request: TextCompletionRequest) -> JsonCompletion:
        body: dict[str, Any] = {
            "model": self.model,
            "max_tokens": request.max_output_tokens or 2000,
            "temperature": request.temperature,
            "system": request.system,
            "messages": [{"role": "user", "content": request.user}],
        }
        payload = await self._post("/v1/messages", body)
        text = self._plain_text(payload)
        return JsonCompletion(text=text, provider=self.provider, model=payload.get("model", self.model))

    async def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        try:
            response = await self._client.post(path, json=body)
        except httpx.HTTPError as error:
            raise AIClientError(f"Request to Claude failed: {error}") from error
        if response.status_code >= 400:
            raise AIClientError(
                f"Claude returned HTTP {response.status_code}: {response.text[:500]}"
            )
        try:
            return response.json()
        except ValueError as error:
            raise AIClientError(f"Claude returned non-JSON: {error}") from error

    @staticmethod
    def _tool_input_text(payload: dict[str, Any]) -> str:
        for block in payload.get("content") or []:
            if block.get("type") == "tool_use":
                return json.dumps(block.get("input") or {})
        raise AIClientError("Claude response had no tool_use payload")

    @staticmethod
    def _plain_text(payload: dict[str, Any]) -> str:
        parts: list[str] = []
        for block in payload.get("content") or []:
            if block.get("type") == "text":
                parts.append(str(block.get("text") or ""))
        return "\n".join(parts).strip()

    async def aclose(self) -> None:
        await self._client.aclose()
