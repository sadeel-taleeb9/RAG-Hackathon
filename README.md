# Smart Academic Advisor — Birzeit University

A bilingual (Arabic / English) Retrieval-Augmented Generation (RAG) assistant that answers students' academic questions **only from official Birzeit University documents**, cites the exact document and page for every answer, and explicitly refuses when the documents do not contain the answer.

Built for the **IEEE RAG Hackathon 2026 at Bethlehem University** (Problem 1 in the judging guide: "Smart Academic Advisor") by a team of three.

> **Repository status: STARTER SKELETON.** The structure, shared contract, configuration, mock mode, CLI and tests are implemented. The RAG algorithms are documented `TODO`s raising `NotImplementedError`. See `docs/TEAM_TASKS.md`. Update this banner when the real pipeline works.

## Features

- Questions in Arabic, English, mixed text and (target) Palestinian colloquial Arabic.
- Answers grounded in the official PDFs, with numbered citations: document name, page number and an excerpt.
- Explicit refusal when the documents do not contain the answer; no guessing.
- Clear separation of invalid input, missing evidence and technical errors.
- Handles conflicting document versions (e.g. the 2024–2025 catalog says 158 credit hours for Computer Engineering, the 2026 study plan says 138).
- Right-to-left rendering for Arabic.
- Mock mode so the UI works without an API key or index.

## Technology stack

| Layer | Technology |
|---|---|
| UI | Streamlit |
| PDF extraction | PyMuPDF (default), pypdf (fallback) |
| Embeddings | `intfloat/multilingual-e5-small` via sentence-transformers (CPU) |
| Vector store | FAISS `IndexFlatIP` (local files) |
| LLM | Any OpenAI-compatible API (OpenAI, Groq, OpenRouter, Gemini, Ollama) via the `openai` SDK |
| Config | `.env` + python-dotenv |
| Tests | pytest |

## Architecture

```
PDFs ─► ingest (page text + metadata) ─► chunker (page-bounded, line-aware)
     ─► embeddings (multilingual) ─► FAISS index (storage/index)

Question ─► validate ─► retrieve Top-K (+ course-code boost, threshold)
         ─► LLM with numbered context [S1..Sn] ─► citations mapped in code
         ─► {answer, sources, supported, status, error, is_mock} ─► Streamlit
```

Details: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). Contract: [`docs/INTEGRATION.md`](docs/INTEGRATION.md).

## Repository layout

```
smart-academic-advisor/
├── app.py                 Streamlit UI                                   (Partner 2)
├── config.py              Validated settings from .env                   (Partner 2)
├── requirements.txt / .env.example / .gitignore / README.md              (Partner 2)
├── rag/
│   ├── schemas.py         Shared data contract + validator               (Partner 1, agreed by all)
│   ├── ingest.py          PDF → PageRecord                                (Partner 1)
│   ├── chunker.py         PageRecord → Chunk                              (Partner 1)
│   ├── embeddings.py      Multilingual embeddings                         (Partner 1)
│   ├── vector_store.py    FAISS index + metadata mapping                  (Partner 1)
│   ├── retriever.py       Top-K retrieval, hybrid boost, threshold        (Partner 1)
│   ├── generator.py       Grounded prompt, LLM call, citations, refusal   (Partner 1)
│   └── pipeline.py        answer_question(), build_index(), CLI           (Partner 1)
├── data/university_docs/  Official PDFs + manifest.json                   (Partner 1)
├── tests/
│   ├── test_ingest.py, test_retriever.py                                  (Partner 1)
│   ├── test_pipeline.py                                                   (Partner 2)
│   ├── questions.json, evaluate.py                                        (Partner 3)
├── docs/                  Architecture, tasks, integration, evaluation, business, marketing, demo
└── presentation/          SLIDE_OUTLINE.md, final_pitch.pdf               (Partner 3)
```

## Installation

Requirements: Python 3.10–3.12, about 2 GB of free disk space (PyTorch + embedding model), internet for the first run.

```bash
git clone https://github.com/<your-user>/smart-academic-advisor.git
cd smart-academic-advisor
python -m venv .venv
# Windows: .venv\Scripts\activate      macOS/Linux: source .venv/bin/activate
pip install --upgrade pip
pip install torch --index-url https://download.pytorch.org/whl/cpu   # small CPU-only build
pip install -r requirements.txt
```

## Configuration

```bash
cp .env.example .env        # Windows: copy .env.example .env
```

Edit `.env`:

| Variable | Purpose | Default |
|---|---|---|
| `RAG_MODE` | `mock` (simulated answers) or `real` | `mock` |
| `LLM_API_KEY` | Your LLM provider key (never commit it) | placeholder |
| `LLM_BASE_URL` / `LLM_MODEL` | Provider endpoint and model (presets in `.env.example`) | OpenAI / `gpt-4o-mini` |
| `PDF_EXTRACTOR` | `pymupdf` or `pypdf` | `pymupdf` |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | Chunking, in characters | 900 / 150 |
| `EMBEDDING_MODEL` | Multilingual embedding model | `intfloat/multilingual-e5-small` |
| `TOP_K` / `MIN_SIMILARITY` | Retrieval depth / refusal threshold | 5 / 0.80 (to be calibrated) |

## Adding university PDFs

Put PDFs in `data/university_docs/` and add an entry for each in `data/university_docs/manifest.json` (title, version, priority). Two documents ship with the repo: the 2024–2025 undergraduate catalog (`BZU.pdf`, 625 pages) and the 2026 Computer Engineering study plan (34 pages). Known data issues are listed in [`data/university_docs/README.md`](data/university_docs/README.md).

## Build the vector index

```bash
python -m rag.ingest --compare            # optional: choose the PDF extractor with golden checks
python -m rag.pipeline --build-index      # PDFs → chunks → embeddings → storage/index/
```

Rebuild after changing the documents, `EMBEDDING_MODEL`, `CHUNK_SIZE` or `CHUNK_OVERLAP`.

## Run the app

```bash
streamlit run app.py
```

- **Mock mode** (default): no key or index needed. Type `#unsupported` or `#error` in a question to preview those states.
- **Real mode:** set `RAG_MODE=real` and `LLM_API_KEY` in `.env`, build the index, restart Streamlit.

Command-line check without the UI:

```bash
python -m rag.pipeline --mode real --ask "How many credit hours are required to graduate in Computer Engineering?"
```

## Run the tests and the evaluation

```bash
pytest -q                                  # unit + contract tests (no API calls)
RUN_LIVE_TESTS=1 pytest -k live -v         # optional end-to-end tests (real key + index)
python -m tests.evaluate                   # evaluation on tests/questions.json → storage/eval_report.json
```

Tests for unfinished functions are marked `pending` (expected to fail with `NotImplementedError`). When a function is implemented, its tests run for real; remove the marker once they pass. Evaluation results: [`docs/EVALUATION.md`](docs/EVALUATION.md).

## Team

| Member | Role | Owns |
|---|---|---|
| Partner 1 — Taqwa | RAG & AI Engineer | `rag/`, RAG tests, architecture |
| Partner 2 — Sadeel | Full-Stack & Integration Engineer | `app.py`, config, README, integration, GitHub |
| Partner 3 — Obada | QA, Evaluation & Business Lead | evaluation dataset and report, business, marketing, slides, demo |

## Limitations

- Knowledge is limited to the two included documents. Questions about fees, schedules, or other programs' newer plans may be refused.
- The 2024–2025 catalog may be out of date for programs other than Computer Engineering.
- PDF table extraction is imperfect (merged cells, highlighted rows, RTL number order); see `data/university_docs/README.md`.
- No conversation memory: each question is answered independently.
- The LLM requires internet access; retrieval runs locally.
- Answers are informational; students should confirm official decisions with the Registrar or their academic advisor.

## Security

- API keys are read only from `.env`, which is git-ignored. `.env.example` contains placeholders only.
- No student personal data is indexed or stored.
- All user and model text is HTML-escaped before rendering.

## AI usage disclosure

Required by the hackathon rules. TODO(PARTNER 2): update this section at the end with what actually happened.

- The starter repository structure, module skeletons, TODO instructions, shared schema, configuration loader, mock mode, CLI scaffolding, test skeletons, evaluation question templates and documentation templates were generated with **Claude (Anthropic)** from the team's own planning documents, and reviewed by the team.
- While preparing the skeleton, the AI extracted text from the provided PDFs to pre-fill page references in `tests/questions.json` and to document data issues. Pre-filled references are marked `PREFILLED_CONFIRM_VISUALLY` until a team member verifies them.
- TODO: list which functions each partner implemented themselves and which were written or suggested by AI tools (name the tools), as the judges will ask (question 8 of the judges' question bank).

## Demo

See [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md). TODO(PARTNER 2): add the screenshots and backup video link that Partner 3 prepares.
