"""Stable identity keys for skill store entries.

Two captures are "the same entry" when their key parts match after
normalisation. Hashing keeps the column fixed-width regardless of how long the
underlying quote or clause is, and keeps it usable in an index.
"""

import hashlib
import re
import unicodedata

from app.models.skill_stores import DEDUP_KEY_LENGTH

_WHITESPACE = re.compile(r"\s+")
#  Punctuation is dropped so smart quotes, trailing periods, and stray brackets
#  do not make the same sentence look like two different ones.
_PUNCTUATION = re.compile(r"[^\w\s]", re.UNICODE)


def normalize(value: str) -> str:
    """Casefold, strip punctuation, and collapse whitespace."""
    # NFKC first, so typographic variants of the same character unify.
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = _PUNCTUATION.sub(" ", normalized)
    return _WHITESPACE.sub(" ", normalized).strip()


def dedup_key(*parts: str | None) -> str:
    """Hash normalised parts into a fixed-width identity key.

    Parts are joined with a separator that cannot appear after normalisation, so
    ("ab", "c") and ("a", "bc") never collide.
    """
    joined = "\x1f".join(normalize(part) for part in parts if part is not None)
    digest = hashlib.sha256(joined.encode("utf-8")).hexdigest()
    return digest[:DEDUP_KEY_LENGTH]
