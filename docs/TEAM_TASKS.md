# Team Tasks — 210-Minute Plan

Every file has exactly one owner, so the three partners can work in parallel with no merge conflicts.

| Owner | Files (exclusive) |
|---|---|
| **Partner 1 — RAG & AI** | `rag/schemas.py` (shared contract, changes need agreement), `rag/ingest.py`, `rag/chunker.py`, `rag/embeddings.py`, `rag/vector_store.py`, `rag/retriever.py`, `rag/generator.py`, `rag/pipeline.py`, `rag/__init__.py`, `data/university_docs/manifest.json`, `data/university_docs/README.md`, `tests/test_ingest.py`, `tests/test_retriever.py`, `docs/ARCHITECTURE.md` |
| **Partner 2 — Full-Stack & Integration** | `app.py`, `config.py`, `requirements.txt`, `.env.example`, `.gitignore`, `README.md`, `tests/__init__.py`, `tests/test_pipeline.py`, `docs/INTEGRATION.md`, `docs/TEAM_TASKS.md`, all Git operations on `main` |
| **Partner 3 — QA, Evaluation & Business** | `tests/questions.json`, `tests/evaluate.py`, `docs/EVALUATION.md`, `docs/BUSINESS_PLAN.md`, `docs/MARKETING_PLAN.md`, `docs/DEMO_SCRIPT.md`, `presentation/SLIDE_OUTLINE.md`, `presentation/final_pitch.pdf` |

Priority legend: **P0** = without it the submission fails; **P1** = needed for a strong score; **P2** = only if time allows (after minute 165 nothing new starts).

## Milestones (whole team)

| Minute | Gate | Who checks |
|---|---|---|
| 10 | Contract agreed, repo pushed, everyone has the code | P2 |
| 30 / 60 / 90 / 120 / 150 / 180 | 2-minute stand-up: done / blocked / need from whom | all |
| 75 | Index built and `retrieve()` returns sensible chunks; UI prototype runs in mock mode | P1, P2 |
| 120 | First real end-to-end answer with a correct citation | P2 |
| 165 | **Feature freeze** — bug fixes, evaluation, docs, slides only | P2 |
| 195 | **Code freeze** — final push, tag `v1.0`, submission prep | P2 |
| 210 | Submitted (deadline 3:00 PM) | P2 |

---

## Partner 1 — RAG & AI Engineer

| ID | Time | File → function / section | Input | Expected output | Depends on | Acceptance criteria | Est. | Prio |
|---|---|---|---|---|---|---|---|---|
| P1-01 | 0–10 | `rag/schemas.py`, `docs/INTEGRATION.md` | Team discussion | Agreed contract and default settings | — | All 3 confirm the response dict and status table | 10 | P0 |
| P1-02 | 10–20 | `rag/ingest.py` → `load_manifest`, `discover_pdfs`, `normalize_text` | PDFs + manifest | Functions implemented | P2-02 (deps installed) | `pytest tests/test_ingest.py -k "normalize or discover or manifest"` shows XPASS → remove `@pending` | 10 | P0 |
| P1-03 | 20–35 | `rag/ingest.py` → `extract_pdf` (both branches), `compare_extractors` | PDF path | `list[PageRecord]` | P1-02 | `python -m rag.ingest --compare` passes the most golden checks (incl. "95" on plan p. 3); set `PDF_EXTRACTOR` | 15 | P0 |
| P1-04 | 35–40 | `rag/ingest.py` → `ingest_directory` | `docs_dir` | 659 records | P1-03 | `python -m rag.ingest --stats` prints 625 + 34 pages | 5 | P0 |
| P1-05 | 40–55 | `rag/chunker.py` → all 3 functions | `list[PageRecord]` | `list[Chunk]` | P1-04 | `pytest tests/test_retriever.py -k "chunk or split"` passes; ~1.3k–2k chunks | 15 | P0 |
| P1-06 | 55–62 | `rag/embeddings.py` → `load_embedding_model`, `get_embedding_dimension`, `embed_texts` | texts | `(n, 384)` float32 | P2-02 | One Arabic query embeds; norm = 1.0 | 7 | P0 |
| P1-07 | 62–70 | `rag/vector_store.py` → `VectorStore` (all methods) | chunks + vectors | `storage/index/*` | P1-06 | vector-store tests pass; save → load round-trip | 8 | P0 |
| P1-08 | 70–78 | `rag/pipeline.py` → `build_index`; run it | settings | Built index + meta | P1-05..07 | `python -m rag.pipeline --build-index` finishes; **milestone 75** | 8 | P0 |
| P1-09 | 78–95 | `rag/retriever.py` → `detect_language`, `extract_course_codes`, `normalize_for_matching`, `retrieve` | question | `list[RetrievedChunk]` | P1-08 | Retriever tests pass; "prerequisite of ENCS5300" returns plan p. 3 in Top-5 (`--verbose` shows scores) | 17 | P0 |
| P1-10 | 95–112 | `rag/generator.py` → `format_context`, `build_messages`, `get_llm_client`, `call_llm`, `parse_citations`, `generate_answer` | question + chunks | `RAGResponse` | P1-09, API key | Answer cites `[1]`; invalid tags dropped; `INSUFFICIENT_EVIDENCE` → refusal | 17 | P0 |
| P1-11 | 112–120 | `rag/pipeline.py` → `get_resources`, `_answer_real` | question | response dict | P1-10 | **Milestone 120**: `--mode real --ask "How many credit hours…"` → answered, plan p. 1 | 8 | P0 |
| P1-12 | 120–135 | `.env` `MIN_SIMILARITY` calibration (with P3) | `tests/questions.json` | Threshold + numbers | P1-11, P3-05 | In-scope vs out-of-scope top-1 scores recorded in `docs/EVALUATION.md` | 15 | P1 |
| P1-13 | 135–165 | Fix the worst failures from P3's report (chunking, boost, prompt) | eval report | Improved metrics | P1-12 | Before/after numbers recorded; no test regressions | 30 | P1 |
| P1-14 | 165–195 | Regression: `pytest -q` + `python -m tests.evaluate`; remove all `@pending` markers on implemented functions | — | Green tests | P1-13 | 0 failed, 0 xfailed for implemented code | 30 | P0 |
| P1-15 | 195–210 | Q&A prep from `docs/ARCHITECTURE.md` §3 | — | Ready answers | — | Can explain chunking, embeddings, refusal, conflicts, cost without notes | 15 | P1 |

## Partner 2 — Full-Stack & Integration Engineer

| ID | Time | File → function / section | Input | Expected output | Depends on | Acceptance criteria | Est. | Prio |
|---|---|---|---|---|---|---|---|---|
| P2-01 | 0–10 | Git: create repo, push this skeleton, create branches (commands below) | ZIP | GitHub repo | — | Both partners can clone; `main` protected by convention | 10 | P0 |
| P2-02 | 0–25 (in background) | `requirements.txt`: create venv, install CPU torch then requirements on **all three laptops** | — | Working env | — | `python -c "import fitz, faiss, sentence_transformers, streamlit, openai"` works | 15 | P0 |
| P2-03 | 25–35 | `.env` from `.env.example`; `streamlit run app.py` in mock mode | — | Running UI | P2-02 | Mock answer, sources, MOCK banner visible | 10 | P0 |
| P2-04 | 35–55 | `app.py` → check all 4 states (`#unsupported`, `#error`, spaces, normal) | — | Distinct rendering | P2-03 | No traceback in any state; `pytest tests/test_pipeline.py` all pass | 20 | P0 |
| P2-05 | 55–75 | `app.py` → `render_sidebar` TODOs (documents list, index health, AI note) | manifest, index meta | Sidebar | P2-04 | **Milestone 75**: prototype demoable in mock mode | 20 | P1 |
| P2-06 | 75–100 | `app.py` → duplicate-submission guard; source PDF download button | — | Features | P2-05 | Double Enter does not double-answer; PDF opens at least by download | 25 | P1 |
| P2-07 | 100–120 | `config.py` TODOs (LOG_LEVEL, LLM_BASE_URL validation); help P1 run `--build-index` on the demo laptop | — | — | — | Config tests pass; index exists on the demo laptop | 20 | P1 |
| P2-08 | 120–150 | Switch `RAG_MODE=real`; integration procedure in `docs/INTEGRATION.md` §5; RTL and ~400 px width check | — | Bug list for P1 | P1-11 | All 4 sidebar examples behave correctly | 30 | P0 |
| P2-09 | 150–165 | `README.md` final pass (commands, screenshots, AI disclosure, limitations) | — | README | P2-08 | A stranger can install and run from the README alone | 15 | P0 |
| P2-10 | 165–195 | Clean install test: fresh clone, new venv, follow README exactly; merge P1/P3 final files | — | Verified repo | P2-09 | Fresh clone runs mock mode + real mode; `pytest -q` passes; no `.env` in Git (`git ls-files | grep .env` shows only `.env.example`) | 30 | P0 |
| P2-11 | 195–210 | Code freeze, final push, tag `v1.0`, submit links | — | Submission | P2-10 | Repo public/accessible, links open, slides PDF in `presentation/` | 15 | P0 |

## Partner 3 — QA, Evaluation & Business Lead

| ID | Time | File → function / section | Input | Expected output | Depends on | Acceptance criteria | Est. | Prio |
|---|---|---|---|---|---|---|---|---|
| P3-01 | 0–10 | `docs/DEMO_SCRIPT.md`, `presentation/SLIDE_OUTLINE.md` | Judging guide | Shared understanding of the 9 mandatory slides and the rubric | — | Team agrees the slide list | 10 | P0 |
| P3-02 | 10–35 | `tests/questions.json` → confirm every `PREFILLED_CONFIRM_VISUALLY` case in the PDFs | PDFs | `VERIFIED` + initials | — | Each case checked at the stated page | 25 | P0 |
| P3-03 | 35–45 | `tests/questions.json` → finish Q12; add 2 cases (one more catalog regulation, one more Arabic) | PDFs | ≥ 20 cases | P3-02 | All new cases VERIFIED | 10 | P1 |
| P3-04 | 45–75 | `docs/BUSINESS_PLAN.md` §1–6 (problem, users, alternatives, TAM/SAM/SOM with sources) | Web research | Sourced figures | — | Every number has a source link or the label ASSUMPTION | 30 | P0 |
| P3-05 | 75–100 | `tests/evaluate.py` → all TODO functions | questions.json | Working evaluator | P3-03 | Runs in mock mode without crashing (mock scores are meaningless — do not report them) | 25 | P0 |
| P3-06 | 100–120 | `docs/BUSINESS_PLAN.md` §7–11 (revenue, pricing, costs, projections, risks) | P1's token logs later | Draft numbers | P3-04 | Assumptions table complete | 20 | P0 |
| P3-07 | 120–135 | First real evaluation run; calibrate threshold with P1 | Real pipeline | `storage/eval_report.json` | P1-11 | Report saved; failures listed | 15 | P0 |
| P3-08 | 135–150 | `docs/MARKETING_PLAN.md` | Business plan | Persona, channels, KPIs, 90-day plan | P3-06 | All sections filled | 15 | P0 |
| P3-09 | 150–175 | `docs/EVALUATION.md` + slides 1–9 in the slide tool | Final eval report | Draft deck ≤ 12 slides | P1-13 | Metrics copied from the saved report only | 25 | P0 |
| P3-10 | 175–195 | `docs/DEMO_SCRIPT.md`: screenshots + 2–3 min backup video | Running app | Backup assets | P2-08 | Video shows 1 answered + 1 refused question | 20 | P1 |
| P3-11 | 195–210 | Export `presentation/final_pitch.pdf`; rehearse 5-minute pitch | Deck | PDF + rehearsal | P3-09 | Pitch ≤ 5:00 on a stopwatch | 15 | P0 |

---

## Delivering files to Partner 2

- **With Git (preferred):** work on your branch, push often, tell Partner 2 in the stand-up which files are ready. Partner 2 merges.
- **Without Git:** put **whole files** with their exact repo names into the shared folder `delivery/<partner>/<HHMM>/`. Partner 2 copies them into the repo and commits.

## Git commands

**Partner 2 — create the repository (minute 0–10):**

```bash
unzip smart-academic-advisor.zip && cd smart-academic-advisor
git init -b main
git add .
git status                       # check that .env and storage/ are NOT listed
git commit -m "Starter skeleton: structure, contract, mock mode, TODOs"
# Create an empty repo on GitHub named smart-academic-advisor (no README), then:
git remote add origin https://github.com/<your-user>/smart-academic-advisor.git
git push -u origin main
git switch -c p1-rag && git push -u origin p1-rag
git switch -c p3-eval-business && git push -u origin p3-eval-business
git switch main
```

**Partners 1 and 3 — daily loop:**

```bash
git clone https://github.com/<your-user>/smart-academic-advisor.git && cd smart-academic-advisor
git switch p1-rag                # or p3-eval-business
# ... edit ONLY your own files ...
git add rag/ingest.py            # add files explicitly; never `git add .` with a .env around
git commit -m "P1: implement extract_pdf with PyMuPDF"
git push
```

**Partner 2 — merge and final submission:**

```bash
git switch main && git pull
git merge --no-ff origin/p1-rag -m "Merge P1 RAG work"
git merge --no-ff origin/p3-eval-business -m "Merge P3 evaluation and business docs"
pytest -q
git ls-files | grep -E "(^|/)\.env$" && echo "STOP: .env is tracked" || echo "OK: no .env tracked"
git push
# Code freeze (minute 195):
git tag -a v1.0 -m "IEEE RAG Hackathon submission"
git push origin v1.0
```

If a real key was ever committed: **revoke it in the provider console immediately** (removing it from Git history is not enough), create a new key, and update only your local `.env`.
