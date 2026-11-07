# Architecture

**Owner:** Partner 1 (technical content). Partner 2 keeps it consistent with the code.

## 1. Data flow

```
OFFLINE (once, ~minutes)                         ONLINE (per question, ~1–4 s)
------------------------                         ------------------------------
data/university_docs/*.pdf                       Streamlit UI (app.py)
        │  rag/ingest.py                                 │ answer_question(q)
        ▼                                                ▼
PageRecord(document, page, text, version)        rag/pipeline.py
        │  rag/chunker.py                          ├─ validate input ──► invalid_input
        ▼                                          ├─ mock mode ───────► mock response
Chunk(chunk_id, document, page, text)              └─ real mode:
        │  rag/embeddings.py  ("passage: ")            rag/retriever.py
        ▼                                                ├─ embed query ("query: ")
float32 vectors (L2-normalized)                          ├─ FAISS Top-K × 4 candidates
        │  rag/vector_store.py                           ├─ course-code boost (hybrid)
        ▼                                                ├─ threshold ──► [] ──► insufficient_evidence
storage/index/                                           ▼
  faiss.index  chunks.jsonl  index_meta.json       rag/generator.py
                                                   ├─ numbered context [S1..Sn]
                                                   ├─ LLM (OpenAI-compatible API)
                                                   ├─ INSUFFICIENT_EVIDENCE ──► refusal
                                                   └─ [S#] → real (document, page)
                                                        ▼
                                                   RAGResponse.to_dict()
                                                   validate_response_dict()
                                                        ▼
                                                   app.py renders answer + sources
```

Any exception anywhere in the online path becomes `status = "system_error"` inside `answer_question()`. The UI never shows a traceback.

## 2. Layers and responsibilities

| Layer | File | Responsibility | Must NOT |
|---|---|---|---|
| Contract | `rag/schemas.py` | Dataclasses, statuses, exceptions, `validate_response_dict` | import other project modules |
| Config | `config.py` | Read and validate `.env`; redact secrets | import `rag` |
| Ingestion | `rag/ingest.py` | PDF → normalized `PageRecord`s with page metadata | chunk, embed |
| Chunking | `rag/chunker.py` | Page-bounded, line-aware chunks with a context header | read PDFs |
| Embeddings | `rag/embeddings.py` | Load the model once; normalized vectors | know about FAISS |
| Vector store | `rag/vector_store.py` | FAISS index + row → chunk mapping; save/load/staleness | embed text |
| Retrieval | `rag/retriever.py` | Dense search + code boost + threshold | call the LLM |
| Generation | `rag/generator.py` | Grounded prompt, LLM call, citation mapping, refusal | retrieve |
| Orchestration | `rag/pipeline.py` | `answer_question`, error mapping, index build CLI | render UI |
| UI | `app.py` | Chat, RTL, statuses, sources | contain RAG logic |

Import direction (acyclic): `schemas ← ingest/chunker/embeddings/vector_store ← retriever/generator ← pipeline ← app`; `config` is imported lazily by `pipeline` and directly by `app`.

## 3. Key design decisions (prepare these for the judges' Q&A)

| Decision | Choice | Why | Alternative considered |
|---|---|---|---|
| Chunk boundary | Never cross a page | Every citation is exact; judges can verify in seconds | Cross-page windows (better context, ambiguous citations) |
| Chunk packing | Whole lines, ~900 chars, ~150 overlap | Study-plan table rows keep course + prerequisite together | Token-based recursive splitter |
| Context header | `[title | version | page]` on each chunk | Chunk understandable alone; enables version conflict resolution | Metadata only in the index |
| Embeddings | `multilingual-e5-small` | Arabic + English, cross-lingual, CPU-friendly | `e5-base`, `bge-m3` (better but heavier) |
| Vector store | FAISS `IndexFlatIP` | ~1.5k vectors: exact, instant, no server | Chroma/Qdrant (more setup, no benefit at this size) |
| Hybrid | Course-code regex boost | Dense models confuse ENCS5200 vs ENCS5300 | BM25 (`rank-bm25`) — add only if evaluation shows a need |
| Refusal | Two layers: similarity threshold + LLM `INSUFFICIENT_EVIDENCE` | Cheap pre-filter (no LLM cost) + semantic check | LLM only (costs money on every off-topic question) |
| Citations | `[S#]` tags mapped in code | Model cannot invent file names or pages | Ask the model to write sources (hallucination risk) |
| Conflicts | Prefer newer `doc_version`; mention both | Catalog 2024–25 says 158 h, plan 2026 says 138 h | Silently pick one |
| LLM | Any OpenAI-compatible API via `LLM_BASE_URL` | Switch provider without code changes | Provider-specific SDKs |

## 4. Known data challenges (measured on the real PDFs)

- `BZU.pdf`: 625 pages, Arabic, text layer on every page; ~1.13 M characters with pypdf; ~15 s to extract.
- Study plan: 34 pages, Arabic + English, tables with merged cells (semester labels) and highlighted rows.
- `pypdf` reverses numbers in some RTL table rows (95 → 59 on plan page 3). Golden checks in `rag/ingest.py` catch it.
- Version conflict: 158 (catalog, p. 570) vs 138 (plan, p. 1) credit hours for Computer Engineering.
- Internal inconsistency: ENCS5341's prerequisite is "ENCS3340" in the elective table (p. 4) but "90 credit hours and ENCS3340" in its description (p. 28).

## 5. Security and privacy

- API keys come only from `.env` (git-ignored). `Settings.__repr__` hides the key and `Settings.redacted()` is the only form that may be logged.
- Unknown exceptions show only their class name to users. Our own error messages are written so they never contain secrets.
- All user and LLM text is HTML-escaped before rendering.
- The documents are public university documents. No student data is stored. Questions are not persisted unless the optional feedback feature is added (it must store no personal data).
- Prompt injection: the question is delimited as data, and the system prompt tells the model to ignore instructions inside the question or context. Tested by case Q18.

## 6. Scaling and cost (judges' question 6)

TODO(PARTNER 1): fill in with measured values from your logs, not guesses. Partner 3 copies them into `docs/BUSINESS_PLAN.md` §8 and slide 8.

| Item | How to measure | Value |
|---|---|---|
| Prompt tokens per answer | `resp.usage.prompt_tokens` logged by `call_llm` (mean over the evaluation run) | TODO |
| Completion tokens per answer | `resp.usage.completion_tokens` | TODO |
| Cost per answer | tokens × the provider's published price (cite the pricing page and its date) | TODO |
| Cost at 10,000 users | answers per user per month (labeled ASSUMPTION) × cost per answer | TODO |
| Retrieval latency | per-stage timing logged by `_answer_real` | TODO |

Scaling path: more documents mean a rebuilt index only (FAISS flat stays instant up to roughly hundreds of thousands of chunks; switch to HNSW beyond that). More users means horizontal Streamlit/API instances sharing a read-only index; the LLM API is the main cost driver, and out-of-scope questions cost nothing because the similarity threshold refuses before any LLM call.
