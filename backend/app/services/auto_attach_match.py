"""Match an upload field's context against the recent-document index."""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Sequence

from app.core.config import settings

TOKEN_RE = re.compile(r"[a-z0-9]+")

DOC_TYPE_ALIASES: dict[str, tuple[str, ...]] = {
    "resume": ("resume", "cv", "curriculum vitae", "curriculum", "vitae"),
    "id_scan": (
        "id",
        "id scan",
        "identity",
        "passport",
        "drivers license",
        "driver license",
        "government id",
        "photo id",
    ),
    "transcript": ("transcript", "academic record", "grades", "grade report"),
    "pdf": ("pdf", "document", "attachment", "file"),
    "image": ("image", "photo", "picture", "scan", "jpeg", "png"),
    "other": (),
}


def normalize(text: str) -> str:
    return " ".join(TOKEN_RE.findall(text.casefold()))


@dataclass(frozen=True, slots=True)
class RankedDocument:
    document_id: object
    filename: str
    doc_type: str
    source_url: str
    summary: str
    has_file: bool
    confidence: float
    reason: str


def _accept_ok(accept: str | None, mime_type: str, filename: str) -> bool:
    if not accept or not accept.strip():
        return True
    accept_l = accept.casefold()
    mime_l = (mime_type or "").casefold()
    name_l = filename.casefold()
    if "image/" in accept_l or accept_l.strip() == "image/*":
        return mime_l.startswith("image/") or name_l.endswith(
            (".png", ".jpg", ".jpeg", ".gif", ".webp")
        )
    if "pdf" in accept_l or "application/pdf" in accept_l:
        return mime_l == "application/pdf" or name_l.endswith(".pdf")
    #  Loose accept lists like ".pdf,.doc" — any extension token match.
    tokens = {part.strip().lstrip(".") for part in accept_l.split(",") if part.strip()}
    if any(name_l.endswith(f".{token}") for token in tokens if token and "/" not in token):
        return True
    return True  # Unknown accept: do not hard-filter.


#  Generic container types should not beat a specific resume/ID match just
#  because the field mentions "PDF" or "file".
GENERIC_DOC_TYPES = frozenset({"pdf", "image", "other"})
WEAK_NAME_TOKENS = frozenset(
    {"pdf", "doc", "docx", "file", "document", "scan", "image", "photo", "png", "jpg"}
)


def score_document(
    field_text: str,
    *,
    filename: str,
    doc_type: str,
    summary: str,
    accept: str | None,
    mime_type: str,
) -> tuple[float, str]:
    if not _accept_ok(accept, mime_type, filename):
        return 0.0, "Does not match the field's accept filter"

    field_norm = normalize(field_text)
    if not field_norm:
        return 0.0, "Upload field has no label context"

    best = 0.0
    reason = "Weak overlap with field context"
    field_tokens = set(field_norm.split())

    name_norm = normalize(filename.rsplit(".", 1)[0])
    if name_norm:
        name_tokens = set(name_norm.split())
        overlap = name_tokens & field_tokens - WEAK_NAME_TOKENS
        if overlap:
            best = max(best, 0.96)
            reason = "Filename matches field label"
        elif name_norm in field_norm or field_norm in name_norm:
            best = max(best, 0.95)
            reason = "Filename matches field label"
        else:
            ratio = SequenceMatcher(None, field_norm, name_norm).ratio()
            if ratio > best:
                best = ratio
                reason = "Filename similar to field label"

    aliases = DOC_TYPE_ALIASES.get(doc_type, ())
    for alias in (doc_type.replace("_", " "),) + aliases:
        alias_norm = normalize(alias)
        if not alias_norm:
            continue
        alias_tokens = set(alias_norm.split())
        if alias_tokens and alias_tokens <= field_tokens:
            type_score = 0.8 if doc_type in GENERIC_DOC_TYPES else 0.93
            if type_score > best:
                best = type_score
                reason = f"Field asks for a {doc_type.replace('_', ' ')}"
        else:
            ratio = SequenceMatcher(None, field_norm, alias_norm).ratio()
            if doc_type in GENERIC_DOC_TYPES:
                ratio = min(ratio, 0.8)
            if ratio > best:
                best = ratio
                reason = f"Field wording overlaps {doc_type.replace('_', ' ')}"

    summary_norm = normalize(summary)[:400]
    if summary_norm:
        #  Shared tokens between field context and document summary.
        shared = set(field_norm.split()) & set(summary_norm.split()) - WEAK_NAME_TOKENS
        if shared:
            token_score = min(0.9, 0.55 + 0.1 * len(shared))
            if token_score > best:
                best = token_score
                reason = "Summary keywords match the field"

    return best, reason


def rank_documents(
    *,
    label_text: str,
    surrounding_text: str,
    field_name: str | None,
    accept: str | None,
    documents: Sequence[tuple[object, str, str, str, str, str | None, str]],
    min_confidence: float | None = None,
) -> list[RankedDocument]:
    threshold = (
        settings.auto_attach_min_confidence
        if min_confidence is None
        else min_confidence
    )
    field_text = " ".join(
        part for part in (label_text, surrounding_text, field_name or "") if part
    )
    ranked: list[RankedDocument] = []
    for (
        document_id,
        filename,
        doc_type,
        source_url,
        summary,
        storage_path,
        mime_type,
    ) in documents:
        confidence, reason = score_document(
            field_text,
            filename=filename,
            doc_type=doc_type,
            summary=summary,
            accept=accept,
            mime_type=mime_type,
        )
        if confidence < threshold:
            continue
        ranked.append(
            RankedDocument(
                document_id=document_id,
                filename=filename,
                doc_type=doc_type,
                source_url=source_url,
                summary=summary,
                has_file=bool(storage_path),
                confidence=round(confidence, 3),
                reason=reason,
            )
        )
    ranked.sort(
        key=lambda row: (
            row.confidence,
            0 if row.doc_type in GENERIC_DOC_TYPES else 1,
            1 if row.has_file else 0,
        ),
        reverse=True,
    )
    return ranked


def infer_doc_type(filename: str, title: str, summary: str) -> str:
    blob = normalize(f"{filename} {title} {summary[:500]}")
    for doc_type, aliases in DOC_TYPE_ALIASES.items():
        if doc_type in ("pdf", "image", "other"):
            continue
        for alias in (doc_type.replace("_", " "),) + aliases:
            if normalize(alias) and normalize(alias) in blob:
                return doc_type
    name = filename.casefold()
    if name.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
        return "image"
    if name.endswith(".pdf") or "pdf" in blob:
        return "pdf"
    return "other"


def summarize_text(text: str, limit: int = 400) -> str:
    collapsed = re.sub(r"\s+", " ", text).strip()
    if len(collapsed) <= limit:
        return collapsed
    return f"{collapsed[: limit - 1]}…"
