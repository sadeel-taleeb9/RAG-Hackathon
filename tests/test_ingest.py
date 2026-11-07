"""
File: tests/test_ingest.py

OWNER: Partner 1 — RAG & AI Engineer

PURPOSE:
Unit and data tests for rag/ingest.py: path validation, text normalization,
page metadata preservation, and GOLDEN checks against the real PDFs (values
verified by reading the documents, including the RTL number-reversal trap on
study-plan page 3).

Run:  pytest tests/test_ingest.py -v
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from rag import ingest
from rag.schemas import IngestionError, PageRecord

pending = pytest.mark.xfail(
    raises=NotImplementedError, reason="Pending Partner 1 implementation", strict=False
)

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "data" / "university_docs"
PLAN = DOCS / "1_Computer_Engineering_4_YEAR_PLAN_APRIL_25_2026.pdf"
CATALOG = DOCS / "BZU.pdf"

HAS_PYMUPDF = importlib.util.find_spec("fitz") is not None
HAS_PYPDF = importlib.util.find_spec("pypdf") is not None
AVAILABLE_EXTRACTORS = [e for e, ok in (("pymupdf", HAS_PYMUPDF), ("pypdf", HAS_PYPDF)) if ok]


def _configured_extractor() -> str:
    from config import get_settings

    return get_settings().pdf_extractor


# --------------------------------------------------------------------------
# normalize_text
# --------------------------------------------------------------------------
@pending
def test_normalize_removes_tatweel_bidi_and_extra_spaces():
    assert ingest.normalize_text("دلـيل‏  جامعة   بيرزيت") == "دليل جامعة بيرزيت"


@pending
def test_normalize_preserves_line_breaks_but_collapses_blank_runs():
    assert ingest.normalize_text("a\n\n\n\n\nb") == "a\n\nb"
    assert ingest.normalize_text("COMP433 الهندسة البرمجية COMP3330\nCOMP3330 x") == (
        "COMP433 الهندسة البرمجية COMP3330\nCOMP3330 x"
    )


@pending
def test_normalize_empty_returns_empty():
    assert ingest.normalize_text("") == ""
    assert ingest.normalize_text("   \n\t ") == ""


@pending
def test_normalize_folds_arabic_presentation_forms():
    # U+FEDF U+FEE0 ... are presentation forms some PDFs emit; NFKC must fold them.
    presentation = "ﻟﺎ"  # "لا"-like presentation-form sequence
    out = ingest.normalize_text(presentation)
    assert all(not (0xFB50 <= ord(ch) <= 0xFEFF) for ch in out)


# --------------------------------------------------------------------------
# discover_pdfs / load_manifest
# --------------------------------------------------------------------------
@pending
def test_discover_pdfs_finds_shipped_documents_sorted():
    names = [p.name for p in ingest.discover_pdfs(DOCS)]
    assert names == sorted(names)
    assert PLAN.name in names and CATALOG.name in names


@pending
def test_discover_pdfs_missing_dir_raises(tmp_path):
    with pytest.raises(IngestionError):
        ingest.discover_pdfs(tmp_path / "does_not_exist")


@pending
def test_discover_pdfs_empty_dir_raises(tmp_path):
    (tmp_path / "notes.txt").write_text("not a pdf", encoding="utf-8")
    with pytest.raises(IngestionError):
        ingest.discover_pdfs(tmp_path)


@pending
def test_load_manifest_reads_versions():
    manifest = ingest.load_manifest(DOCS)
    assert manifest["BZU.pdf"]["doc_version"] == "2024-2025"
    assert manifest[PLAN.name]["doc_version"] == "2026-04-25"


@pending
def test_load_manifest_missing_file_returns_empty(tmp_path):
    assert ingest.load_manifest(tmp_path) == {}


# --------------------------------------------------------------------------
# extract_pdf — validation
# --------------------------------------------------------------------------
@pending
def test_extract_pdf_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        ingest.extract_pdf(DOCS / "missing.pdf")


@pending
def test_extract_pdf_rejects_non_pdf(tmp_path):
    f = tmp_path / "notes.txt"
    f.write_text("hello", encoding="utf-8")
    with pytest.raises(ValueError):
        ingest.extract_pdf(f)


@pending
def test_extract_pdf_rejects_empty_path():
    with pytest.raises(ValueError):
        ingest.extract_pdf("")


@pending
def test_extract_pdf_corrupted_file_raises(tmp_path):
    f = tmp_path / "broken.pdf"
    f.write_bytes(b"%PDF-1.4 this is not really a pdf")
    with pytest.raises(IngestionError):
        ingest.extract_pdf(f, extractor=_configured_extractor())


# --------------------------------------------------------------------------
# extract_pdf — metadata on a generated PDF (needs PyMuPDF to create it)
# --------------------------------------------------------------------------
@pending
def test_extract_pdf_keeps_page_numbers_including_empty_pages(tmp_path):
    fitz = pytest.importorskip("fitz")
    path = tmp_path / "sample.pdf"
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "Page one COMP433")
    doc.new_page()  # intentionally empty page
    doc.new_page().insert_text((72, 72), "Page three ENCS5300")
    doc.save(path)
    doc.close()

    records = ingest.extract_pdf(path, extractor="pymupdf")
    assert [r.page for r in records] == [1, 2, 3]
    assert all(r.document == "sample.pdf" for r in records)
    assert records[1].text == ""
    assert "ENCS5300" in records[2].text


# --------------------------------------------------------------------------
# Real documents (slow: BZU.pdf has 625 pages)
# --------------------------------------------------------------------------
needs_docs = pytest.mark.skipif(
    not (PLAN.exists() and CATALOG.exists()), reason="University PDFs not present"
)
needs_extractor = pytest.mark.skipif(not AVAILABLE_EXTRACTORS, reason="No PDF library installed")


@pending
@needs_docs
@needs_extractor
def test_study_plan_metadata():
    records = ingest.extract_pdf(PLAN, extractor=_configured_extractor())
    assert len(records) == 34
    assert [r.page for r in records] == list(range(1, 35))
    assert all(isinstance(r, PageRecord) and r.document == PLAN.name for r in records)


_GOLDEN_CACHE: dict[str, list[PageRecord]] = {}


@pending
@needs_docs
@needs_extractor
@pytest.mark.parametrize("document,page,expected", ingest.GOLDEN_EXTRACTION_CHECKS)
def test_golden_extraction_checks(document, page, expected):
    """These values were verified against the PDFs. A failure here means the
    chosen PDF_EXTRACTOR damages the data (e.g. reverses '95' into '59')."""
    if document not in _GOLDEN_CACHE:
        _GOLDEN_CACHE[document] = ingest.extract_pdf(DOCS / document, extractor=_configured_extractor())
    record = _GOLDEN_CACHE[document][page - 1]
    assert record.page == page
    assert expected in record.text, f"{expected!r} not found on {document} page {page}"
