"""
File: rag/ingest.py

OWNER: Partner 1 — RAG & AI Engineer

PURPOSE:
Extract and normalize academic content from the official Birzeit University
PDF documents in data/university_docs/, one PageRecord per PDF page, without
ever losing the (document, page) metadata that citations depend on.

DEPENDENCIES:
- PyMuPDF (`import fitz`) — default extractor (PDF_EXTRACTOR=pymupdf)
- pypdf — fallback extractor (PDF_EXTRACTOR=pypdf)
- pathlib, json, unicodedata, re, logging (stdlib)
- rag.schemas (PageRecord, IngestionError)
- config (get_settings) — only inside functions / the CLI

IMPORTANT: import fitz / pypdf INSIDE the functions that use them, never at
module level, so tests and the mock UI can import this module on machines
where those libraries are not installed yet.

EXPECTED OUTPUT:
list[PageRecord] where every record has document (filename only), 1-based
page, normalized text, doc_title and doc_version from manifest.json.

FINDINGS FROM THE ACTUAL PDFs (verified while preparing this repo):
- Both PDFs have a text layer on every page (no OCR needed). Full pypdf
  extraction of BZU.pdf (625 pages) took about 15 s.
- pypdf REVERSES some numbers in right-to-left table rows: study plan page 3,
  ENCS5200 prerequisite "انهاء 95 ساعة" comes out as "انهاء 59 ساعة", and
  "COMP23xx" comes out as "xx3COMP2". Visually confirmed: the true value is 95.
- pdftotext/poppler breaks the lam-alef ligature ("العلامات" -> "العالمات");
  pypdf does not.
- PyMuPDF was NOT tested (it was not installable in the preparation
  environment). Run compare_extractors() in your first 10 minutes.

CLI (run from the repository root):
    python -m rag.ingest --compare            # extractor comparison on golden pages
    python -m rag.ingest --stats              # page/char counts per document
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import unicodedata
from pathlib import Path

from rag.schemas import IngestionError, PageRecord

logger = logging.getLogger(__name__)

# Golden checks: (document, 1-based page, substring that MUST appear in the
# extracted, normalized text). Use them to choose PDF_EXTRACTOR and as a
# regression test (tests/test_ingest.py). Each was verified against the PDF.
GOLDEN_EXTRACTION_CHECKS: list[tuple[str, int, str]] = [
    ("1_Computer_Engineering_4_YEAR_PLAN_APRIL_25_2026.pdf", 1, "138"),
    ("1_Computer_Engineering_4_YEAR_PLAN_APRIL_25_2026.pdf", 1, "لا"),
    ("1_Computer_Engineering_4_YEAR_PLAN_APRIL_25_2026.pdf", 3, "95"),
    ("1_Computer_Engineering_4_YEAR_PLAN_APRIL_25_2026.pdf", 2, "COMP23xx"),
    ("1_Computer_Engineering_4_YEAR_PLAN_APRIL_25_2026.pdf", 3, "ENCS5300"),
    ("BZU.pdf", 570, "158"),
    ("BZU.pdf", 2, "registrar@birzeit.edu"),
]

# Characters that carry no meaning for retrieval and break matching.
_BIDI_AND_ZERO_WIDTH = re.compile(r"[​-‏‪-‮⁦-⁩﻿]")
_ARABIC_TATWEEL = "ـ"


def load_manifest(docs_dir: Path) -> dict[str, dict[str, object]]:
    """Load data/university_docs/manifest.json.

    Args:
        docs_dir: Folder containing the PDFs and manifest.json.

    Returns:
        Mapping filename -> metadata dict (doc_title, doc_version, language,
        scope, priority). Returns {} if manifest.json is absent.

    Raises:
        IngestionError: If manifest.json exists but is not valid JSON or has
            no "documents" object.
    """
    # TODO(PARTNER 1):
    # 1. Build path = docs_dir / "manifest.json".
    # 2. If it does not exist: logger.warning(...) and return {} (ingestion
    #    still works; records just get empty doc_title/doc_version).
    # 3. Read with encoding="utf-8" and json.loads; on json.JSONDecodeError
    #    raise IngestionError("manifest.json is invalid JSON: <line/col>").
    # 4. Require data["documents"] to be a dict; otherwise IngestionError.
    # 5. Return data["documents"].
    #
    # EDGE CASES:
    # - Manifest lists a file that is not on disk -> logger.warning, ignore.
    # - PDF on disk missing from the manifest -> logger.warning; ingest it
    #   anyway with doc_title = filename stem, doc_version = "".
    #
    # ACCEPTANCE CRITERIA:
    # load_manifest(settings.docs_dir)["BZU.pdf"]["doc_version"] == "2024-2025"
    raise NotImplementedError("Partner 1 must implement load_manifest().")


def discover_pdfs(docs_dir: Path) -> list[Path]:
    """Find every PDF to ingest.

    Args:
        docs_dir: Folder to scan (non-recursive).

    Returns:
        Sorted list of PDF paths (sorted by filename so chunk ids and index
        order are deterministic across machines).

    Raises:
        IngestionError: If docs_dir does not exist, is not a directory, or
            contains no PDF files.
    """
    # TODO(PARTNER 1):
    # 1. Validate docs_dir exists and is a directory -> IngestionError with
    #    the absolute path in the message.
    # 2. Collect files whose suffix.lower() == ".pdf" (so "PLAN.PDF" counts).
    #    Use docs_dir.iterdir(), not glob("*.pdf"), because glob is
    #    case-sensitive on Linux.
    # 3. Skip hidden/temp files: names starting with "." or "~$".
    # 4. Sort by p.name.
    # 5. If the list is empty -> IngestionError("No PDF files found in ...").
    # 6. logger.info the count and filenames.
    #
    # EDGE CASES:
    # - Non-PDF files in the folder (README.md, manifest.json) -> ignored.
    # - Sub-folders -> ignored (keep it simple; document this in README).
    #
    # ACCEPTANCE CRITERIA:
    # Returns exactly the two shipped PDFs, in alphabetical order.
    raise NotImplementedError("Partner 1 must implement discover_pdfs().")


def normalize_text(text: str) -> str:
    """Normalize extracted PDF text for storage, display, and embedding.

    The result is what the LLM sees and what the user sees in excerpts, so it
    must stay readable. Do NOT do aggressive normalization (e.g. alef
    unification) here — that belongs only in keyword matching
    (rag/retriever.py::normalize_for_matching).

    Args:
        text: Raw page text from the extractor (may be "").

    Returns:
        Cleaned text. Line breaks are PRESERVED because each table row of the
        study plan is one line ("COMP433 الهندسة البرمجية COMP3330") and the
        chunker relies on lines to keep course codes next to their
        prerequisites.
    """
    # TODO(PARTNER 1):
    # 1. If text is empty or only whitespace, return "".
    # 2. unicodedata.normalize("NFKC", text): folds Arabic presentation forms
    #    (U+FB50–U+FDFF, U+FE70–U+FEFF), which some PDFs emit, into normal
    #    Arabic letters. Verify on one page that Arabic is still readable.
    # 3. Remove bidi control and zero-width characters with
    #    _BIDI_AND_ZERO_WIDTH.sub("", text).
    # 4. Remove tatweel (_ARABIC_TATWEEL), e.g. "دلـيل" -> "دليل".
    # 5. Replace bullet glyphs ("▪", "•", "", "") with "- ".
    # 6. Replace non-breaking spaces ( ) and tabs with a normal space.
    # 7. Collapse runs of spaces inside each line to one space; strip each
    #    line; KEEP "\n" between lines.
    # 8. Collapse 3+ consecutive blank lines to one blank line.
    # 9. Remove dot leaders from the table of contents ("....... 570") by
    #    collapsing runs of 4+ dots into " ... ".
    # 10. Do NOT translate Arabic-Indic digits (٠-٩) here; keep the source
    #     text faithful. (Matching handles them.)
    #
    # EDGE CASES:
    # - Mixed Arabic/English on one line -> unchanged order, only cleaned.
    # - Course codes "ENCS 5300" vs "ENCS5300" -> leave as-is here.
    # - Text that is only page-number digits -> returns those digits.
    #
    # ACCEPTANCE CRITERIA:
    # normalize_text("دلـيل‏  جامعة   بيرزيت") == "دليل جامعة بيرزيت"
    # normalize_text("a\n\n\n\n\nb") == "a\n\nb"
    raise NotImplementedError("Partner 1 must implement normalize_text().")


def extract_pdf(
    file_path: str | Path,
    extractor: str = "pymupdf",
    manifest_entry: dict[str, object] | None = None,
) -> list[PageRecord]:
    """Extract text from one PDF while preserving document and page metadata.

    Args:
        file_path: Path to the source PDF.
        extractor: "pymupdf" or "pypdf" (from settings.pdf_extractor).
        manifest_entry: This file's entry from manifest.json, or None.

    Returns:
        One PageRecord per page, in page order, INCLUDING pages whose text is
        empty (so page numbering never shifts and missing text is visible).

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the path is empty, not a .pdf, or extractor is unknown.
        IngestionError: If the PDF is corrupted, encrypted, or has zero pages.
    """
    # TODO(PARTNER 1):
    # 1. Validate file_path is not empty -> ValueError.
    # 2. path = Path(file_path); if not path.is_file() -> FileNotFoundError.
    # 3. If path.suffix.lower() != ".pdf" -> ValueError.
    # 4. If extractor not in ("pymupdf", "pypdf") -> ValueError.
    # 5. PyMuPDF branch:
    #      import fitz
    #      try: doc = fitz.open(path)
    #      except Exception as exc: raise IngestionError(f"Cannot open {path.name}: {exc}") from exc
    #      if doc.needs_pass: raise IngestionError(f"{path.name} is password-protected")
    #      for i, page in enumerate(doc): raw = page.get_text("text", sort=True)
    #    Try sort=True AND sort=False on study-plan page 3 and keep whichever
    #    preserves "95" and "COMP23xx" (see GOLDEN_EXTRACTION_CHECKS).
    #    Close the document in a finally block.
    # 6. pypdf branch:
    #      from pypdf import PdfReader
    #      reader = PdfReader(str(path)); if reader.is_encrypted -> IngestionError
    #      raw = page.extract_text() or ""
    #    pypdf prints harmless warnings for some fonts; silence them with
    #    logging.getLogger("pypdf").setLevel(logging.ERROR).
    # 7. text = normalize_text(raw).
    # 8. Remove running headers/footers: compute lines that appear on > 60%
    #    of pages of THIS document (e.g. "ENCO", "برنامج بكالوريوس هندسة الحاسوب")
    #    and strip them from each page. Do this after all pages are read.
    #    Keep a bare page-number line only if it is the sole content.
    # 9. Build PageRecord(document=path.name, page=i + 1, text=text,
    #    doc_title=str(entry.get("doc_title", path.stem)),
    #    doc_version=str(entry.get("doc_version", ""))).
    # 10. Count pages whose text has < 20 non-space characters. If any,
    #     logger.warning with their page numbers ("possible scanned pages").
    #     If ALL pages are empty -> IngestionError("no extractable text; OCR
    #     required") — do not silently produce an empty index.
    # 11. If the document has 0 pages -> IngestionError.
    #
    # OPTIONAL (Priority 2, only after the core pipeline works):
    # - PyMuPDF `page.find_tables()` on study-plan pages 1–6 to turn table rows
    #   into explicit lines such as
    #   "Course: ENCS5300 | Name: مشروع التخرج | Prerequisite: ENCS4300, ENCS5200".
    #   Measure the effect with tests/evaluate.py before keeping it.
    #
    # EDGE CASES:
    # - Empty PDF (0 pages)            -> IngestionError.
    # - Corrupted PDF                  -> IngestionError naming the file.
    # - Scanned pages                  -> kept with text="", warning logged.
    # - Mixed Arabic and English       -> preserved (normalize_text).
    # - Tables / irregular layouts     -> one row per line; verify golden checks.
    # - Missing file                   -> FileNotFoundError.
    # - Password-protected PDF         -> IngestionError.
    #
    # ACCEPTANCE CRITERIA:
    # Every record keeps its original filename and 1-based page number, and
    # every GOLDEN_EXTRACTION_CHECKS entry passes for the chosen extractor.
    raise NotImplementedError("Partner 1 must implement extract_pdf().")


def ingest_directory(docs_dir: Path, extractor: str = "pymupdf") -> list[PageRecord]:
    """Extract every PDF in docs_dir.

    Args:
        docs_dir: Folder with PDFs and manifest.json.
        extractor: "pymupdf" or "pypdf".

    Returns:
        All PageRecords from all documents, ordered by (document, page).

    Raises:
        IngestionError: If no document could be ingested at all.
    """
    # TODO(PARTNER 1):
    # 1. manifest = load_manifest(docs_dir)
    # 2. for path in discover_pdfs(docs_dir):
    #        try: records.extend(extract_pdf(path, extractor, manifest.get(path.name)))
    #        except IngestionError as exc: logger.error(...); failed.append(path.name)
    #    One broken PDF must NOT stop the others (avoid silent data loss by
    #    logging it loudly instead).
    # 3. If records is empty -> IngestionError listing `failed`.
    # 4. logger.info a summary: documents, pages, empty pages, total chars.
    #
    # ACCEPTANCE CRITERIA:
    # With the two shipped PDFs: 659 records (625 + 34).
    raise NotImplementedError("Partner 1 must implement ingest_directory().")


def compare_extractors(docs_dir: Path) -> list[dict[str, object]]:
    """Run GOLDEN_EXTRACTION_CHECKS with every available extractor.

    Use this in minutes 0–15 to pick PDF_EXTRACTOR with evidence.

    Returns:
        One row per (extractor, check): {"extractor", "document", "page",
        "expected", "passed"}. Extractors that are not installed are
        reported with passed=None instead of crashing.
    """
    # TODO(PARTNER 1):
    # 1. For extractor in ("pymupdf", "pypdf"):
    #      try extract_pdf for each document referenced by the checks
    #      (cache per document; BZU.pdf takes ~15 s with pypdf).
    #      except ImportError -> record passed=None for that extractor.
    # 2. For each check, passed = expected in records[page - 1].text
    # 3. Return the rows; the CLI prints them as a table.
    # 4. Choose the extractor with the most passes; set PDF_EXTRACTOR in .env
    #    and tell Partner 2 so .env.example gets the same default.
    #    If BOTH fail the "95" check, add a targeted fix in extract_pdf for
    #    reversed digit runs in RTL lines, or use find_tables() for pages 1–6
    #    of the study plan, and record the decision in docs/EVALUATION.md.
    raise NotImplementedError("Partner 1 must implement compare_extractors().")


def _main() -> None:
    """Small CLI for Partner 1's diagnostics (implemented infrastructure)."""
    from config import get_settings

    parser = argparse.ArgumentParser(description="PDF ingestion diagnostics.")
    parser.add_argument("--compare", action="store_true", help="compare extractors on golden pages")
    parser.add_argument("--stats", action="store_true", help="print page/char counts per document")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    settings = get_settings()

    if args.compare:
        for row in compare_extractors(settings.docs_dir):
            print(json.dumps(row, ensure_ascii=False))
    elif args.stats:
        records = ingest_directory(settings.docs_dir, settings.pdf_extractor)
        by_doc: dict[str, list[int]] = {}
        for r in records:
            by_doc.setdefault(r.document, []).append(len(r.text))
        for doc, lengths in by_doc.items():
            empty = sum(1 for n in lengths if n < 20)
            print(f"{doc}: pages={len(lengths)} chars={sum(lengths)} near_empty={empty}")
    else:
        parser.print_help()


if __name__ == "__main__":
    _main()
