"""
File: rag/vector_store.py

OWNER: Partner 1 — RAG & AI Engineer

PURPOSE:
Store chunk embeddings in a local FAISS index, keep an exact
row -> Chunk mapping, and save/load both to disk so the Streamlit app never
re-embeds documents at request time.

DEPENDENCIES:
- faiss-cpu (imported INSIDE methods only)
- numpy, json, hashlib, pathlib, logging (stdlib)
- rag.schemas (Chunk, IndexNotReadyError)

ON-DISK LAYOUT (settings.index_dir, default storage/index/, git-ignored):
    faiss.index       FAISS IndexFlatIP (exact inner-product search)
    chunks.jsonl      one JSON Chunk per line; line i <-> FAISS row i
    index_meta.json   {"embedding_model", "dimension", "chunk_size",
                       "chunk_overlap", "pdf_extractor", "num_chunks",
                       "documents": {filename: sha256}, "built_at"}

WHY IndexFlatIP: ~1.5k vectors x 384 dims is tiny; exact search takes
microseconds, needs no training, and is deterministic. With L2-normalized
vectors, inner product == cosine similarity. Scaling note for the judges:
switch to IndexHNSWFlat beyond roughly 1M chunks.

EXPECTED OUTPUT:
VectorStore.search() returns (Chunk, score) pairs whose metadata comes from
chunks.jsonl, never from the LLM.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from rag.schemas import Chunk, IndexNotReadyError

logger = logging.getLogger(__name__)

INDEX_FILE = "faiss.index"
CHUNKS_FILE = "chunks.jsonl"
META_FILE = "index_meta.json"


def file_sha256(path: Path) -> str:
    """Return the SHA-256 hex digest of a file (implemented helper)."""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


class VectorStore:
    """FAISS index + aligned chunk list.

    Invariant: self.index.ntotal == len(self.chunks) at all times, and row i
    of the index is the embedding of self.chunks[i].
    """

    def __init__(self, dimension: int) -> None:
        """Create an EMPTY store.

        Args:
            dimension: Embedding size (e.g. 384). Must be > 0.

        Raises:
            ValueError: If dimension <= 0.
            ImportError: If faiss is not installed (message must say
                `pip install faiss-cpu`).
        """
        # TODO(PARTNER 1):
        # 1. Validate dimension > 0.
        # 2. import faiss (inside the method) -> on ImportError re-raise with a
        #    clear install hint.
        # 3. self.dimension = dimension
        #    self.index = faiss.IndexFlatIP(dimension)
        #    self.chunks: list[Chunk] = []
        #    self.meta: dict[str, Any] = {}
        raise NotImplementedError("Partner 1 must implement VectorStore.__init__().")

    def add(self, chunks: list[Chunk], vectors: np.ndarray) -> None:
        """Add chunks and their vectors, preserving alignment.

        Args:
            chunks: Chunks in the same order as the vector rows.
            vectors: float32 array (len(chunks), dimension), L2-normalized.

        Raises:
            ValueError: Empty input, len(chunks) != vectors.shape[0], wrong
                dimension, non-float32 dtype that cannot be converted, NaN
                values, or a chunk_id already present in the store.
        """
        # TODO(PARTNER 1):
        # 1. Validate non-empty and equal lengths.
        # 2. vectors = np.ascontiguousarray(vectors, dtype=np.float32)
        # 3. Validate vectors.ndim == 2 and vectors.shape[1] == self.dimension
        #    -> ValueError("Vector dimension mismatch: expected D, got d. "
        #       "Did you change EMBEDDING_MODEL without rebuilding?").
        # 4. Validate np.isfinite(vectors).all().
        # 5. Reject duplicate chunk_ids (against existing + within batch).
        # 6. self.index.add(vectors); self.chunks.extend(chunks)
        # 7. assert self.index.ntotal == len(self.chunks)
        raise NotImplementedError("Partner 1 must implement VectorStore.add().")

    def search(self, query_vector: np.ndarray, k: int) -> list[tuple[Chunk, float]]:
        """Return the k most similar chunks.

        Args:
            query_vector: float32 array of shape (dimension,) or (1, dimension),
                L2-normalized.
            k: Number of results (>= 1). If k > number of chunks, return all.

        Returns:
            [(chunk, score), ...] sorted by score descending. Empty list only
            if the store is empty (callers treat that as IndexNotReadyError).

        Raises:
            ValueError: Wrong dimension or k < 1.
        """
        # TODO(PARTNER 1):
        # 1. Validate k >= 1; reshape query to (1, dimension); check dimension.
        # 2. If self.index.ntotal == 0 -> return [].
        # 3. k_eff = min(k, self.index.ntotal)
        # 4. scores, ids = self.index.search(query, k_eff)
        # 5. FAISS returns id -1 for missing results: skip any id < 0.
        # 6. Map each id to self.chunks[id] (bounds-check; an out-of-range id
        #    means the files are out of sync -> raise IndexNotReadyError).
        # 7. Return [(chunk, float(score)), ...].
        raise NotImplementedError("Partner 1 must implement VectorStore.search().")

    def save(self, index_dir: Path, meta: dict[str, Any]) -> None:
        """Persist index, chunks and metadata atomically enough for a hackathon.

        Args:
            index_dir: Target folder (created if missing).
            meta: Build metadata (see module docstring). num_chunks and
                dimension are filled in here.
        """
        # TODO(PARTNER 1):
        # 1. index_dir.mkdir(parents=True, exist_ok=True)
        # 2. Write to temporary names first (e.g. "faiss.index.tmp"), then
        #    Path.replace() to the final names, so a crash mid-save does not
        #    leave a half-written index that loads "successfully".
        # 3. faiss.write_index(self.index, str(tmp_index))
        # 4. chunks.jsonl: one json.dumps(asdict(chunk), ensure_ascii=False)
        #    per line, encoding="utf-8" (Arabic must stay readable).
        # 5. index_meta.json with meta + {"num_chunks": len(self.chunks),
        #    "dimension": self.dimension}, ensure_ascii=False, indent=2.
        _ = (asdict, json)  # used by the implementation
        raise NotImplementedError("Partner 1 must implement VectorStore.save().")

    @classmethod
    def load(cls, index_dir: Path, expected_model: str | None = None) -> "VectorStore":
        """Load a store saved by save().

        Args:
            index_dir: Folder containing the three files.
            expected_model: If given, must equal meta["embedding_model"].

        Returns:
            A ready VectorStore.

        Raises:
            IndexNotReadyError: Any missing file, unreadable/corrupted file,
                ntotal != number of chunk lines, dimension mismatch, or model
                mismatch. The message MUST end with the fix:
                "Run: python -m rag.pipeline --build-index".
        """
        # TODO(PARTNER 1):
        # 1. Check all three files exist -> IndexNotReadyError listing missing.
        # 2. meta = json.loads(...); index = faiss.read_index(...);
        #    chunks = [Chunk(**json.loads(line)) for line in file if line.strip()]
        #    Wrap each step: any exception -> IndexNotReadyError("corrupted ...").
        # 3. Consistency checks: index.ntotal == len(chunks) == meta["num_chunks"];
        #    index.d == meta["dimension"].
        # 4. If expected_model and meta["embedding_model"] != expected_model ->
        #    IndexNotReadyError("Index was built with X but EMBEDDING_MODEL is Y").
        # 5. Build the instance without re-creating an empty index:
        #    store = cls.__new__(cls); set dimension, index, chunks, meta.
        # 6. logger.info number of chunks loaded.
        raise NotImplementedError("Partner 1 must implement VectorStore.load().")

    def is_stale(self, docs_dir: Path) -> bool:
        """Return True if the PDFs on disk differ from those the index was built from.

        Compare {pdf.name: file_sha256(pdf)} for the PDFs in docs_dir with
        self.meta["documents"]. pipeline.py logs a WARNING when stale (it does
        not auto-rebuild during a request; rebuilding takes minutes).
        """
        # TODO(PARTNER 1): implement as described above (5 lines).
        raise NotImplementedError("Partner 1 must implement VectorStore.is_stale().")
