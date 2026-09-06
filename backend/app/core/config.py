from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://loom:loom@localhost:5432/loom"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    #  Viewer uploads hit the API directly; the extension id is not known ahead.
    cors_origin_regex: str = r"chrome-extension://.*"

    # --- Stub auth -------------------------------------------------------
    # Shared secret between the extension, dashboard, and this API. Every
    # request maps to a single development user. Swap ``get_current_user_id``
    # when Clerk/Supabase sessions land; callers already depend on that hook.
    stub_auth_token: str = "loom-dev-token"
    stub_user_id: str = "dev-user"

    #  Caps the synchronous reclassify endpoint (the expensive user-triggered
    #  AI path). The background worker is bounded separately by batch size.
    classification_rate_limit_per_minute: int = 30

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
    ai_provider: str = "stub"
    ai_api_key: str = ""
    ai_base_url: str = "https://api.openai.com/v1"
    ai_model: str = "gpt-4o-mini"
    ai_timeout_seconds: float = 30.0
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
