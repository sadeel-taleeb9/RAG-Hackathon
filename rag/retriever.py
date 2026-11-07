"""
File: rag/retriever.py

OWNER: Partner 1 — RAG & AI Engineer

PURPOSE:
Given a user question (Arabic, English, or mixed), return the Top-K most
relevant chunks with scores and exact source metadata, or an EMPTY list when
nothing is relevant enough (which the pipeline turns into an explicit
"insufficient evidence" refusal).

DEPENDENCIES:
- numpy, re, unicodedata, logging (stdlib)
- rag.schemas (Chunk, RetrievedChunk)
- rag.vector_store (VectorStore)
- rag.embeddings (EmbedFn) — injected, so tests can use fake embeddings

EXPECTED OUTPUT:
list[RetrievedChunk], rank 1 = best, len <= top_k, every score >= min_similarity.

RETRIEVAL DESIGN (judging criterion "Retrieval", 10 points; the guide says
the quality of retrieved passages matters more than the number of techniques):
1. Dense retrieval with a multilingual model (cross-lingual Arabic <-> English).
2. Lightweight HYBRID step without an extra library: exact course-code match
   boost. Dense models are weak at exact identifiers ("ENCS5300" vs
   "ENCS5200" look almost identical to them); a regex boost fixes the most
   common advisor question type: "what is the prerequisite of <code>?".
3. Over-fetch (top_k * CANDIDATE_MULTIPLIER) -> boost -> re-sort -> cut to top_k.
4. Relevance threshold on the BEST score: below it, return [] (refusal).
"""

from __future__ import annotations

import logging
import re
import unicodedata

from rag.embeddings import EmbedFn
from rag.schemas import Chunk, IndexNotReadyError, RetrievedChunk
from rag.vector_store import VectorStore

logger = logging.getLogger(__name__)

CANDIDATE_MULTIPLIER = 4
COURSE_CODE_BOOST = 0.05      # added to cosine score per matched course code (tune!)
MAX_QUERY_CHARS = 1000

_ARABIC_CHAR = re.compile(r"[؀-ۿݐ-ݿࢠ-ࣿ]")
_LATIN_CHAR = re.compile(r"[A-Za-z]")
_QUERY_COURSE_CODE = re.compile(r"\b([A-Za-z]{4})\s?(\d{2,5}[A-Za-z]{0,2})\b")
_ARABIC_INDIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


def detect_language(text: str) -> str:
    """Return "ar" or "en" for the dominant script of the text.

    Args:
        text: User question.

    Returns:
        "ar" if Arabic letters >= Latin letters, else "en". Course codes like
        "ENCS5300" inside an Arabic sentence must not flip it to "en":
        "ما هو المتطلب السابق لمساق ENCS5300؟" -> "ar".
    """
    # TODO(PARTNER 1):
    # 1. Count _ARABIC_CHAR and _LATIN_CHAR matches, ignoring course codes
    #    (remove _QUERY_COURSE_CODE matches before counting).
    # 2. Return "ar" if arabic >= latin and arabic > 0, else "en".
    # 3. Empty / digits-only text -> "en" (caller already rejects empty input).
    #
    # ACCEPTANCE CRITERIA:
    # detect_language("كم ساعة للتخرج؟") == "ar"
    # detect_language("How many credit hours?") == "en"
    # detect_language("ما هو المتطلب السابق لمساق ENCS5300؟") == "ar"
    raise NotImplementedError("Partner 1 must implement detect_language().")


def normalize_for_matching(text: str) -> str:
    """Aggressive normalization used ONLY for keyword matching, never for display.

    Steps: NFKC; Arabic-Indic digits -> ASCII; remove diacritics (harakat
    U+064B–U+0652) and tatweel; unify alef forms (أ إ آ -> ا); ta marbuta
    (ة -> ه); alef maqsura (ى -> ي); uppercase Latin; collapse spaces.
    """
    # TODO(PARTNER 1): implement the steps above in that order (~10 lines).
    # ACCEPTANCE CRITERIA:
    # normalize_for_matching("إنهاء ٩٠ ساعة") == normalize_for_matching("انهاء 90 ساعه")
    _ = (unicodedata, _ARABIC_INDIC_DIGITS)  # used by the implementation
    raise NotImplementedError("Partner 1 must implement normalize_for_matching().")


def extract_course_codes(text: str) -> set[str]:
    """Extract course codes, canonicalized (upper case, no inner space).

    "encs 5300 and COMP433" -> {"ENCS5300", "COMP433"}
    """
    # TODO(PARTNER 1):
    # 1. Translate Arabic-Indic digits first (students may type "ENCS٥٣٠٠").
    # 2. For each _QUERY_COURSE_CODE match: (letters.upper() + digits) with
    #    any "xx" placeholder suffix kept lower-case as in the source ("COMP23xx").
    # 3. Return the set.
    raise NotImplementedError("Partner 1 must implement extract_course_codes().")


def retrieve(
    query: str,
    store: VectorStore,
    embed_fn: EmbedFn,
    top_k: int,
    min_similarity: float,
    doc_priority: dict[str, int] | None = None,
) -> list[RetrievedChunk]:
    """Retrieve the most relevant chunks for a question.

    Args:
        query: User question (already validated as non-empty by the pipeline).
        store: Loaded VectorStore.
        embed_fn: Function from rag.embeddings.make_embed_fn (or a fake in tests).
        top_k: Max number of chunks to return (settings.top_k).
        min_similarity: If the best final score is below this, return []
            (settings.min_similarity).
        doc_priority: Optional {filename: priority} from manifest.json; lower
            number = more authoritative. Used only to break near-ties.

    Returns:
        Up to top_k RetrievedChunk objects, rank 1..n, scores descending.
        [] means "no relevant evidence" — NOT an error.

    Raises:
        ValueError: Empty/whitespace query, query longer than MAX_QUERY_CHARS,
            top_k < 1.
        IndexNotReadyError: If the store is empty (propagated / raised here).
    """
    # TODO(PARTNER 1):
    # 1. Validate inputs (ValueError messages are shown to developers only).
    # 2. If len(store.chunks) == 0 -> raise IndexNotReadyError("Index is empty. Run: ...").
    # 3. q_vec = embed_fn([query.strip()], "query")[0]
    # 4. candidates = store.search(q_vec, top_k * CANDIDATE_MULTIPLIER)
    # 5. HYBRID BOOST: codes = extract_course_codes(query). For each candidate,
    #    final = score + COURSE_CODE_BOOST * len(codes & extract_course_codes(chunk.text)).
    #    If codes is non-empty and NO candidate contains any of them, do a
    #    cheap exact scan over store.chunks for chunks containing the code and
    #    add up to top_k of them with score = their dense score (re-embed is
    #    NOT needed: compute np.dot(q_vec, vector) only if you kept vectors;
    #    otherwise give them score = min_similarity + COURSE_CODE_BOOST).
    #    Log when this fallback fires — it is a useful evaluation insight.
    # 6. Tie-break: sort by (-final_score, doc_priority.get(document, 99)).
    # 7. Drop near-duplicate chunks (same document+page and >80% identical
    #    text, e.g. overlap neighbors) so Top-K is not wasted on repeats.
    # 8. THRESHOLD: if not candidates or best final score < min_similarity -> return [].
    #    Also drop individual results below min_similarity - 0.05 so weak
    #    tail chunks do not pollute the prompt.
    # 9. Return RetrievedChunk(chunk, score=final, rank=i+1) for the top_k.
    # 10. logger.debug the (chunk_id, score) list — essential for Partner 3's
    #     Precision@K and for explaining failures to the judges.
    #
    # CALIBRATING min_similarity (do this at ~minute 120, takes 10 minutes):
    # - E5 cosine scores are compressed (often 0.75–0.90 even for unrelated
    #   text), so the default 0.80 is ONLY a placeholder.
    # - Run every question in tests/questions.json, record the top-1 score.
    # - Choose a threshold between the lowest in-scope top-1 score and the
    #   highest out-of-scope top-1 score. If they overlap, prefer fewer false
    #   answers (refusing is cheaper than hallucinating) and rely on the LLM's
    #   INSUFFICIENT_EVIDENCE rule as a second line of defense.
    # - Write the measured numbers into docs/EVALUATION.md.
    #
    # EDGE CASES:
    # - Arabic question about an English passage -> works via multilingual model.
    # - "ENCS 5300" vs "ENCS5300"                -> canonicalized by extract_course_codes.
    # - Greeting "hello" / "مرحبا"               -> low scores -> [] -> polite refusal.
    # - Two documents disagree (158 vs 138 hours) -> BOTH chunks should be
    #   retrieved; the generator resolves the conflict using doc_version.
    #
    # ACCEPTANCE CRITERIA:
    # - For "What is the prerequisite of ENCS5300?" the chunk from the study
    #   plan page 3 containing "ENCS5300" is in the Top-K.
    # - For an out-of-scope question the result is [].
    _ = (Chunk, IndexNotReadyError)  # used by the implementation
    raise NotImplementedError("Partner 1 must implement retrieve().")
