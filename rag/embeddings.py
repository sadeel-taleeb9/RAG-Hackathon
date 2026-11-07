"""
File: rag/embeddings.py

OWNER: Partner 1 — RAG & AI Engineer

PURPOSE:
Turn chunk texts and user queries into L2-normalized float32 vectors with a
multilingual (Arabic + English) embedding model, loading the model once per
process.

DEPENDENCIES:
- sentence-transformers (imported INSIDE load_embedding_model only)
- numpy
- functools.lru_cache, logging (stdlib)
- rag.schemas (EmbeddingError)

EXPECTED OUTPUT:
numpy.ndarray of shape (n, dim), dtype float32, each row with L2 norm 1.0,
so inner product == cosine similarity in the FAISS index.

MODEL CHOICE (judges ask this — question 2 of the judges' question bank):
Default: intfloat/multilingual-e5-small (~118M params, 384-dim, ~470 MB,
runs on CPU). It is trained on many languages including Arabic, so an Arabic
question can retrieve an English passage and vice versa (the study plan mixes
both). Alternatives if evaluation shows weak Arabic recall:
  - intfloat/multilingual-e5-base   (768-dim, better, ~2x slower)
  - BAAI/bge-m3                     (1024-dim, strong Arabic, heavy on CPU)
Changing the model REQUIRES rebuilding the index (dimension changes).

E5 MODELS REQUIRE PREFIXES: "query: " for questions and "passage: " for
documents. Without them retrieval quality drops noticeably. Other model
families (bge-m3, MiniLM) must NOT get these prefixes — see _prefix_for().
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Callable, Literal

import numpy as np

from rag.schemas import EmbeddingError

logger = logging.getLogger(__name__)

TextKind = Literal["query", "passage"]

# Signature used for dependency injection in retriever.py and in tests:
# a function that takes texts + kind and returns an (n, dim) float32 array.
EmbedFn = Callable[[list[str], TextKind], np.ndarray]


def _prefix_for(model_name: str, kind: TextKind) -> str:
    """Return the text prefix the model family expects (implemented)."""
    if "e5" in model_name.lower():
        return "query: " if kind == "query" else "passage: "
    return ""


@lru_cache(maxsize=2)
def load_embedding_model(model_name: str) -> Any:
    """Load (once) and return a SentenceTransformer model.

    Args:
        model_name: Hugging Face model id from settings.embedding_model.

    Returns:
        A loaded sentence_transformers.SentenceTransformer.

    Raises:
        EmbeddingError: If the library is missing, the model cannot be
            downloaded (offline), or loading fails for any other reason.
    """
    # TODO(PARTNER 1):
    # 1. try: from sentence_transformers import SentenceTransformer
    #    except ImportError as exc: raise EmbeddingError(
    #        "sentence-transformers is not installed: pip install -r requirements.txt") from exc
    # 2. try: model = SentenceTransformer(model_name, device="cpu")
    #    except Exception as exc: raise EmbeddingError(
    #        f"Could not load embedding model {model_name!r}. First run needs internet "
    #        "to download it (~470 MB for e5-small); later runs use the local "
    #        "Hugging Face cache.") from exc
    # 3. logger.info model name + model.get_sentence_embedding_dimension().
    # 4. Return the model. lru_cache guarantees one load per process, so
    #    Streamlit reruns do not reload it.
    #
    # EDGE CASES:
    # - No internet during the demo -> download the model BEFORE the demo by
    #   running `python -m rag.pipeline --build-index` once on the demo laptop.
    # - Wrong model name -> EmbeddingError (not a raw OSError in the UI).
    #
    # ACCEPTANCE CRITERIA:
    # Two calls with the same name return the SAME object (`is`).
    raise NotImplementedError("Partner 1 must implement load_embedding_model().")


def get_embedding_dimension(model_name: str) -> int:
    """Return the vector size of the model (e.g. 384 for e5-small)."""
    # TODO(PARTNER 1):
    # return int(load_embedding_model(model_name).get_sentence_embedding_dimension())
    raise NotImplementedError("Partner 1 must implement get_embedding_dimension().")


def embed_texts(
    texts: list[str],
    kind: TextKind,
    model_name: str,
    batch_size: int = 32,
) -> np.ndarray:
    """Embed a list of texts.

    Args:
        texts: Chunk texts (kind="passage") or a single-item list with the
            user question (kind="query").
        kind: "query" or "passage" — controls the E5 prefix.
        model_name: settings.embedding_model.
        batch_size: settings.embedding_batch_size.

    Returns:
        float32 array of shape (len(texts), dim), every row L2-normalized.

    Raises:
        ValueError: If texts is empty, contains a non-string, or contains an
            empty/whitespace-only string, or kind is invalid.
        EmbeddingError: If the model fails or returns vectors with the wrong
            shape, NaN, or zero norm.
    """
    # TODO(PARTNER 1):
    # 1. Validate: texts is a non-empty list of non-empty strings;
    #    kind in ("query", "passage"). Report the index of the first bad item.
    # 2. model = load_embedding_model(model_name)
    # 3. prefix = _prefix_for(model_name, kind); inputs = [prefix + t for t in texts]
    # 4. vectors = model.encode(inputs, batch_size=batch_size,
    #        normalize_embeddings=True, convert_to_numpy=True,
    #        show_progress_bar=(len(inputs) > 100))
    #    Wrap in try/except -> EmbeddingError.
    # 5. vectors = np.asarray(vectors, dtype=np.float32)
    # 6. Validate shape == (len(texts), get_embedding_dimension(model_name)).
    # 7. Validate np.isfinite(vectors).all(); and that every row norm is
    #    within 1e-3 of 1.0 (re-normalize with np.linalg.norm if not; a zero
    #    norm row -> EmbeddingError).
    # 8. Return vectors.
    #
    # PERFORMANCE NOTE: ~1,500 chunks with e5-small on a laptop CPU takes on
    # the order of a few minutes. Build the index ONCE (pipeline --build-index)
    # and never embed passages inside the Streamlit request path.
    #
    # EDGE CASES:
    # - Empty list / empty string      -> ValueError (caller bug, not system error).
    # - Mixed Arabic/English text      -> fine for multilingual models.
    # - Very long text (> 512 tokens)  -> silently truncated by the model; this
    #   is why chunk_size stays ~900 characters.
    #
    # ACCEPTANCE CRITERIA:
    # embed_texts(["ما هي متطلبات التخرج؟"], "query", name).shape == (1, dim)
    # and the row norm is 1.0 ± 1e-3.
    raise NotImplementedError("Partner 1 must implement embed_texts().")


def make_embed_fn(model_name: str, batch_size: int = 32) -> EmbedFn:
    """Bind model settings into an EmbedFn for dependency injection (implemented)."""

    def _embed(texts: list[str], kind: TextKind) -> np.ndarray:
        return embed_texts(texts, kind, model_name, batch_size)

    return _embed
