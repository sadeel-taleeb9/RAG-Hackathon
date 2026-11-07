# University Documents

**Owner:** Partner 1 (content and `manifest.json`). Partner 2 commits the files.

This folder holds the official Birzeit University PDFs that the advisor answers from. The RAG pipeline reads **every `*.pdf` in this folder** when you run `python -m rag.pipeline --build-index`.

## Included documents

| File | What it is | Pages | Version | Text layer |
|---|---|---|---|---|
| `BZU.pdf` | Birzeit University Undergraduate Catalog (Arabic) | 625 | 2024–2025 | Yes (no scanned pages found) |
| `1_Computer_Engineering_4_YEAR_PLAN_APRIL_25_2026.pdf` | Computer Engineering (ENCO) program, prerequisites, 4-year plan, course descriptions (Arabic + English) | 34 | 2026-04-25 | Yes |

Page numbers in citations are the **1-based PDF page index** (the number your PDF viewer shows in its toolbar). For `BZU.pdf` the printed page number happens to match the PDF index, which makes it easy to verify.

## Known data issues (found while preparing this starter repo)

These were found by extracting and reading the PDFs. They matter for retrieval quality, evaluation, and the judges' Q&A.

1. **Conflicting versions.** `BZU.pdf` (2024–2025, PDF page 570) says Computer Engineering requires **158** credit hours. The newer study plan (2026-04-25, PDF page 1) says **138**. The system must prefer the newer program-specific document and mention the discrepancy. `manifest.json` records versions and priority for this reason.
2. **Number reversal in RTL table rows.** On study-plan page 3, the prerequisite of ENCS5200 is "finish **95** credit hours" (checked visually). `pypdf` extracts it as "59", and also turned `COMP23xx` into `xx3COMP2`. Partner 1 must compare extractors on this page (see `rag/ingest.py::compare_extractors`).
3. **Lam-alef ligature damage.** `pdftotext` (poppler) splits the "لا" ligature, which produces broken words such as "العالمات" instead of "العلامات". `pypdf` got this right. Check whichever extractor you choose on the word "لا يقل" (study plan, page 1).
4. **Highlighted (changed) rows.** Some rows on study-plan pages 2–3 are highlighted in yellow or red to mark new or changed courses. Highlighting is lost in text extraction. Do not rely on it.

## Adding more documents

1. Copy the PDF into this folder. Use a filename without spaces if you can.
2. Add an entry to `manifest.json` with the **exact** filename as the key (`doc_title`, `doc_version`, `language`, `scope`, `priority`; lower priority number = more authoritative).
3. Rebuild the index: `python -m rag.pipeline --build-index`.
4. Ask Partner 3 to add at least one evaluation question that targets the new document.

Do not put private student data (transcripts, grades, IDs) in this folder. The index and the LLM prompts would contain it.
