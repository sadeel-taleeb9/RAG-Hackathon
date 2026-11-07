"""
File: rag/pipeline.py

OWNER: Partner 1 — RAG & AI Engineer
CONSUMERS: app.py (Partner 2), tests/test_pipeline.py (Partner 2),
           tests/evaluate.py (Partner 3)

PURPOSE:
The ONE public entry point of the RAG system:

    from Rag.pipeline import answer_question
    response = answer_question("How many credit hours ...?")

and the offline index builder:

    python -m rag.pipeline --build-index

DATA FLOW:
PDF -> ingest.extract_pdf -> chunker.chunk_pages -> embeddings.embed_texts
    -> vector_store.VectorStore (saved to storage/index)
At question time:
question -> validate -> retriever.retrieve -> generator.generate_answer
         -> RAGResponse.to_dict() -> validate_response_dict -> app.py

STATUS:
IMPLEMENTED infrastructure (works now, do not break):
  - answer_question(): input validation, mock/real dispatch, error mapping,
    contract validation of every response.
  - mock_answer(): deterministic mock responses for UI development.
  - CLI.
TODO(PARTNER 1):
  - get_resources(), _answer_real(), build_index().

RESPONSE CONTRACT (see rag/schemas.py and docs/INTEGRATION.md):
{
    "answer":    str,                        # always displayable
    "sources":   [{"document": str, "page": int, "excerpt": str}],  # always a list
    "supported": bool,                       # True only when status == "answered"
    "status":    "answered" | "insufficient_evidence" | "invalid_input" | "system_error",
    "error":     str | None,                 # technical detail, only for system_error
    "is_mock":   bool                        # True for mock responses
}
"answer", "sources", "supported" are exactly the three keys agreed in the
team plan; "status", "error", "is_mock" were added to keep invalid input,
missing evidence and technical failure strictly separate.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import time
from typing import TYPE_CHECKING, Any

from Rag.schemas import (
    STATUS_ANSWERED,
    STATUS_INSUFFICIENT_EVIDENCE,
    STATUS_INVALID_INPUT,
    STATUS_SYSTEM_ERROR,
    RAGError,
    RAGResponse,
    SourceCitation,
    validate_response_dict,
)

if TYPE_CHECKING:
    from config import Settings

logger = logging.getLogger(__name__)

MAX_QUESTION_CHARS = 1000
_HAS_LETTER = re.compile(r"[A-Za-z؀-ۿ]")
_ARABIC = re.compile(r"[؀-ۿ]")

INVALID_INPUT_MESSAGES = {
    "empty": "Please type a question. / يرجى كتابة سؤال.",
    "too_long": (
        f"Your question is too long (max {MAX_QUESTION_CHARS} characters). Please shorten it. / "
        f"السؤال طويل جداً (الحد الأقصى {MAX_QUESTION_CHARS} حرف). يرجى اختصاره."
    ),
    "no_letters": "Please type your question using words. / يرجى كتابة السؤال بكلمات.",
    "not_text": "The question must be text. / يجب أن يكون السؤال نصاً.",
}

SYSTEM_ERROR_MESSAGE = (
    "Something went wrong on our side, so I could not answer. This is a technical "
    "problem, not a missing-information problem. Please try again in a moment. / "
    "حدث خطأ تقني ولم أتمكن من الإجابة. يرجى المحاولة مرة أخرى بعد قليل."
)


# ---------------------------------------------------------------------------
# Implemented infrastructure
# ---------------------------------------------------------------------------
def validate_question(question: Any) -> tuple[str | None, str | None]:
    """Validate raw user input.

    Returns:
        (clean_question, None) when valid, or (None, user_message) when invalid.
    """
    if not isinstance(question, str):
        return None, INVALID_INPUT_MESSAGES["not_text"]
    clean = " ".join(question.split())
    if not clean:
        return None, INVALID_INPUT_MESSAGES["empty"]
    if len(clean) > MAX_QUESTION_CHARS:
        return None, INVALID_INPUT_MESSAGES["too_long"]
    if not _HAS_LETTER.search(clean):
        return None, INVALID_INPUT_MESSAGES["no_letters"]
    return clean, None


def mock_answer(question: str) -> RAGResponse:
    """Deterministic MOCK responses so Partner 2 can build the UI before the
    real pipeline exists. Mock answers are clearly labeled and use a fake
    document name, so they can never be mistaken for real academic answers.

    Triggers (type them in the UI to see each state):
        "#unsupported" anywhere in the question -> insufficient_evidence
        "#error"       anywhere in the question -> system_error
        anything else                           -> answered with 2 fake sources
    """
    lowered = question.lower()
    arabic = bool(_ARABIC.search(question))
    if "#error" in lowered:
        return RAGResponse(
            answer="[MOCK] " + SYSTEM_ERROR_MESSAGE,
            status=STATUS_SYSTEM_ERROR,
            error="MockError: simulated technical failure (#error trigger).",
            is_mock=True,
        )
    if "#unsupported" in lowered:
        return RAGResponse(
            answer=(
                "[MOCK] لم أجد هذه المعلومة في الوثائق (رد تجريبي)."
                if arabic
                else "[MOCK] I could not find this in the documents (simulated refusal)."
            ),
            status=STATUS_INSUFFICIENT_EVIDENCE,
            is_mock=True,
        )
    answer = (
        "[MOCK] هذه إجابة تجريبية وليست من وثائق الجامعة [1]. تُستخدم لاختبار الواجهة فقط [2]."
        if arabic
        else "[MOCK] This is a simulated answer, not taken from university documents [1]. "
        "It exists only to test the interface [2]."
    )
    return RAGResponse(
        answer=answer,
        sources=[
            SourceCitation("MOCK_DOCUMENT.pdf", 1, "Mock excerpt — not real university content."),
            SourceCitation("MOCK_DOCUMENT.pdf", 2, "Second mock excerpt."),
        ],
        supported=True,
        status=STATUS_ANSWERED,
        is_mock=True,
    )


def _system_error(exc: BaseException, is_mock: bool = False) -> RAGResponse:
    """Map an exception to a system_error response without leaking secrets."""
    # Messages from our own error classes are written to be safe and useful.
    # For unknown exceptions only the class name is exposed.
    from config import ConfigurationError

    if isinstance(exc, (RAGError, ConfigurationError, NotImplementedError)):
        detail = f"{type(exc).__name__}: {exc}"
    else:
        detail = f"{type(exc).__name__} (see server logs)"
    return RAGResponse(
        answer=SYSTEM_ERROR_MESSAGE,
        status=STATUS_SYSTEM_ERROR,
        error=detail,
        is_mock=is_mock,
    )


def answer_question(question: str, settings: "Settings | None" = None) -> dict[str, Any]:
    """Answer a student's question. NEVER raises.

    Args:
        question: Raw user input (Arabic, English or mixed).
        settings: Optional Settings override (evaluation sweeps, tests).
            Defaults to config.get_settings().

    Returns:
        A dict that satisfies rag.schemas.validate_response_dict().
    """
    started = time.perf_counter()
    is_mock = False
    try:
        clean, problem = validate_question(question)
        if problem is not None:
            response = RAGResponse(answer=problem, status=STATUS_INVALID_INPUT)
        else:
            if settings is None:
                from config import get_settings

                settings = get_settings()
            is_mock = settings.rag_mode == "mock"
            response = mock_answer(clean) if is_mock else _answer_real(clean, settings)  # type: ignore[arg-type]
        result = response.to_dict()
        validate_response_dict(result)
    except Exception as exc:  # noqa: BLE001 — the UI must never see a traceback
        logger.exception("answer_question failed")
        result = _system_error(exc, is_mock=is_mock).to_dict()

    logger.info(
        "answer_question status=%s sources=%d mock=%s latency_ms=%.0f",
        result["status"],
        len(result["sources"]),
        result["is_mock"],
        (time.perf_counter() - started) * 1000,
    )
    return result


# ---------------------------------------------------------------------------
# TODO(PARTNER 1): real pipeline
# ---------------------------------------------------------------------------
_RESOURCES: dict[str, Any] = {}


def get_resources(settings: "Settings") -> dict[str, Any]:
    """Load (once per process) everything needed to answer questions.

    Returns:
        {"store": VectorStore, "embed_fn": EmbedFn, "doc_priority": {filename: int}}

    Raises:
        IndexNotReadyError: Index missing/corrupted/built with another model.
        EmbeddingError: Model cannot be loaded.
    """
    # TODO(PARTNER 1):
    # 1. Cache key: (str(settings.index_dir), settings.embedding_model). If the
    #    key is in _RESOURCES, return the cached dict (Streamlit reruns the
    #    script on every interaction; module globals survive reruns).
    # 2. from Rag.vector_store import VectorStore
    #    store = VectorStore.load(settings.index_dir, expected_model=settings.embedding_model)
    # 3. if store.is_stale(settings.docs_dir): logger.warning("PDFs changed since
    #    the index was built; run --build-index") — keep serving.
    # 4. from Rag.embeddings import make_embed_fn, load_embedding_model
    #    load_embedding_model(settings.embedding_model)  # warm up now, not on 1st question
    #    embed_fn = make_embed_fn(settings.embedding_model, settings.embedding_batch_size)
    # 5. from Rag.ingest import load_manifest
    #    doc_priority = {name: int(meta.get("priority", 99)) for name, meta in load_manifest(settings.docs_dir).items()}
    # 6. Store and return the dict.
    raise NotImplementedError("Partner 1 must implement get_resources().")


def _answer_real(question: str, settings: "Settings") -> RAGResponse:
    """Run the real RAG pipeline."""

    from Rag.retriever import detect_language, retrieve
    from Rag.generator import generate_answer, insufficient_response
    import time

    language = detect_language(question)

    resources = get_resources(settings)

    start = time.perf_counter()

    chunks = retrieve(
        question,
        resources["store"],
        resources["embed_fn"],
        settings.top_k,
        settings.min_similarity,
        resources["doc_priority"],
    )

    retrieval_ms = (time.perf_counter() - start) * 1000

    logger.info("Retrieval completed in %.2f ms", retrieval_ms)

    if not chunks:
        return insufficient_response(language)

    start = time.perf_counter()

    response = generate_answer(
        question,
        chunks,
        language,
        settings,
    )

    generation_ms = (time.perf_counter() - start) * 1000

    logger.info("Generation completed in %.2f ms", generation_ms)

    return response

    raise NotImplementedError("Partner 1 must implement the real RAG path (_answer_real).")


def build_index(settings: "Settings") -> dict[str, Any]:
    """Offline: PDFs -> pages -> chunks -> embeddings -> FAISS index on disk.

    Returns:
        The metadata dict written to index_meta.json.

    Raises:
        IngestionError / EmbeddingError on failure (the CLI prints them).
    """
    # TODO(PARTNER 1):
    # 1. from Rag.ingest import ingest_directory
    #    from Rag.chunker import chunk_pages
    #    from Rag.embeddings import embed_texts, get_embedding_dimension
    #    from Rag.vector_store import VectorStore, file_sha256
    # 2. records = ingest_directory(settings.docs_dir, settings.pdf_extractor)
    # 3. chunks = chunk_pages(records, settings.chunk_size, settings.chunk_overlap)
    # 4. vectors = embed_texts([c.text for c in chunks], "passage",
    #                          settings.embedding_model, settings.embedding_batch_size)
    # 5. store = VectorStore(get_embedding_dimension(settings.embedding_model)); store.add(chunks, vectors)
    # 6. meta = {"embedding_model", "chunk_size", "chunk_overlap", "pdf_extractor",
    #            "documents": {pdf.name: file_sha256(pdf) for pdf in PDFs},
    #            "built_at": datetime.now(timezone.utc).isoformat()}
    # 7. store.save(settings.index_dir, meta); _RESOURCES.clear()
    # 8. Print a summary: pages, chunks, seconds per stage.
    raise NotImplementedError("Partner 1 must implement build_index().")


def _main() -> None:
    """CLI (implemented)."""
    from config import get_settings, override_settings

    parser = argparse.ArgumentParser(description="Smart Academic Advisor RAG pipeline.")
    parser.add_argument("--build-index", action="store_true", help="build the vector index from PDFs")
    parser.add_argument("--ask", metavar="QUESTION", help="ask one question and print the JSON response")
    parser.add_argument("--mode", choices=["mock", "real"], help="override RAG_MODE for this run")
    parser.add_argument("--verbose", action="store_true", help="DEBUG logging (shows retrieval scores)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    settings = override_settings(rag_mode=args.mode) if args.mode else get_settings()

    if args.build_index:
        meta = build_index(settings)
        print(json.dumps(meta, ensure_ascii=False, indent=2))
    elif args.ask:
        print(json.dumps(answer_question(args.ask, settings), ensure_ascii=False, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    _main()
