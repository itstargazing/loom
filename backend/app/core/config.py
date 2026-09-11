from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _asyncpg_url(url: str) -> str:
    """Render/Railway/Fly hand out postgres:// or postgresql://. SQLAlchemy async needs +asyncpg."""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        return "postgresql+asyncpg://" + url[len("postgresql://") :]
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://loom:loom@localhost:5432/loom"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = (
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:3001,http://127.0.0.1:3001"
    )
    #  Viewer uploads hit the API directly; the extension id is not known ahead.
    cors_origin_regex: str = r"chrome-extension://.*"

    # --- Auth ------------------------------------------------------------
    #  development | production. Production refuses AUTH_MODE=stub at startup.
    environment: str = "development"
    #  stub = shared bearer (local only). jwt = per-user tokens (Clerk/Supabase/
    #  mint_dev_jwt). Set AUTH_MODE=jwt before more than one real user.
    auth_mode: str = "stub"
    # Shared secret between the extension, dashboard, and this API. Every
    # request maps to a single development user when AUTH_MODE=stub.
    stub_auth_token: str = "loom-dev-token"
    stub_user_id: str = "dev-user"
    jwt_secret: str = "loom-dev-jwt-secret"
    jwt_algorithms: str = "HS256"
    #  Optional JWKS for Clerk/Supabase asymmetric JWTs (RS256).
    jwt_jwks_url: str = ""
    jwt_audience: str = ""
    jwt_issuer: str = ""

    #  Caps the synchronous reclassify endpoint (the expensive user-triggered
    #  AI path). The background worker is bounded separately by batch size.
    classification_rate_limit_per_minute: int = 30
    llm_rate_limit_per_minute: int = 20
    #  Below this, a classification is held for digest review instead of routed.
    classification_auto_route_min_confidence: float = 0.5

    # --- Observability ---------------------------------------------------
    #  Optional. When set, errors are reported to Sentry.
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.0

    # --- Capture ingest --------------------------------------------------
    max_events_per_batch: int = 100
    max_payload_chars: int = 200_000
    #  Bounds the Redis stream so a backlog cannot consume unbounded memory.
    capture_stream_max_len: int = 100_000

    # --- Worker ----------------------------------------------------------
    worker_batch_size: int = 50
    worker_block_ms: int = 5_000
    # Entries left unacknowledged this long are reclaimed by another worker.
    worker_claim_min_idle_ms: int = 60_000

    # --- AI --------------------------------------------------------------
    #  "openai" for any OpenAI-compatible endpoint, or "stub" for the offline
    #  heuristic classifier. Defaults to the stub so a fresh checkout runs with
    #  no API key; an empty key with provider "openai" falls back to the stub.
    #  "claude", "openai", or "stub". Empty key with claude/openai falls back to stub.
    ai_provider: str = "stub"
    ai_api_key: str = ""
    ai_base_url: str = "https://api.openai.com/v1"
    ai_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5"
    ai_timeout_seconds: float = 30.0
    embedding_provider: str = "stub"
    embedding_api_key: str = ""
    embedding_base_url: str = "https://api.openai.com/v1"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    #  Classification output is small; this only guards against runaway loops.
    ai_max_output_tokens: int = 2_000

    #  Classification batch size is smaller than the capture batch because each
    #  entry costs a model call.
    classification_batch_size: int = 10

    # --- Contradiction watcher ------------------------------------------
    #  How often the background job rescans recent claims for conflicting pairs.
    contradiction_watch_interval_seconds: float = 30.0
    #  Only claims seen within this many days are candidates for pairing.
    contradiction_lookback_days: int = 30

    # --- Reading compiler -----------------------------------------------
    #  Sections with less visual attention than this are not filed as read.
    #  Matches the extension's default dwellThresholdMs.
    reading_dwell_threshold_ms: int = 3_000

    # --- Form filler ----------------------------------------------------
    #  Uploaded PDFs land here; never go over the extension message bus.
    form_storage_dir: str = ".data/forms"
    #  Matches below this confidence stay blank for manual entry.
    form_match_min_confidence: float = 0.75
    form_upload_max_bytes: int = 20 * 1024 * 1024

    # --- Live doc diff --------------------------------------------------
    #  How often watched document URLs are re-snapshotted from capture events.
    live_doc_diff_interval_seconds: float = 45.0

    # --- Auto-attach ----------------------------------------------------
    #  Suggestions below this confidence stay hidden (never auto-filled).
    auto_attach_min_confidence: float = 0.75

    # --- Local-only sensitive mode --------------------------------------
    #  Comma-separated hostname suffixes always treated as local-only
    #  (in addition to each user's custom list).
    #  Hostname suffixes (e.g. .gov) or exact hosts (bank.example.com).
    local_only_domains: str = ".gov,bank.example.com"

    @field_validator("database_url", mode="before")
    @classmethod
    def require_asyncpg(cls, value: str) -> str:
        return _asyncpg_url(value)

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def local_only_domains_default(self) -> list[str]:
        return [
            part.strip()
            for part in self.local_only_domains.split(",")
            if part.strip()
        ]


settings = Settings()
