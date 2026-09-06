"""Minimal text PDF writer — no third-party PDF dependency."""

from __future__ import annotations


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _wrap(text: str, width: int = 90) -> list[str]:
    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        if not paragraph.strip():
            lines.append("")
            continue
        words = paragraph.split()
        current: list[str] = []
        length = 0
        for word in words:
            extra = len(word) + (1 if current else 0)
            if length + extra > width and current:
                lines.append(" ".join(current))
                current = [word]
                length = len(word)
            else:
                current.append(word)
                length += extra
        if current:
            lines.append(" ".join(current))
    return lines


def render_pdf(title: str, body: str) -> bytes:
    """Build a simple multi-page Helvetica PDF from plain text."""
    content_lines = _wrap(title, 80) + [""] + _wrap(body, 90)
    pages: list[list[str]] = []
    page: list[str] = []
    for line in content_lines:
        page.append(line)
        if len(page) >= 54:
            pages.append(page)
            page = []
    if page or not pages:
        pages.append(page)

    objects: list[bytes] = []
    # 1: catalog, 2: pages, then per page: page dict + content stream

    page_object_ids: list[int] = []
    next_id = 3

    content_objects: list[tuple[int, bytes]] = []
    page_dicts: list[tuple[int, int]] = []  # (page_id, content_id)

    for page_lines in pages:
        content_id = next_id
        page_id = next_id + 1
        next_id += 2
        page_object_ids.append(page_id)

        stream_lines = ["BT", "/F1 11 Tf", "50 780 Td", "14 TL"]
        first = True
        for line in page_lines:
            if first:
                stream_lines.append(f"({_escape(line)}) Tj")
                first = False
            else:
                stream_lines.append("T*")
                stream_lines.append(f"({_escape(line)}) Tj")
        stream_lines.append("ET")
        stream = "\n".join(stream_lines).encode("latin-1", errors="replace")
        content_objects.append(
            (
                content_id,
                b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
            )
        )
        page_dicts.append((page_id, content_id))

    font_id = next_id
    next_id += 1

    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    kids = " ".join(f"{page_id} 0 R" for page_id in page_object_ids)
    objects.append(
        (
            f"2 0 obj\n<< /Type /Pages /Kids [{kids}] /Count {len(page_object_ids)} >>\nendobj\n"
        ).encode()
    )

    # Placeholder slots so object numbers stay sequential when we emit.
    by_id: dict[int, bytes] = {1: objects[0], 2: objects[1]}
    for content_id, body_bytes in content_objects:
        by_id[content_id] = (
            f"{content_id} 0 obj\n".encode() + body_bytes + b"\nendobj\n"
        )
    for page_id, content_id in page_dicts:
        by_id[page_id] = (
            f"{page_id} 0 obj\n"
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Contents {content_id} 0 R /Resources << /Font << /F1 {font_id} 0 R >> >> >>\n"
            f"endobj\n"
        ).encode()
    by_id[font_id] = (
        f"{font_id} 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    ).encode()

    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for object_id in range(1, font_id + 1):
        offsets.append(len(output))
        output.extend(by_id[object_id])

    xref_pos = len(output)
    output.extend(f"xref\n0 {font_id + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for object_id in range(1, font_id + 1):
        output.extend(f"{offsets[object_id]:010d} 00000 n \n".encode())
    output.extend(
        (
            f"trailer\n<< /Size {font_id + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_pos}\n%%EOF\n"
        ).encode()
    )
    return bytes(output)
