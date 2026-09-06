"""APA and MLA strings from whatever bibliographic metadata we have.

Classification extracts author, work, publisher, and date when they are present.
This module turns those fields — plus the source URL as a last resort — into
the two styles the dashboard can switch between. Missing pieces are omitted
rather than invented, so a citation with only a page title and a URL is still
a usable reference.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

CITATION_STYLES = ("apa", "mla")
YEAR_RE = re.compile(r"\b(1[5-9]\d{2}|20\d{2}|21\d{2})\b")


@dataclass(frozen=True, slots=True)
class CitationMeta:
    author: str | None = None
    work_title: str | None = None
    publisher: str | None = None
    published_date: str | None = None
    source_url: str = ""
    page_title: str = ""


def site_name(url: str) -> str:
    host = urlparse(url).hostname or ""
    if host.startswith("www."):
        host = host[4:]
    return host


def _clean(value: str | None) -> str:
    return (value or "").strip()


def _year(published_date: str | None) -> str | None:
    if not published_date:
        return None
    match = YEAR_RE.search(published_date)
    return match.group(1) if match else None


def _title(meta: CitationMeta) -> str:
    return _clean(meta.work_title) or _clean(meta.page_title) or "Untitled"


def _container(meta: CitationMeta) -> str:
    return _clean(meta.publisher) or site_name(meta.source_url)


def _invert_author(author: str) -> str:
    """APA: 'Jane Hansen' -> 'Hansen, J.'; leave 'Hansen, J.' and orgs alone."""
    name = _clean(author)
    if not name:
        return ""
    if "," in name or " et al" in name.casefold():
        return name
    parts = name.split()
    if len(parts) < 2:
        return name
    if any(len(part) > 1 and part.isupper() for part in parts):
        # Acronym-heavy org names (WHO, NASA) stay as written.
        return name
    last = parts[-1]
    initials = " ".join(f"{part[0]}." for part in parts[:-1] if part)
    return f"{last}, {initials}".strip()


def format_apa(meta: CitationMeta) -> str:
    author = _invert_author(meta.author or "")
    year = _year(meta.published_date) or "n.d."
    title = _title(meta)
    container = _container(meta)
    url = _clean(meta.source_url)

    if author:
        head = f"{author} ({year}). {title}."
    else:
        head = f"{title}. ({year})."

    parts = [head]
    if container and container.casefold() not in title.casefold():
        parts.append(f"{container}.")
    if url:
        parts.append(url)
    return " ".join(parts)


def format_mla(meta: CitationMeta) -> str:
    author = _clean(meta.author)
    title = _title(meta)
    container = _container(meta)
    year = _year(meta.published_date) or _clean(meta.published_date)
    url = _clean(meta.source_url)

    chunks: list[str] = []
    if author:
        ended = author.endswith(".")
        chunks.append(author if ended else f"{author}.")
    chunks.append(f'"{title}."')
    if container:
        tail = container if container.endswith(",") else f"{container},"
        chunks.append(tail)
    if year:
        chunks.append(f"{year},")
    if url:
        chunks.append(url if url.endswith(".") else f"{url}.")
    return " ".join(chunks)


def format_styles(meta: CitationMeta) -> dict[str, str]:
    return {"apa": format_apa(meta), "mla": format_mla(meta)}


def bibliography_filename(collection_name: str | None, style: str, fmt: str) -> str:
    raw = (collection_name or "citations").strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", raw).strip("-") or "citations"
    return f"{slug}-{style}.{fmt}"


def render_bibliography(entries: list[str], *, style: str, format: str, heading: str) -> str:
    """Plain text or Markdown bibliography, sorted as given."""
    if format == "md":
        lines = [f"# {heading}", "", f"*Cited in {style.upper()}.*", ""]
        if not entries:
            lines.append("_No citations in this collection._")
            return "\n".join(lines) + "\n"
        for index, entry in enumerate(entries, start=1):
            lines.append(f"{index}. {entry}")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    if not entries:
        return ""
    return "\n\n".join(entries) + "\n"
