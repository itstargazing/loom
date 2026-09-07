import logging

from app.ai.anthropic_client import AnthropicClient
from app.ai.base import AIClient
from app.ai.openai_client import OpenAICompatibleClient
from app.ai.stub_client import StubAIClient
from app.core.config import settings

logger = logging.getLogger(__name__)

_client: AIClient | None = None
_local_client: AIClient | None = None
_embed_client: AIClient | None = None


def _cloud_key() -> str:
    if settings.ai_provider == "claude":
        return settings.anthropic_api_key or settings.ai_api_key
    return settings.ai_api_key


def _build_client() -> AIClient:
    provider = settings.ai_provider
    if provider == "claude":
        key = _cloud_key()
        if not key:
            logger.warning(
                "AI_PROVIDER is 'claude' but no Anthropic key is set; "
                "falling back to the heuristic stub client."
            )
            return StubAIClient()
        return AnthropicClient(
            api_key=key,
            model=settings.anthropic_model,
            timeout_seconds=settings.ai_timeout_seconds,
        )

    if provider == "openai":
        if not settings.ai_api_key:
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

    if provider != "stub":
        logger.warning(
            "Unknown AI_PROVIDER %r; falling back to the heuristic stub client.",
            provider,
        )
    return StubAIClient()


def _build_embed_client() -> AIClient:
    provider = settings.embedding_provider
    key = settings.embedding_api_key or settings.ai_api_key
    if provider == "openai" and key:
        return OpenAICompatibleClient(
            api_key=key,
            base_url=settings.embedding_base_url,
            model=settings.embedding_model,
            timeout_seconds=settings.ai_timeout_seconds,
        )
    if provider == "openai" and not key:
        logger.warning("EMBEDDING_PROVIDER is openai without a key; using hashed stub embeddings.")
    return StubAIClient(provider="stub-embed", model="hash-v1")


def get_ai_client() -> AIClient:
    """Process-wide client, so the HTTP connection pool is reused."""
    global _client
    if _client is None:
        _client = _build_client()
        logger.info("AI client: provider=%s model=%s", _client.provider, _client.model)
    return _client


def get_embedding_client() -> AIClient:
    global _embed_client
    if _embed_client is None:
        _embed_client = _build_embed_client()
        logger.info(
            "Embedding client: provider=%s model=%s",
            _embed_client.provider,
            _embed_client.model,
        )
    return _embed_client


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
    global _client, _local_client, _embed_client
    if _client is not None:
        await _client.aclose()
        _client = None
    if _embed_client is not None and _embed_client is not _client:
        await _embed_client.aclose()
        _embed_client = None
    else:
        _embed_client = None
    _local_client = None
