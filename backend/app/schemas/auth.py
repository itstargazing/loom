"""Auth / account schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel


class AccountOut(BaseModel):
    model_config = ConfigDict(
        from_attributes=True, alias_generator=to_camel, populate_by_name=True
    )

    user_id: str
    display_name: str
    email: str | None
    auth_mode: str
    created_at: datetime
    updated_at: datetime
    #  Filled by the auth router from the live AUTH_MODE setting.
    session_note: str = ""


class AccountPatch(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    display_name: str | None = None
    email: str | None = None

    @model_validator(mode="after")
    def _at_least_one(self) -> "AccountPatch":
        if not self.model_fields_set:
            raise ValueError("No fields to update")
        return self


class LogoutOut(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    ok: bool = True
    detail: str = "Clear the bearer token on the client to end this session."


class DeleteAccountIn(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    confirm: str = Field(
        description='Type "DELETE" to permanently erase this user\'s LOOM data.'
    )

    @model_validator(mode="after")
    def _must_confirm(self) -> "DeleteAccountIn":
        if self.confirm.strip() != "DELETE":
            raise ValueError('Confirmation must be exactly "DELETE"')
        return self
