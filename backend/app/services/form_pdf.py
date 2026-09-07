"""Read and fill AcroForm fields with pypdf."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from pypdf import PdfReader, PdfWriter
from pypdf.generic import BooleanObject, NameObject, TextStringObject

PASSWORD_PROTECTED = "password-protected"


def normalize_pdf_bytes(payload: bytes) -> bytes:
    """Drop a BOM or junk prefix so the %PDF header is at byte 0."""
    marker = payload.find(b"%PDF")
    if marker <= 0 or marker > 1024:
        return payload
    return payload[marker:]


def looks_like_pdf(payload: bytes) -> bool:
    return normalize_pdf_bytes(payload).lstrip().startswith(b"%PDF")


def _open_reader(pdf_bytes: bytes) -> PdfReader:
    reader = PdfReader(io.BytesIO(normalize_pdf_bytes(pdf_bytes)))
    if getattr(reader, "is_encrypted", False):
        try:
            result = reader.decrypt("")
        except Exception as error:
            raise ValueError(PASSWORD_PROTECTED) from error
        if result == 0:
            raise ValueError(PASSWORD_PROTECTED)
    return reader


def _as_field(name: Any, field: Any) -> dict[str, Any] | None:
    if name is None:
        return None
    field_type = str(field.get("/FT", "") or "").replace("/", "").lower() or "unknown"
    value = field.get("/V")
    if value is not None:
        value = str(value)
    options: list[str] = []
    states = field.get("/_States_")
    if isinstance(states, list):
        options = [str(item) for item in states]
    return {
        "name": str(name),
        "type": field_type,
        "value": value,
        "options": options,
    }


def extract_fields(pdf_bytes: bytes) -> list[dict[str, Any]]:
    """Return structured field metadata for matching.

    Walks AcroForm names and page widget annotations. Flattened or scanned
    PDFs legitimately return an empty list.
    """
    reader = _open_reader(pdf_bytes)
    by_name: dict[str, dict[str, Any]] = {}

    raw = reader.get_fields() or {}
    for name, field in raw.items():
        parsed = _as_field(name, field)
        if parsed:
            by_name[parsed["name"]] = parsed

    for page in reader.pages:
        annots = page.get("/Annots") or []
        for annot in annots:
            try:
                widget = annot.get_object()
            except Exception:
                continue
            subtype = str(widget.get("/Subtype", ""))
            if subtype not in {"/Widget", "Widget"}:
                continue
            target = widget
            name = widget.get("/T")
            if name is None and "/Parent" in widget:
                try:
                    target = widget["/Parent"].get_object()
                    name = target.get("/T")
                except Exception:
                    continue
            parsed = _as_field(name, target)
            if parsed and parsed["name"] not in by_name:
                by_name[parsed["name"]] = parsed

    return list(by_name.values())


def fill_fields(pdf_bytes: bytes, values: dict[str, str]) -> bytes:
    """Write matched values into the PDF; unmatched fields stay as-is.

    Values are written onto the field dictionaries and NeedAppearances is set
    so viewers regenerate the visible text. Appearance streams are not built
    here — they fail on many real-world forms and would guess at fonts.
    """
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    writer.append(reader)

    for page in writer.pages:
        annots = page.get("/Annots")
        if not annots:
            continue
        for annot in annots:
            widget = annot.get_object()
            target = widget
            name = widget.get("/T")
            if name is None and "/Parent" in widget:
                target = widget["/Parent"].get_object()
                name = target.get("/T")
            if name is None:
                continue
            key = str(name)
            if key not in values:
                continue
            target[NameObject("/V")] = TextStringObject(values[key])
            target[NameObject("/DV")] = TextStringObject(values[key])

    if "/AcroForm" in writer._root_object:  # noqa: SLF001
        writer._root_object["/AcroForm"].update(  # noqa: SLF001
            {NameObject("/NeedAppearances"): BooleanObject(True)}
        )

    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def storage_root(base: str) -> Path:
    path = Path(base)
    if not path.is_absolute():
        #  Relative to the backend package root (…/backend).
        path = Path(__file__).resolve().parents[2] / path
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_stored_path(base: str, stored: str) -> Path:
    path = Path(stored)
    if not path.is_absolute():
        path = storage_root(base) / path
    return path


def build_fillable_pdf(field_names: list[str]) -> bytes:
    """Minimal AcroForm PDF used by tests and local seeding."""
    from pypdf.generic import (
        ArrayObject,
        BooleanObject,
        DictionaryObject,
        FloatObject,
        NameObject,
        NumberObject,
        TextStringObject,
    )

    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    annots = ArrayObject()
    fields = ArrayObject()
    y = 720.0
    for name in field_names:
        widget = DictionaryObject()
        widget.update(
            {
                NameObject("/Type"): NameObject("/Annot"),
                NameObject("/Subtype"): NameObject("/Widget"),
                NameObject("/FT"): NameObject("/Tx"),
                NameObject("/T"): TextStringObject(name),
                NameObject("/Ff"): NumberObject(0),
                NameObject("/Rect"): ArrayObject(
                    [
                        FloatObject(120),
                        FloatObject(y),
                        FloatObject(480),
                        FloatObject(y + 20),
                    ]
                ),
                NameObject("/F"): NumberObject(4),
                NameObject("/DA"): TextStringObject("/Helv 12 Tf 0 g"),
                NameObject("/V"): TextStringObject(""),
            }
        )
        ref = writer._add_object(widget)  # noqa: SLF001
        widget[NameObject("/P")] = page.indirect_reference
        annots.append(ref)
        fields.append(ref)
        y -= 28
    page[NameObject("/Annots")] = annots
    writer._root_object[NameObject("/AcroForm")] = DictionaryObject(  # noqa: SLF001
        {
            NameObject("/Fields"): fields,
            NameObject("/NeedAppearances"): BooleanObject(True),
            NameObject("/DA"): TextStringObject("/Helv 0 Tf 0 g"),
        }
    )
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()
