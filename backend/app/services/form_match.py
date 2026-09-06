"""Match PDF form field names to profile values.

Fuzzy aliases cover the common labels; a light AI (or stub heuristic) pass
handles leftovers. Low-confidence matches are left blank — never guessed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from app.core.config import settings

TOKEN_RE = re.compile(r"[a-z0-9]+")

#  Profile key → alternate labels people put on forms.
PROFILE_ALIASES: dict[str, tuple[str, ...]] = {
    "full_name": ("name", "full name", "applicant name", "legal name", "your name"),
    "first_name": ("first name", "given name", "fname", "forename"),
    "last_name": ("last name", "surname", "family name", "lname"),
    "email": ("email", "e-mail", "email address", "mail"),
    "phone": ("phone", "telephone", "mobile", "cell", "phone number"),
    "address_line1": ("address", "street", "street address", "address line 1", "addr1"),
    "address_line2": ("address line 2", "apt", "suite", "unit", "addr2"),
    "city": ("city", "town"),
    "state": ("state", "province", "region"),
    "postal_code": ("zip", "zip code", "postal", "postal code", "postcode"),
    "country": ("country", "nation"),
    "date_of_birth": ("date of birth", "dob", "birth date", "birthday"),
    "ssn": ("ssn", "social security", "social security number"),
    "company": ("company", "organization", "employer", "org"),
    "title": ("title", "job title", "position", "role"),
}


def normalize_label(label: str) -> str:
    return " ".join(TOKEN_RE.findall(label.casefold()))


@dataclass(frozen=True, slots=True)
class FieldMatch:
    field_name: str
    field_type: str
    profile_key: str | None
    value: str | None
    confidence: float
    needs_manual: bool
    reason: str


def _best_alias_score(field_norm: str, profile_key: str) -> float:
    labels = (profile_key.replace("_", " "),) + PROFILE_ALIASES.get(profile_key, ())
    best = 0.0
    for label in labels:
        label_norm = normalize_label(label)
        if not label_norm:
            continue
        if field_norm == label_norm:
            return 1.0
        field_tokens = set(field_norm.split())
        label_tokens = set(label_norm.split())
        #  Token containment, not substring: "name" must not match "filename".
        if label_tokens and label_tokens <= field_tokens:
            best = max(best, 0.92)
        if field_tokens and field_tokens <= label_tokens:
            best = max(best, 0.92)
        best = max(best, SequenceMatcher(None, field_norm, label_norm).ratio())
    return best


def effective_profile(profile: dict[str, Any]) -> dict[str, Any]:
    """Drop blanks and synthesize full_name from first + last when missing."""
    values = {
        str(key): value
        for key, value in profile.items()
        if value is not None and str(value).strip() != ""
    }
    if "full_name" not in values:
        first = str(values.get("first_name", "")).strip()
        last = str(values.get("last_name", "")).strip()
        combined = f"{first} {last}".strip()
        if combined:
            values["full_name"] = combined
    return values


def match_field_locally(
    field_name: str,
    field_type: str,
    profile: dict[str, Any],
    *,
    min_confidence: float | None = None,
) -> FieldMatch:
    threshold = (
        settings.form_match_min_confidence
        if min_confidence is None
        else min_confidence
    )
    field_norm = normalize_label(field_name)
    if not field_norm:
        return FieldMatch(
            field_name=field_name,
            field_type=field_type,
            profile_key=None,
            value=None,
            confidence=0.0,
            needs_manual=True,
            reason="Empty field name",
        )

    best_key: str | None = None
    best_score = 0.0
    for key, raw in profile.items():
        if raw is None or str(raw).strip() == "":
            continue
        score = _best_alias_score(field_norm, str(key))
        if score > best_score:
            best_score = score
            best_key = str(key)

    if best_key is None or best_score < threshold:
        return FieldMatch(
            field_name=field_name,
            field_type=field_type,
            profile_key=best_key,
            value=None,
            confidence=best_score,
            needs_manual=True,
            reason=(
                f"Best candidate {best_key!r} scored {best_score:.2f}; left blank"
                if best_key
                else "No profile key resembled this field"
            ),
        )

    return FieldMatch(
        field_name=field_name,
        field_type=field_type,
        profile_key=best_key,
        value=str(profile[best_key]),
        confidence=best_score,
        needs_manual=False,
        reason=f"Matched profile key {best_key!r}",
    )


def match_document_fields(
    fields: list[dict[str, Any]],
    profile: dict[str, Any],
    *,
    min_confidence: float | None = None,
) -> list[FieldMatch]:
    resolved = effective_profile(profile)
    return [
        match_field_locally(
            str(field.get("name", "")),
            str(field.get("type", "unknown")),
            resolved,
            min_confidence=min_confidence,
        )
        for field in fields
    ]
