# Integration Contract

**Owner:** Partner 2 (integration). The contract itself lives in `rag/schemas.py` (owned by Partner 1). All three partners agree on it in minutes 0–10. After that, any change needs a message to the other two **before** it is pushed.

## 1. The one function the UI calls

```python
from rag.pipeline import answer_question

response: dict = answer_question(question: str)   # never raises
```

### Response structure

```python
{
    "answer":    "The program requires 138 credit hours [1]. ...",   # str, always displayable
    "sources":   [                                                    # list, ALWAYS a list
        {"document": "1_Computer_Engineering_4_YEAR_PLAN_APRIL_25_2026.pdf",
         "page": 1,                                                   # int >= 1, PDF page index
         "excerpt": "تمنح دائرة الهندسة الكهربائية ..."}              # str, optional, <= ~300 chars
    ],
    "supported": True,                                                # bool
    "status":    "answered",                                          # see table below
    "error":     None,                                                # str only for system_error
    "is_mock":   False                                                # bool
}
```

`answer`, `sources` and `supported` are the three keys agreed in the team plan. `status`, `error` and `is_mock` were added so that the three failure cases can never be confused.

### Status values

| status | Meaning | supported | sources | error | UI rendering |
|---|---|---|---|---|---|
| `answered` | Grounded answer with ≥ 1 citation | `True` | ≥ 1 | `None` | answer + numbered sources |
| `insufficient_evidence` | Documents do not contain the answer | `False` | `[]` | `None` | blue info box (refusal) |
| `invalid_input` | Empty, too long, or no words | `False` | `[]` | `None` | yellow warning |
| `system_error` | Technical failure (LLM, index, config…) | `False` | `[]` | short technical text | red error + "Technical details" expander |

`rag.schemas.validate_response_dict()` enforces every rule in this table. `answer_question()` runs it on every response before returning. A violation turns into `system_error` with the violation in `error`, so contract bugs show up immediately instead of silently.

## 2. Functions each partner exposes

| Partner | Module | Function | Input → Output |
|---|---|---|---|
| P1 | `rag/ingest.py` | `ingest_directory(docs_dir, extractor)` | `Path, str` → `list[PageRecord]` |
| P1 | `rag/chunker.py` | `chunk_pages(records, chunk_size, chunk_overlap)` | → `list[Chunk]` |
| P1 | `rag/embeddings.py` | `embed_texts(texts, kind, model_name, batch_size)` / `make_embed_fn(...)` | → `np.ndarray (n, dim) float32` |
| P1 | `rag/vector_store.py` | `VectorStore.add / search / save / load` | `search(vec, k)` → `list[(Chunk, float)]` |
| P1 | `rag/retriever.py` | `retrieve(query, store, embed_fn, top_k, min_similarity, doc_priority)` | → `list[RetrievedChunk]` (`[]` = no evidence) |
| P1 | `rag/generator.py` | `generate_answer(question, chunks, language, settings)` | → `RAGResponse` |
| P1 | `rag/pipeline.py` | `answer_question(question)` and `build_index(settings)` | → `dict` (above) |
| P2 | `config.py` | `get_settings()` | → `Settings` |
| P2 | `app.py` | — (consumer only) | |
| P3 | `tests/evaluate.py` | `python -m tests.evaluate` | → `storage/eval_report.json` |

## 3. Error handling rules

| Situation | Raised where | Becomes |
|---|---|---|
| Empty / whitespace / > 1000 chars / no letters | `pipeline.validate_question` | `invalid_input` |
| No chunk above `MIN_SIMILARITY` | `retriever.retrieve` returns `[]` | `insufficient_evidence` (no LLM call) |
| LLM replies `INSUFFICIENT_EVIDENCE` or cites nothing valid | `generator.generate_answer` | `insufficient_evidence` |
| Index missing / corrupted / built with another model | `IndexNotReadyError` | `system_error` ("Run: python -m rag.pipeline --build-index") |
| Model download/load failure | `EmbeddingError` | `system_error` |
| Auth, timeout, rate limit, network, unknown model | `LLMServiceError` | `system_error` |
| Bad `.env` value / missing key in real mode | `ConfigurationError` | `system_error` (UI also shows it at startup) |
| Anything unexpected | any `Exception` | `system_error` with class name only |

Rule of thumb for Partner 1: **return** `insufficient_evidence` when the documents lack the answer; **raise** a `RAGError` subclass when something is broken. Never return `system_error` yourself.

## 4. Mock → real switch

1. Minutes 10–120: Partner 2 builds the UI with `RAG_MODE=mock` (the default). Mock triggers: type `#unsupported` or `#error` in a question to see those states; send spaces to see `invalid_input`.
2. Mock responses start with `[MOCK]`, set `is_mock=True`, cite `MOCK_DOCUMENT.pdf`, and the UI shows a MOCK MODE banner. They can never pass as real answers.
3. When Partner 1 says "real path ready" (target: minute 120):
   ```bash
   python -m rag.pipeline --build-index           # once; downloads the model the first time
   python -m rag.pipeline --mode real --ask "How many credit hours are required to graduate in Computer Engineering?"
   ```
4. If the CLI answer is valid, set `RAG_MODE=real` in `.env` and restart Streamlit. No code change is needed in `app.py`.

## 5. Integration test procedure (Partner 2, at minutes 120 and 165)

```bash
pytest -q                                   # contract, config and mock tests must pass
python -m rag.pipeline --mode real --ask "What is the prerequisite of COMP433 Software Engineering?"
python -m rag.pipeline --mode real --ask "What is the weather in Ramallah tomorrow?"   # must be insufficient_evidence
python -m rag.pipeline --mode real --ask "   "                                         # must be invalid_input
streamlit run app.py                        # click the 4 sidebar examples
```

## 6. Diagnosing contract mismatches

| Symptom in the UI | Likely cause | Fix |
|---|---|---|
| "Integration contract mismatch: 'sources' must always be a list" | `None` returned instead of `[]` | Use `RAGResponse(...).to_dict()`; never build dicts by hand |
| `system_error` with "An 'answered' response must cite at least one source" | Generator returned `answered` with no valid citations | Follow strict mode in `generate_answer` step 6 |
| `system_error` with "'supported' must be True if and only if…" | `supported` set independently of `status` | Set both together |
| `sources[i]['page'] must be an int >= 1` | 0-based page index or page as string | Use `page = i + 1` in `extract_pdf` |
| `NotImplementedError (see server logs)` | Real mode on before the pipeline is finished | Use `RAG_MODE=mock` |
| `IndexNotReadyError: … built with X but EMBEDDING_MODEL is Y` | Model changed after building | Rebuild the index |

## 7. File delivery to Partner 2 (only Partner 2 pushes to `main`)

Choose ONE method in minute 0–10:

- **Preferred: feature branches.** Partner 1 pushes to `p1-rag`, Partner 3 to `p3-eval-business`. Partner 2 merges into `main`. Because every file has exactly one owner, merges have no conflicts.
- **Fallback (no Git access):** a shared folder (Google Drive/USB) with **whole files** named exactly as in the repo. Partner 2 copies them in and commits with the message `P1: <what>` or `P3: <what>`.

Never send code through chat apps that change quotes or indentation.
