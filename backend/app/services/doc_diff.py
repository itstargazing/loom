"""Compare document texts and decide whether divergence is worth flagging."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from difflib import SequenceMatcher, unified_diff

WHITESPACE_RE = re.compile(r"\s+")
PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)


@dataclass(frozen=True, slots=True)
class DiffResult:
    unified: str
    summary: str
    is_meaningful: bool
    ratio: float


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_for_compare(text: str) -> str:
    """Strip formatting noise so whitespace-only edits look identical."""
    collapsed = WHITESPACE_RE.sub(" ", text).strip().casefold()
    return PUNCT_RE.sub("", collapsed)


def compute_diff(
    left_label: str,
    left_text: str,
    right_label: str,
    right_text: str,
    *,
    trivial_ratio: float = 0.98,
) -> DiffResult:
    if left_text == right_text:
        return DiffResult(
            unified="",
            summary="Identical",
            is_meaningful=False,
            ratio=1.0,
        )

    left_norm = normalize_for_compare(left_text)
    right_norm = normalize_for_compare(right_text)
    if left_norm == right_norm:
        return DiffResult(
            unified="",
            summary="Formatting-only differences",
            is_meaningful=False,
            ratio=1.0,
        )

    ratio = SequenceMatcher(None, left_norm, right_norm).ratio()
    lines = list(
        unified_diff(
            left_text.splitlines(),
            right_text.splitlines(),
            fromfile=left_label,
            tofile=right_label,
            lineterm="",
            n=3,
        )
    )
    unified = "\n".join(lines)
    added = sum(
        1 for line in lines if line.startswith("+") and not line.startswith("+++")
    )
    removed = sum(
        1 for line in lines if line.startswith("-") and not line.startswith("---")
    )
    summary = f"{added} line(s) added, {removed} line(s) removed"
    is_meaningful = ratio < trivial_ratio and (added + removed) > 0
    if not is_meaningful and left_norm != right_norm:
        #  Short docs can change a few words without crossing the line threshold.
        is_meaningful = ratio < trivial_ratio
        if is_meaningful and not summary:
            summary = "Content wording changed"
    return DiffResult(
        unified=unified,
        summary=summary or "Content wording changed",
        is_meaningful=is_meaningful,
        ratio=ratio,
    )
