from app.services.citation_format import (
    CitationMeta,
    bibliography_filename,
    format_apa,
    format_mla,
    format_styles,
    render_bibliography,
    site_name,
)


META = CitationMeta(
    author="Jane Hansen",
    work_title="Global temperature trends",
    publisher="Nature",
    published_date="2024-03-12",
    source_url="https://www.nature.com/articles/s41586-024-00001",
    page_title="Global temperature trends",
)


def test_site_name_strips_www():
    assert site_name("https://www.nature.com/articles/x") == "nature.com"


def test_apa_inverts_a_personal_name_and_keeps_the_year():
    rendered = format_apa(META)
    assert rendered.startswith("Hansen, J. (2024). Global temperature trends.")
    assert "Nature." in rendered
    assert rendered.endswith("https://www.nature.com/articles/s41586-024-00001")


def test_mla_quotes_the_title_and_keeps_the_author_as_written():
    rendered = format_mla(META)
    assert rendered.startswith("Jane Hansen.")
    assert '"Global temperature trends."' in rendered
    assert "Nature," in rendered
    assert "2024," in rendered


def test_missing_author_does_not_invent_one():
    meta = CitationMeta(
        work_title="Untitled memo",
        source_url="https://example.edu/memo",
        page_title="Memo",
    )
    apa = format_apa(meta)
    mla = format_mla(meta)
    assert apa.startswith("Untitled memo. (n.d.).")
    assert '"Untitled memo."' in mla
    assert "None" not in apa
    assert "None" not in mla


def test_format_styles_always_returns_apa_and_mla():
    styles = format_styles(META)
    assert set(styles) == {"apa", "mla"}
    assert styles["apa"] == format_apa(META)
    assert styles["mla"] == format_mla(META)


def test_already_inverted_author_is_left_alone():
    meta = CitationMeta(author="Hansen, J.", work_title="Paper", published_date="2020")
    assert format_apa(meta).startswith("Hansen, J. (2020).")


def test_bibliography_filename_slugs_the_collection():
    assert bibliography_filename("Thesis reading", "apa", "txt") == "thesis-reading-apa.txt"
    assert bibliography_filename(None, "mla", "md") == "citations-mla.md"


def test_markdown_bibliography_is_numbered():
    body = render_bibliography(
        ["First cite.", "Second cite."],
        style="apa",
        format="md",
        heading="Thesis reading",
    )
    assert body.startswith("# Thesis reading")
    assert "1. First cite." in body
    assert "2. Second cite." in body


def test_plain_bibliography_is_blank_line_separated():
    body = render_bibliography(
        ["First cite.", "Second cite."],
        style="apa",
        format="txt",
        heading="ignored",
    )
    assert body == "First cite.\n\nSecond cite.\n"
