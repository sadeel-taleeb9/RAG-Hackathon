"""
File: rag/chunker.py

OWNER: Partner 1 — RAG & AI Engineer

PURPOSE:
Split PageRecords into retrievable Chunks that (a) never span two pages,
(b) never cut a course code away from its name/prerequisite, and (c) carry a
short contextual header so a chunk is understandable on its own.

DEPENDENCIES:
- re, logging (stdlib)
- rag.schemas (PageRecord, Chunk)

EXPECTED OUTPUT:
list[Chunk] with stable chunk_ids "<document>::p<page>::c<index>".

WHY THIS STRATEGY (judges ask this — question 1 of the judges' question bank):
- Page-bounded chunks make every citation exact (one chunk = one page).
- Line-aware packing keeps each study-plan table row intact, so
  "ENCS5300 مشروع التخرج ENCS4300, ENCS5200" stays in one chunk and the
  course -> prerequisite relationship survives.
- Character-based sizes (not tokens) avoid loading a tokenizer and behave the
  same for Arabic and English. ~900 chars is roughly 150–250 words: large
  enough for a whole regulation article or 10–15 table rows, small enough to
  keep Top-5 context under ~5k characters.
- Overlap (~150 chars, whole lines only) protects sentences that straddle a
  chunk boundary without duplicating whole rows many times.
"""

from __future__ import annotations

import logging
import re

from rag.schemas import Chunk, PageRecord

logger = logging.getLogger(__name__)

# Course codes in these documents: 4 uppercase letters + 3-5 digits, sometimes
# with a placeholder suffix ("COMP23xx"). Examples: ENCS5300, COMP433, MATH1311.
COURSE_CODE_PATTERN = re.compile(r"\b[A-Z]{4}\s?\d{2,5}[a-z]{0,2}\b")

MIN_CHUNK_CHARS = 40  # Shorter chunks are noise ("570", "ENCO") — merge or drop.


def build_chunk_header(record: PageRecord) -> str:
    """Return the contextual header prepended to every chunk of a page.

    Format (one line):
        "[<doc_title> | <doc_version> | page <page>]"

    Why: a chunk such as "ENCS5300 مشروع التخرج ENCS4300, ENCS5200" does not
    say which program or document version it comes from. The header gives
    the embedding model and the LLM that context, and lets the generator
    prefer the newer document when two chunks disagree.

    Args:
        record: The page the chunk comes from.

    Returns:
        Header string WITHOUT a trailing newline.
    """
    # TODO(PARTNER 1):
    # 1. title = record.doc_title or record.document
    # 2. Include doc_version only if non-empty.
    # 3. Return e.g. "[Computer Engineering B.Sc. ... | 2026-04-25 | page 3]".
    # 4. Keep it under ~120 chars; truncate the title with "…" if needed.
    #
    # ACCEPTANCE CRITERIA:
    # build_chunk_header(PageRecord("a.pdf", 3, "x", "Plan", "2026")) == "[Plan | 2026 | page 3]"
    raise NotImplementedError("Partner 1 must implement build_chunk_header().")


def split_page_into_chunks(
    record: PageRecord,
    chunk_size: int,
    chunk_overlap: int,
) -> list[Chunk]:
    """Split ONE page into chunks.

    Args:
        record: Page to split (text already normalized by ingest.py).
        chunk_size: Target maximum characters per chunk BODY (header excluded).
        chunk_overlap: Characters of trailing context (whole lines) repeated at
            the start of the next chunk.

    Returns:
        Chunks for this page, chunk index starting at 0. [] for empty pages.

    Raises:
        ValueError: If chunk_size <= 0, chunk_overlap < 0, or
            chunk_overlap >= chunk_size.
    """
    # TODO(PARTNER 1):
    # 1. Validate the size arguments (ValueError with the bad values).
    # 2. If record.text.strip() is empty -> return [] (logged by ingest.py).
    # 3. lines = [ln for ln in record.text.split("\n")] ; treat blank lines as
    #    paragraph separators (keep them as "" entries).
    # 4. Greedy packing: append whole lines to the current buffer while
    #    len(buffer) + len(line) + 1 <= chunk_size.
    # 5. A single line longer than chunk_size (long Arabic paragraph):
    #    split it at sentence boundaries — ".", "؟", "?", "!", "؛", "،" followed
    #    by a space — and, only as a last resort, at the last space before
    #    chunk_size. NEVER split inside a token matched by COURSE_CODE_PATTERN.
    # 6. When a chunk is emitted, start the next buffer with the LAST whole
    #    lines of the previous chunk whose total length <= chunk_overlap
    #    (overlap is line-based so table rows are never cut in half).
    # 7. Prefer to close a chunk at a blank line or before a heading-like line
    #    (e.g. starts with "المادة", "Article", a numbered item "3.", or a
    #    course code at line start) when the buffer is already >= 60% full.
    #    This keeps one regulation article / one course description together.
    # 8. Merge a final chunk shorter than MIN_CHUNK_CHARS into the previous
    #    chunk of the same page (if any); drop it if it is the only chunk and
    #    is just a page number or header residue.
    # 9. Body text for chunk i = build_chunk_header(record) + "\n" + body.
    # 10. chunk_id = f"{record.document}::p{record.page}::c{i}".
    # 11. Copy document, page, doc_title, doc_version from the record.
    #
    # EDGE CASES:
    # - Very short page (< MIN_CHUNK_CHARS)       -> 1 chunk if meaningful, else [].
    # - Page that is one giant line                -> sentence split (step 5).
    # - Table page with 30 rows                    -> several chunks, rows intact.
    # - Course description "ENCS3350 ... Prerequisite: (ENCS338 or ENCS2380)"
    #   spanning 2 lines                           -> same chunk (step 7).
    # - Duplicate consecutive chunks (overlap = whole chunk) -> impossible
    #   because overlap < chunk_size; assert progress in the loop.
    #
    # ACCEPTANCE CRITERIA:
    # - No chunk body exceeds chunk_size, except a single unsplittable token.
    # - Every input line appears in at least one chunk (no silent data loss).
    # - Every COURSE_CODE_PATTERN match in the page appears intact in a chunk.
    raise NotImplementedError("Partner 1 must implement split_page_into_chunks().")


def chunk_pages(
    records: list[PageRecord],
    chunk_size: int,
    chunk_overlap: int,
) -> list[Chunk]:
    """Chunk every page and return all chunks in (document, page, index) order.

    Args:
        records: Output of rag.ingest.ingest_directory().
        chunk_size: From settings.chunk_size.
        chunk_overlap: From settings.chunk_overlap.

    Returns:
        All chunks. chunk_ids are unique.

    Raises:
        ValueError: If records is empty, or if duplicate chunk_ids are produced
            (that would corrupt the id -> metadata mapping in the vector store).
    """
    # TODO(PARTNER 1):
    # 1. If not records -> ValueError("No pages to chunk").
    # 2. chunks = [c for r in records for c in split_page_into_chunks(r, ...)]
    # 3. Exact-duplicate removal: identical BODY text (header excluded) that
    #    appears on many pages (repeated boilerplate) — keep the first
    #    occurrence only, log how many were removed. Do NOT dedupe across
    #    different documents if the text is a fact both state (keep both so
    #    conflicts stay visible).
    # 4. Verify uniqueness of chunk_id; raise ValueError on duplicates.
    # 5. logger.info: total chunks, average length, max length.
    #    Expected order of magnitude with defaults: ~1,300–2,000 chunks.
    #
    # ACCEPTANCE CRITERIA:
    # len({c.chunk_id for c in chunks}) == len(chunks), and every chunk has
    # page >= 1 and a non-empty document.
    raise NotImplementedError("Partner 1 must implement chunk_pages().")
