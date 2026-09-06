import logging

from app.ai.base import AIClient
from app.ai.openai_client import OpenAICompatibleClient
from app.ai.stub_client import StubAIClient
from app.core.config import settings

logger = logging.getLogger(__name__)

_client: AIClient | None = None
_local_client: AIClient | None = None


def _build_client() -> AIClient:
    if settings.ai_provider == "openai":
        if not settings.ai_api_key:
            # Falling back keeps a fresh checkout runnable instead of failing at
            # the first classification.
            logger.warning(
                "AI_PROVIDER is 'openai' but AI_API_KEY is empty; "
                "falling back to the heuristic stub client."
            )
            return StubAIClient()

        return OpenAICompatibleClient(
            api_key=settings.ai_api_key,
            base_url=settings.ai_base_url,
            model=settings.ai_model,
            timeout_seconds=settings.ai_timeout_seconds,
        )

    if settings.ai_provider != "stub":
        logger.warning(
            "Unknown AI_PROVIDER %r; falling back to the heuristic stub client.",
            settings.ai_provider,
        )

    return StubAIClient()


def get_ai_client() -> AIClient:
    """Process-wide client, so the HTTP connection pool is reused."""
    global _client
    if _client is None:
        _client = _build_client()
        logger.info("AI client: provider=%s model=%s", _client.provider, _client.model)
    return _client


def get_local_ai_client() -> AIClient:
    """Heuristic client used for sensitive-domain (Phase 14) classification.

    Never calls a cloud model. Recorded as provider ``local`` so the dashboard
    can show the tradeoff plainly.
    """
    global _local_client
    if _local_client is None:
        _local_client = StubAIClient(provider="local", model="heuristic-v1")
        logger.info(
            "Local AI client: provider=%s model=%s",
            _local_client.provider,
            _local_client.model,
        )
    return _local_client


async def close_ai_client() -> None:
    global _client, _local_client
    if _client is not None:
        await _client.aclose()
        _client = None
    _local_client = None
