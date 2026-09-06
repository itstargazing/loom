"""Read and fill AcroForm fields with pypdf."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from pypdf import PdfReader, PdfWriter
from pypdf.generic import BooleanObject, NameObject, TextStringObject


def extract_fields(pdf_bytes: bytes) -> list[dict[str, Any]]:
    """Return structured field metadata for matching."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    if reader.get_fields() is None:
        return []

    fields: list[dict[str, Any]] = []
    for name, field in reader.get_fields().items():
        if name is None:
            continue
        field_type = str(field.get("/FT", "")).replace("/", "").lower() or "unknown"
        value = field.get("/V")
        if value is not None:
            value = str(value)
        options: list[str] = []
        states = field.get("/_States_")
        if isinstance(states, list):
            options = [str(item) for item in states]
        fields.append(
            {
                "name": str(name),
                "type": field_type,
                "value": value,
                "options": options,
            }
        )
    return fields


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
