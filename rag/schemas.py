"""
File: rag/schemas.py

OWNER: Partner 1 — RAG & AI Engineer
CHANGE POLICY: This file is the SHARED CONTRACT. It is agreed by all three
partners in minutes 0–10. After that, any change requires a message to
Partner 2 and Partner 3 BEFORE the change is pushed (see docs/INTEGRATION.md).

PURPOSE:
Single source of truth for every data structure that crosses a module
boundary:

    PageRecord      ingest.py      -> chunker.py
    Chunk           chunker.py     -> embeddings.py / vector_store.py
    RetrievedChunk  retriever.py   -> generator.py / pipeline.py
    SourceCitation  generator.py   -> pipeline.py -> app.py
    RAGResponse     pipeline.py    -> app.py / tests / tests/evaluate.py

DEPENDENCIES:
- Python standard library only (dataclasses, typing).
- MUST NOT import any other project module. Every other module imports
  from here, so importing anything back would create a circular import.

STATUS:
This file is intentionally IMPLEMENTED (not a TODO skeleton) because it is
infrastructure that all three partners need from minute 10 onwards.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Final

# ---------------------------------------------------------------------------
# Response status values.
#
# The three failure categories required by the project brief are kept
# strictly separate:
#   1. STATUS_INVALID_INPUT          -> the user typed something unusable
#   2. STATUS_INSUFFICIENT_EVIDENCE  -> the documents do not support an answer
#   3. STATUS_SYSTEM_ERROR           -> something technical broke
# Only STATUS_ANSWERED may have supported=True.
# ---------------------------------------------------------------------------
STATUS_ANSWERED: Final[str] = "answered"
STATUS_INSUFFICIENT_EVIDENCE: Final[str] = "insufficient_evidence"
STATUS_INVALID_INPUT: Final[str] = "invalid_input"
STATUS_SYSTEM_ERROR: Final[str] = "system_error"

VALID_STATUSES: Final[frozenset[str]] = frozenset(
    {
        STATUS_ANSWERED,
        STATUS_INSUFFICIENT_EVIDENCE,
        STATUS_INVALID_INPUT,
        STATUS_SYSTEM_ERROR,
    }
)

# Keys that MUST exist in every dict returned by rag.pipeline.answer_question().
REQUIRED_RESPONSE_KEYS: Final[tuple[str, ...]] = (
    "answer",
    "sources",
    "supported",
    "status",
    "error",
    "is_mock",
)


# ---------------------------------------------------------------------------
# Exceptions raised INSIDE the RAG package.
# rag.pipeline.answer_question() catches all of them and converts them into a
# STATUS_SYSTEM_ERROR response, so app.py never needs try/except around RAG
# internals. Configuration errors live in config.py (ConfigurationError) so
# that config.py does not depend on the rag package.
# ---------------------------------------------------------------------------
class RAGError(Exception):
    """Base class for every technical failure inside the RAG pipeline."""


class IngestionError(RAGError):
    """A PDF could not be read, or produced no usable text."""


class EmbeddingError(RAGError):
    """The embedding model could not be loaded or returned invalid vectors."""


class IndexNotReadyError(RAGError):
    """The vector index is missing, empty, stale, or corrupted."""


class LLMServiceError(RAGError):
    """The LLM API failed: auth, timeout, rate limit, or malformed output."""


# ---------------------------------------------------------------------------
# Data records
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PageRecord:
    """One extracted PDF page.

    Attributes:
        document: Original PDF filename, e.g. "BZU.pdf" (never a full path,
            so citations do not leak local directory names).
        page: 1-based PDF page index (the page number a PDF viewer shows in
            its toolbar, which is what a judge will type to verify a citation).
        text: Normalized page text. May be "" for pages with no text layer;
            ingest.py must record those pages (and warn) rather than drop them.
        doc_title: Human-readable title from data/university_docs/manifest.json.
        doc_version: Version/effective-date label from the manifest, used to
            resolve conflicts between an old catalog and a newer study plan.
    """

    document: str
    page: int
    text: str
    doc_title: str = ""
    doc_version: str = ""


@dataclass(frozen=True)
class Chunk:
    """A retrievable unit of text.

    Attributes:
        chunk_id: Stable, unique id, format "<document>::p<page>::c<index>",
            e.g. "BZU.pdf::p570::c2". Stable ids make evaluation labels reusable
            across index rebuilds as long as chunking settings do not change.
        document: Same as PageRecord.document.
        page: Same as PageRecord.page. A chunk NEVER spans two pages, so this
            is always a single, exact citation target.
        text: The chunk text exactly as it will be shown to the LLM.
        doc_title: Copied from PageRecord.
        doc_version: Copied from PageRecord.
    """

    chunk_id: str
    document: str
    page: int
    text: str
    doc_title: str = ""
    doc_version: str = ""


@dataclass(frozen=True)
class RetrievedChunk:
    """A chunk returned by the retriever, with its similarity score.

    Attributes:
        chunk: The retrieved Chunk (metadata comes from the index mapping,
            NEVER from the LLM).
        score: Similarity score. With L2-normalized embeddings and an
            inner-product FAISS index this is cosine similarity in [-1, 1];
            higher is better.
        rank: 1-based rank after all re-ranking / boosting steps.
    """

    chunk: Chunk
    score: float
    rank: int


@dataclass(frozen=True)
class SourceCitation:
    """A citation displayed to the user.

    Attributes:
        document: PDF filename that exists in data/university_docs/.
        page: 1-based PDF page index.
        excerpt: Optional short excerpt (<= ~300 chars) of the cited chunk so
            the user can verify the answer without opening the PDF.
    """

    document: str
    page: int
    excerpt: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RAGResponse:
    """The ONLY structure that rag.pipeline.answer_question() returns
    (as a plain dict via to_dict()).

    Invariants (enforced by validate()):
        - supported is True  <=> status == STATUS_ANSWERED
        - status == STATUS_ANSWERED  =>  len(sources) >= 1
        - status in {INVALID_INPUT, INSUFFICIENT_EVIDENCE} => sources == []
        - error is None unless status == STATUS_SYSTEM_ERROR
        - answer is always a non-empty, user-displayable string
    """

    answer: str
    sources: list[SourceCitation] = field(default_factory=list)
    supported: bool = False
    status: str = STATUS_INSUFFICIENT_EVIDENCE
    error: str | None = None
    is_mock: bool = False

    def validate(self) -> None:
        """Raise ValueError if any contract invariant is broken."""
        validate_response_dict(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "sources": [s.to_dict() for s in self.sources],
            "supported": self.supported,
            "status": self.status,
            "error": self.error,
            "is_mock": self.is_mock,
        }


# ---------------------------------------------------------------------------
# Contract validation (used by pipeline.py before returning, by app.py
# defensively, and by tests/test_pipeline.py + tests/evaluate.py).
# ---------------------------------------------------------------------------
def validate_response_dict(response: Any) -> None:
    """Validate a response dict against the integration contract.

    Args:
        response: The object returned by answer_question().

    Raises:
        ValueError: With a precise message naming the first broken rule, so a
            contract mismatch can be diagnosed in seconds.
    """
    if not isinstance(response, dict):
        raise ValueError(f"Response must be a dict, got {type(response).__name__}.")

    missing = [k for k in REQUIRED_RESPONSE_KEYS if k not in response]
    if missing:
        raise ValueError(f"Response is missing required keys: {missing}.")

    answer = response["answer"]
    sources = response["sources"]
    supported = response["supported"]
    status = response["status"]
    error = response["error"]
    is_mock = response["is_mock"]

    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("'answer' must be a non-empty string.")
    if not isinstance(sources, list):
        raise ValueError("'sources' must always be a list (use [] when empty).")
    if not isinstance(supported, bool):
        raise ValueError("'supported' must be a bool, not a truthy value.")
    if status not in VALID_STATUSES:
        raise ValueError(f"'status' must be one of {sorted(VALID_STATUSES)}, got {status!r}.")
    if error is not None and not isinstance(error, str):
        raise ValueError("'error' must be None or a string.")
    if not isinstance(is_mock, bool):
        raise ValueError("'is_mock' must be a bool.")

    for i, src in enumerate(sources):
        if not isinstance(src, dict):
            raise ValueError(f"sources[{i}] must be a dict.")
        if not isinstance(src.get("document"), str) or not src["document"].strip():
            raise ValueError(f"sources[{i}]['document'] must be a non-empty string.")
        page = src.get("page")
        if not isinstance(page, int) or isinstance(page, bool) or page < 1:
            raise ValueError(f"sources[{i}]['page'] must be an int >= 1.")
        if "excerpt" in src and not isinstance(src["excerpt"], str):
            raise ValueError(f"sources[{i}]['excerpt'] must be a string when present.")

    if supported != (status == STATUS_ANSWERED):
        raise ValueError("'supported' must be True if and only if status == 'answered'.")
    if status == STATUS_ANSWERED and not sources:
        raise ValueError("An 'answered' response must cite at least one source.")
    if status in (STATUS_INVALID_INPUT, STATUS_INSUFFICIENT_EVIDENCE) and sources:
        raise ValueError(f"A '{status}' response must have sources == [].")
    if status != STATUS_SYSTEM_ERROR and error is not None:
        raise ValueError("'error' must be None unless status == 'system_error'.")
