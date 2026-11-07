"""
File: tests/test_retriever.py

OWNER: Partner 1 — RAG & AI Engineer

PURPOSE:
Unit tests for chunking (rag/chunker.py), the vector store
(rag/vector_store.py), embeddings validation (rag/embeddings.py) and
retrieval (rag/retriever.py). Uses FAKE embeddings and a FAKE store so the
tests run in seconds without downloading a model.

Run:  pytest tests/test_retriever.py -v
"""

from __future__ import annotations

import hashlib
import re

import numpy as np
import pytest

from rag import chunker, embeddings, retriever
from rag.schemas import Chunk, IndexNotReadyError, PageRecord, RetrievedChunk

pending = pytest.mark.xfail(
    raises=NotImplementedError, reason="Pending Partner 1 implementation", strict=False
)

PLAN_DOC = "1_Computer_Engineering_4_YEAR_PLAN_APRIL_25_2026.pdf"
TABLE_PAGE = PageRecord(
    document=PLAN_DOC,
    page=3,
    text="\n".join(
        [
            "ENCS4300 تدريب عملي انهاء 90 ساعة معتمدة وموافقة الدائرة",
            "ENCS5200 مقدمة مشروع التخرج انهاء 95 ساعة معتمدة وموافقة الدائرة",
            "ENCS5300 مشروع التخرج ENCS4300, ENCS5200",
            "ENCS5250 تقنيات حديثة في هندسة الحاسوب انهاء 90 ساعة وموافقة الدائرة",
        ]
        * 6
    ),
    doc_title="Computer Engineering Study Plan",
    doc_version="2026-04-25",
)


# --------------------------------------------------------------------------
# Fakes
# --------------------------------------------------------------------------
DIM = 64


def fake_embed(texts: list[str], kind: str) -> np.ndarray:
    """Deterministic bag-of-tokens hashing embedding, L2-normalized."""
    out = np.zeros((len(texts), DIM), dtype=np.float32)
    for i, text in enumerate(texts):
        for tok in re.findall(r"\w+", text.upper()):
            h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
            out[i, h % DIM] += 1.0
        norm = np.linalg.norm(out[i])
        out[i] = out[i] / norm if norm else out[i]
    return out


class FakeStore:
    """Duck-typed stand-in for VectorStore (brute-force cosine)."""

    def __init__(self, chunks: list[Chunk]):
        self.chunks = chunks
        self.vectors = fake_embed([c.text for c in chunks], "passage") if chunks else np.zeros((0, DIM))

    def search(self, query_vector: np.ndarray, k: int):
        if not self.chunks:
            return []
        scores = self.vectors @ query_vector.reshape(-1)
        order = np.argsort(-scores)[:k]
        return [(self.chunks[i], float(scores[i])) for i in order]


def make_chunk(i: int, text: str, page: int = 1, doc: str = PLAN_DOC) -> Chunk:
    return Chunk(chunk_id=f"{doc}::p{page}::c{i}", document=doc, page=page, text=text)


CHUNKS = [
    make_chunk(0, "ENCS5300 graduation project prerequisite ENCS4300 ENCS5200", page=3),
    make_chunk(1, "ENCS5200 graduation project proposal finish 95 credit hours", page=3),
    make_chunk(2, "Computer Engineering requires 138 credit hours", page=1),
    make_chunk(3, "Attendance rules absence percentage course withdrawal", page=21, doc="BZU.pdf"),
]


# --------------------------------------------------------------------------
# Implemented helpers (should pass now)
# --------------------------------------------------------------------------
def test_e5_prefixes():
    assert embeddings._prefix_for("intfloat/multilingual-e5-small", "query") == "query: "
    assert embeddings._prefix_for("intfloat/multilingual-e5-small", "passage") == "passage: "
    assert embeddings._prefix_for("BAAI/bge-m3", "query") == ""


def test_course_code_pattern_matches_document_codes():
    text = "COMP433 الهندسة البرمجية COMP3330 و MATH1311 و COMP23xx"
    found = chunker.COURSE_CODE_PATTERN.findall(text)
    assert {"COMP433", "COMP3330", "MATH1311", "COMP23xx"} <= set(found)


# --------------------------------------------------------------------------
# chunker
# --------------------------------------------------------------------------
@pending
def test_chunk_header_format():
    rec = PageRecord("a.pdf", 3, "x", "Plan", "2026")
    assert chunker.build_chunk_header(rec) == "[Plan | 2026 | page 3]"


@pending
def test_split_respects_size_and_keeps_metadata():
    chunks = chunker.split_page_into_chunks(TABLE_PAGE, chunk_size=300, chunk_overlap=60)
    assert len(chunks) > 1
    header = chunker.build_chunk_header(TABLE_PAGE)
    for c in chunks:
        assert c.document == PLAN_DOC and c.page == 3
        body = c.text[len(header) + 1 :]
        assert len(body) <= 300
    assert len({c.chunk_id for c in chunks}) == len(chunks)


@pending
def test_split_never_cuts_course_rows():
    chunks = chunker.split_page_into_chunks(TABLE_PAGE, chunk_size=300, chunk_overlap=60)
    row = "ENCS5300 مشروع التخرج ENCS4300, ENCS5200"
    assert any(row in c.text for c in chunks)
    for c in chunks:
        for line in c.text.split("\n")[1:]:
            if line.startswith("ENCS"):
                assert line in TABLE_PAGE.text  # every line is a complete original row


@pending
def test_split_loses_no_lines():
    chunks = chunker.split_page_into_chunks(TABLE_PAGE, chunk_size=300, chunk_overlap=60)
    joined = "\n".join(c.text for c in chunks)
    for line in set(TABLE_PAGE.text.split("\n")):
        assert line in joined


@pending
def test_split_empty_page_returns_no_chunks():
    assert chunker.split_page_into_chunks(PageRecord("a.pdf", 1, ""), 500, 50) == []


@pending
@pytest.mark.parametrize("size,overlap", [(0, 0), (100, 100), (100, -1)])
def test_split_rejects_bad_sizes(size, overlap):
    with pytest.raises(ValueError):
        chunker.split_page_into_chunks(TABLE_PAGE, size, overlap)


@pending
def test_chunk_pages_unique_ids_and_order():
    pages = [TABLE_PAGE, PageRecord(PLAN_DOC, 4, "ENCS5341 تعلم الالة وعلوم البيانات ENCS3340")]
    chunks = chunker.chunk_pages(pages, 300, 60)
    assert len({c.chunk_id for c in chunks}) == len(chunks)
    assert [c.page for c in chunks] == sorted(c.page for c in chunks)


@pending
def test_chunk_pages_empty_input_raises():
    with pytest.raises(ValueError):
        chunker.chunk_pages([], 300, 60)


# --------------------------------------------------------------------------
# embeddings (validation only — no model download)
# --------------------------------------------------------------------------
@pending
@pytest.mark.parametrize("bad", [[], [""], ["ok", "   "]])
def test_embed_texts_rejects_empty_input(bad):
    with pytest.raises(ValueError):
        embeddings.embed_texts(bad, "query", "intfloat/multilingual-e5-small")


# --------------------------------------------------------------------------
# vector store (needs faiss-cpu)
# --------------------------------------------------------------------------
@pending
def test_vector_store_maps_rows_to_chunks():
    pytest.importorskip("faiss")
    from rag.vector_store import VectorStore

    vecs = fake_embed([c.text for c in CHUNKS], "passage")
    store = VectorStore(DIM)
    store.add(CHUNKS, vecs)
    results = store.search(vecs[2], k=1)
    assert results[0][0].chunk_id == CHUNKS[2].chunk_id
    assert results[0][1] == pytest.approx(1.0, abs=1e-4)


@pending
def test_vector_store_dimension_mismatch_raises():
    pytest.importorskip("faiss")
    from rag.vector_store import VectorStore

    store = VectorStore(DIM)
    with pytest.raises(ValueError):
        store.add(CHUNKS[:1], np.ones((1, DIM + 1), dtype=np.float32))


@pending
def test_vector_store_save_load_roundtrip(tmp_path):
    pytest.importorskip("faiss")
    from rag.vector_store import VectorStore

    vecs = fake_embed([c.text for c in CHUNKS], "passage")
    store = VectorStore(DIM)
    store.add(CHUNKS, vecs)
    store.save(tmp_path, {"embedding_model": "fake"})
    loaded = VectorStore.load(tmp_path, expected_model="fake")
    assert [c.chunk_id for c in loaded.chunks] == [c.chunk_id for c in CHUNKS]
    assert loaded.search(vecs[0], 1)[0][0].chunk_id == CHUNKS[0].chunk_id


@pending
def test_vector_store_load_missing_raises(tmp_path):
    pytest.importorskip("faiss")
    from rag.vector_store import VectorStore

    with pytest.raises(IndexNotReadyError):
        VectorStore.load(tmp_path)


# --------------------------------------------------------------------------
# retriever
# --------------------------------------------------------------------------
@pending
@pytest.mark.parametrize(
    "text,lang",
    [
        ("كم ساعة للتخرج؟", "ar"),
        ("How many credit hours?", "en"),
        ("ما هو المتطلب السابق لمساق ENCS5300؟", "ar"),
    ],
)
def test_detect_language(text, lang):
    assert retriever.detect_language(text) == lang


@pending
def test_extract_course_codes_canonicalizes():
    assert retriever.extract_course_codes("encs 5300 and COMP433") == {"ENCS5300", "COMP433"}
    assert retriever.extract_course_codes("ENCS٥٣٠٠") == {"ENCS5300"}


@pending
def test_normalize_for_matching_unifies_variants():
    assert retriever.normalize_for_matching("إنهاء ٩٠ ساعة") == retriever.normalize_for_matching(
        "انهاء 90 ساعه"
    )


@pending
def test_retrieve_returns_ranked_results_with_metadata():
    store = FakeStore(CHUNKS)
    results = retriever.retrieve(
        "prerequisite ENCS5300 graduation project", store, fake_embed, top_k=2, min_similarity=0.1
    )
    assert 1 <= len(results) <= 2
    assert all(isinstance(r, RetrievedChunk) for r in results)
    assert [r.rank for r in results] == list(range(1, len(results) + 1))
    assert results[0].chunk.chunk_id == CHUNKS[0].chunk_id
    assert results[0].score >= results[-1].score


@pending
def test_retrieve_course_code_boost_prefers_exact_code():
    store = FakeStore(CHUNKS)
    results = retriever.retrieve("ENCS5200", store, fake_embed, top_k=3, min_similarity=0.0)
    assert "ENCS5200" in results[0].chunk.text


@pending
def test_retrieve_below_threshold_returns_empty():
    store = FakeStore(CHUNKS)
    assert retriever.retrieve("weather tomorrow in Ramallah", store, fake_embed, 3, 0.95) == []


@pending
@pytest.mark.parametrize("bad", ["", "   ", "x" * (retriever.MAX_QUERY_CHARS + 1)])
def test_retrieve_rejects_bad_queries(bad):
    with pytest.raises(ValueError):
        retriever.retrieve(bad, FakeStore(CHUNKS), fake_embed, 3, 0.0)


@pending
def test_retrieve_empty_store_raises_index_not_ready():
    with pytest.raises(IndexNotReadyError):
        retriever.retrieve("anything", FakeStore([]), fake_embed, 3, 0.0)
