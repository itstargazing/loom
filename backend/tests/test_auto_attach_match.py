"""Pure tests for upload-field → recent-document matching."""

from uuid import uuid4

from app.services.auto_attach_match import (
    infer_doc_type,
    rank_documents,
    score_document,
    summarize_text,
)


def test_resume_label_matches_resume_document():
    confidence, reason = score_document(
        "Upload your resume PDF",
        filename="jane-doe-resume.pdf",
        doc_type="resume",
        summary="Jane Doe software engineer experience",
        accept="application/pdf",
        mime_type="application/pdf",
    )
    assert confidence >= 0.75
    assert "resume" in reason.casefold() or "filename" in reason.casefold()


def test_resume_beats_generic_pdf_when_field_mentions_both():
    docs = [
        (
            uuid4(),
            "club-signup.pdf",
            "pdf",
            "https://example.com/club.pdf",
            "Fillable PDF",
            "user/club.pdf",
            "application/pdf",
        ),
        (
            uuid4(),
            "jane-doe-resume.pdf",
            "resume",
            "https://files.example.com/resume.pdf",
            "Curriculum vitae",
            None,
            "application/pdf",
        ),
    ]
    ranked = rank_documents(
        label_text="Upload your resume (PDF)",
        surrounding_text="Attach a recent CV or resume.",
        field_name=None,
        accept="application/pdf",
        documents=docs,
    )
    assert ranked
    assert ranked[0].filename == "jane-doe-resume.pdf"


def test_id_field_prefers_id_scan():
    docs = [
        (
            uuid4(),
            "passport-scan.png",
            "id_scan",
            "https://files.example/passport.png",
            "Government ID photo",
            None,
            "image/png",
        ),
        (
            uuid4(),
            "resume.pdf",
            "resume",
            "https://files.example/resume.pdf",
            "Curriculum vitae",
            "user/doc.pdf",
            "application/pdf",
        ),
    ]
    ranked = rank_documents(
        label_text="Government photo ID",
        surrounding_text="Please upload a scan of your passport or driver's license",
        field_name="id_upload",
        accept="image/*",
        documents=docs,
        min_confidence=0.7,
    )
    assert ranked
    assert ranked[0].doc_type == "id_scan"


def test_accept_filter_excludes_images_for_pdf_field():
    confidence, _reason = score_document(
        "Resume",
        filename="photo.png",
        doc_type="image",
        summary="headshot",
        accept="application/pdf",
        mime_type="image/png",
    )
    assert confidence == 0.0


def test_infer_doc_type_from_filename():
    assert infer_doc_type("my_resume_2024.pdf", "", "") == "resume"
    assert infer_doc_type("passport.jpg", "ID", "") == "id_scan"


def test_summarize_truncates():
    text = "word " * 200
    summary = summarize_text(text, limit=40)
    assert len(summary) <= 40
    assert summary.endswith("…")
