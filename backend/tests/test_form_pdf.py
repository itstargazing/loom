"""Read and fill AcroForm fields without a live database."""

from app.services.form_pdf import build_fillable_pdf, extract_fields, fill_fields


def test_build_extract_and_fill_roundtrip():
    original = build_fillable_pdf(["full_name", "email", "mystery"])
    fields = extract_fields(original)
    names = {field["name"] for field in fields}
    assert {"full_name", "email", "mystery"} <= names

    filled = fill_fields(original, {"full_name": "Ada Lovelace", "email": "ada@example.com"})
    after = extract_fields(filled)
    values = {field["name"]: field["value"] for field in after}
    assert "Ada Lovelace" in str(values.get("full_name"))
    assert "ada@example.com" in str(values.get("email"))
    #  Unmatched fields stay empty rather than receiving a guess.
    mystery = str(values.get("mystery") or "")
    assert "Ada" not in mystery
    assert "ada@example.com" not in mystery


def test_extract_empty_when_no_form():
    from pypdf import PdfWriter
    import io

    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    assert extract_fields(buf.getvalue()) == []


def test_normalize_pdf_strips_junk_prefix():
    from app.services.form_pdf import looks_like_pdf, normalize_pdf_bytes

    body = b"%PDF-1.4\n"
    prefixed = b"HTTP/1.1 200 OK\r\n\r\n" + body
    assert normalize_pdf_bytes(prefixed).startswith(b"%PDF")
    assert looks_like_pdf(prefixed)
    assert not looks_like_pdf(b"not a pdf")
