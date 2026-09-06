"""Assemble reading_compiler_entries into one linear document."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class CompiledPassage:
    id: str
    passage: str
    heading: str | None
    source_url: str
    page_title: str
    dwell_ms: int
    last_seen_at: datetime


def order_passages(
    passages: list[CompiledPassage],
    *,
    order: str = "source",
    entry_ids: list[str] | None = None,
) -> list[CompiledPassage]:
    """Order by explicit id list, source document, or most recent dwell."""
    if entry_ids:
        by_id = {passage.id: passage for passage in passages}
        ordered = [by_id[entry_id] for entry_id in entry_ids if entry_id in by_id]
        remaining = [passage for passage in passages if passage.id not in set(entry_ids)]
        return [*ordered, *remaining]

    if order == "recent":
        return sorted(passages, key=lambda item: item.last_seen_at, reverse=True)

    #  Source order: group by URL, keep groups by earliest sighting, passages
    #  inside a group by original list order (caller should pass page order).
    groups: dict[str, list[CompiledPassage]] = {}
    first_seen: dict[str, datetime] = {}
    for passage in passages:
        key = passage.source_url or passage.page_title or passage.id
        groups.setdefault(key, []).append(passage)
        seen = first_seen.get(key)
        if seen is None or passage.last_seen_at < seen:
            first_seen[key] = passage.last_seen_at

    ordered_keys = sorted(groups.keys(), key=lambda key: first_seen[key])
    return [passage for key in ordered_keys for passage in groups[key]]


def render_markdown(
    passages: list[CompiledPassage],
    *,
    title: str = "Reading compilation",
) -> str:
    lines = [f"# {title}", ""]
    current_source: str | None = None

    for passage in passages:
        source_key = passage.source_url or passage.page_title
        if source_key != current_source:
            current_source = source_key
            heading = passage.page_title or passage.source_url or "Untitled source"
            lines.append(f"## {heading}")
            if passage.source_url:
                lines.append(f"*{passage.source_url}*")
            lines.append("")
        if passage.heading:
            lines.append(f"### {passage.heading}")
            lines.append("")
        lines.append(passage.passage.strip())
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_plain_text(
    passages: list[CompiledPassage],
    *,
    title: str = "Reading compilation",
) -> str:
    lines = [title, "=" * len(title), ""]
    current_source: str | None = None

    for passage in passages:
        source_key = passage.source_url or passage.page_title
        if source_key != current_source:
            current_source = source_key
            heading = passage.page_title or passage.source_url or "Untitled source"
            lines.append(heading)
            lines.append("-" * len(heading))
            if passage.source_url:
                lines.append(passage.source_url)
            lines.append("")
        if passage.heading:
            lines.append(passage.heading)
            lines.append("")
        lines.append(passage.passage.strip())
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def compilation_filename(title: str, format: str) -> str:
    slug = "".join(ch if ch.isalnum() else "-" for ch in title.casefold()).strip("-")
    slug = "-".join(part for part in slug.split("-") if part) or "reading"
    return f"{slug}.{format}"
