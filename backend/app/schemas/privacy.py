"""Privacy / local-mode settings schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from app.services.local_mode import normalize_domain_pattern


class PrivacySettingsOut(BaseModel):
    model_config = ConfigDict(
        from_attributes=True, alias_generator=to_camel, populate_by_name=True
    )

    #  Domains the user edited (saved).
    local_only_domains: list[str]
    #  Built-in sensitive suffixes always applied.
    default_domains: list[str] = Field(default_factory=list)
    #  Union used for matching.
    effective_domains: list[str] = Field(default_factory=list)
    updated_at: datetime | None = None
    tradeoff_note: str = (
        "Local-only domains skip cloud AI and use heuristics instead — "
        "they are not on-device-only. Capture events still sync to your LOOM "
        "cloud backend so Ask and skill stores stay filled. See /legal/privacy."
    )


class PrivacySettingsIn(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    local_only_domains: list[str] = Field(default_factory=list)

    @field_validator("local_only_domains")
    @classmethod
    def _normalize_domains(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for item in value:
            pattern = normalize_domain_pattern(str(item))
            if not pattern or pattern in seen:
                continue
            seen.add(pattern)
            cleaned.append(pattern)
        return cleaned[:100]


class LocalModeCheckOut(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    url: str
    hostname: str
    local_mode: bool
    matched_pattern: str | None = None
