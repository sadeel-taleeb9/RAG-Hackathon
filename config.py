"""
File: config.py

OWNER: Partner 2 — Full-Stack & Integration Engineer

PURPOSE:
Centralized, validated configuration for the whole project. Every tunable
value (paths, model names, chunk size, Top-K, thresholds, LLM settings,
mock/real mode) is read here from environment variables (.env) and nowhere
else. Other modules call get_settings(); they never call os.getenv().

DEPENDENCIES:
- python-dotenv
- Python standard library (dataclasses, functools, os, pathlib)
- MUST NOT import the rag package (keeps the import graph acyclic:
  config.py <- rag/* <- app.py).

EXPECTED OUTPUT:
A frozen Settings object. Invalid configuration raises ConfigurationError
with a message that names the variable and the allowed values, and that
NEVER contains a secret value.

STATUS:
The loader and validation below are IMPLEMENTED as minimal infrastructure so
that mock mode runs from minute 10. The TODO(PARTNER 2) blocks are the
remaining configuration work.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT: Path = Path(__file__).resolve().parent

VALID_RAG_MODES = ("mock", "real")
VALID_PDF_EXTRACTORS = ("pymupdf", "pypdf")


class ConfigurationError(Exception):
    """Raised when configuration is missing or invalid.

    The message must name the variable and the expected format, and must
    never include the value of a secret (API keys).
    """


@dataclass(frozen=True)
class Settings:
    # --- Mode -------------------------------------------------------------
    rag_mode: str = "mock"

    # --- Paths (always absolute, cross-platform pathlib objects) ----------
    docs_dir: Path = PROJECT_ROOT / "data" / "university_docs"
    index_dir: Path = PROJECT_ROOT / "storage" / "index"

    # --- Ingestion / chunking --------------------------------------------
    pdf_extractor: str = "pymupdf"
    chunk_size: int = 900          # characters, not tokens
    chunk_overlap: int = 150       # characters

    # --- Embeddings -------------------------------------------------------
    embedding_model: str = "intfloat/multilingual-e5-small"
    embedding_batch_size: int = 32

    # --- Retrieval --------------------------------------------------------
    top_k: int = 5
    min_similarity: float = 0.80   # PLACEHOLDER: calibrate (see rag/retriever.py)

    # --- LLM (any OpenAI-compatible endpoint) -----------------------------
    llm_api_key: str = field(default="", repr=False)  # repr=False: never printed
    llm_base_url: str = ""         # "" = official OpenAI endpoint
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 600
    llm_timeout_seconds: float = 30.0
    llm_max_retries: int = 2

    # --- Logging ----------------------------------------------------------
    log_level: str = "INFO"

    def redacted(self) -> dict[str, object]:
        """Return settings as a dict that is safe to log or show in the UI."""
        data = {k: getattr(self, k) for k in self.__dataclass_fields__}
        data["llm_api_key"] = "***set***" if self.llm_api_key else "***missing***"
        return {k: str(v) for k, v in data.items()}


def _get_str(name: str, default: str) -> str:
    value = os.getenv(name)
    return default if value is None or value.strip() == "" else value.strip()


def _get_int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer, got {raw!r}.") from exc
    if not minimum <= value <= maximum:
        raise ConfigurationError(f"{name} must be between {minimum} and {maximum}, got {value}.")
    return value


def _get_float(name: str, default: float, minimum: float, maximum: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be a number, got {raw!r}.") from exc
    if not minimum <= value <= maximum:
        raise ConfigurationError(f"{name} must be between {minimum} and {maximum}, got {value}.")
    return value


def _resolve_path(name: str, default: Path) -> Path:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    path = Path(raw.strip()).expanduser()
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def load_settings(env_file: Path | None = None) -> Settings:
    """Read .env + environment variables and return validated Settings.

    Args:
        env_file: Optional explicit .env path (tests pass a temp file).
            Defaults to PROJECT_ROOT/.env. A missing .env is NOT an error:
            defaults give a working mock mode.

    Returns:
        A frozen, validated Settings instance.

    Raises:
        ConfigurationError: For any invalid value, or for missing values that
            the selected mode requires (e.g. LLM_API_KEY in real mode).
    """
    load_dotenv(env_file or PROJECT_ROOT / ".env", override=False)

    rag_mode = _get_str("RAG_MODE", "mock").lower()
    if rag_mode not in VALID_RAG_MODES:
        raise ConfigurationError(f"RAG_MODE must be one of {VALID_RAG_MODES}, got {rag_mode!r}.")

    pdf_extractor = _get_str("PDF_EXTRACTOR", "pymupdf").lower()
    if pdf_extractor not in VALID_PDF_EXTRACTORS:
        raise ConfigurationError(
            f"PDF_EXTRACTOR must be one of {VALID_PDF_EXTRACTORS}, got {pdf_extractor!r}."
        )

    chunk_size = _get_int("CHUNK_SIZE", 900, 200, 4000)
    chunk_overlap = _get_int("CHUNK_OVERLAP", 150, 0, 2000)
    if chunk_overlap >= chunk_size:
        raise ConfigurationError(
            f"CHUNK_OVERLAP ({chunk_overlap}) must be smaller than CHUNK_SIZE ({chunk_size})."
        )

    settings = Settings(
        rag_mode=rag_mode,
        docs_dir=_resolve_path("DOCS_DIR", Settings.docs_dir),
        index_dir=_resolve_path("INDEX_DIR", Settings.index_dir),
        pdf_extractor=pdf_extractor,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        embedding_model=_get_str("EMBEDDING_MODEL", Settings.embedding_model),
        embedding_batch_size=_get_int("EMBEDDING_BATCH_SIZE", 32, 1, 512),
        top_k=_get_int("TOP_K", 5, 1, 20),
        min_similarity=_get_float("MIN_SIMILARITY", 0.80, -1.0, 1.0),
        llm_api_key=_get_str("LLM_API_KEY", ""),
        llm_base_url=_get_str("LLM_BASE_URL", ""),
        llm_model=_get_str("LLM_MODEL", Settings.llm_model),
        llm_temperature=_get_float("LLM_TEMPERATURE", 0.0, 0.0, 2.0),
        llm_max_tokens=_get_int("LLM_MAX_TOKENS", 600, 50, 4000),
        llm_timeout_seconds=_get_float("LLM_TIMEOUT_SECONDS", 30.0, 1.0, 300.0),
        llm_max_retries=_get_int("LLM_MAX_RETRIES", 2, 0, 5),
        log_level=_get_str("LOG_LEVEL", "INFO").upper(),
    )

    if settings.rag_mode == "real":
        _validate_real_mode(settings)

    # TODO(PARTNER 2):
    # 1. Confirm with Partner 1 at minute 10 that the defaults above
    #    (CHUNK_SIZE=900, CHUNK_OVERLAP=150, TOP_K=5, embedding model) are the
    #    starting values. Change them ONLY in .env, not in code, during tuning.
    # 2. After Partner 1 calibrates MIN_SIMILARITY (rag/retriever.py), copy
    #    the calibrated value into .env.example with a one-line comment
    #    stating how it was measured (e.g. "midpoint of in-scope vs
    #    out-of-scope top-1 scores on tests/questions.json").
    # 3. Validate LOG_LEVEL against {"DEBUG","INFO","WARNING","ERROR"} and
    #    raise ConfigurationError otherwise.
    # 4. Make sure nothing in the code base ever logs `settings` directly.
    #    Always log settings.redacted(). (Settings.__repr__ already hides
    #    the key because of repr=False — keep it that way.)
    #
    # EDGE CASES:
    # - .env missing entirely            -> defaults, mock mode, no crash.
    # - TOP_K="five"                     -> ConfigurationError naming TOP_K.
    # - CHUNK_OVERLAP >= CHUNK_SIZE      -> ConfigurationError (implemented).
    # - Relative DOCS_DIR on Windows     -> resolved against PROJECT_ROOT.
    #
    # ACCEPTANCE CRITERIA:
    # `python -c "from config import get_settings; print(get_settings().redacted())"`
    # prints every setting and shows the API key only as ***set*** / ***missing***.

    return settings


def _validate_real_mode(settings: Settings) -> None:
    """Checks that only matter when the real RAG pipeline is used."""
    if not settings.llm_api_key or settings.llm_api_key.startswith("your-"):
        raise ConfigurationError(
            "LLM_API_KEY is missing. Copy .env.example to .env and set LLM_API_KEY, "
            "or set RAG_MODE=mock to run the UI without the RAG pipeline."
        )
    if not settings.docs_dir.is_dir():
        raise ConfigurationError(f"DOCS_DIR does not exist: {settings.docs_dir}")
    # TODO(PARTNER 2):
    # 1. If settings.llm_base_url is set, check it starts with "http://" or
    #    "https://"; otherwise raise ConfigurationError naming LLM_BASE_URL.
    # 2. Do NOT check here that the index exists — a missing index is a
    #    runtime state reported by rag.pipeline as IndexNotReadyError with the
    #    exact rebuild command, not a configuration error.


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached accessor used by every module. Loaded once per process."""
    return load_settings()


def override_settings(**changes: object) -> Settings:
    """Return a copy of the current settings with some fields replaced.

    Intended for tests and for evaluation sweeps (e.g. TOP_K=3 vs 5), e.g.:
        s = override_settings(top_k=3)
    """
    return replace(get_settings(), **changes)  # type: ignore[arg-type]
