"""
File: app.py

OWNER: Partner 2 — Full-Stack & Integration Engineer

PURPOSE:
Streamlit chat interface for the Smart Academic Advisor. Accepts Arabic and
English questions, calls rag.pipeline.answer_question(), and renders the
answer, its sources (document + page + excerpt + one-page PDF download),
refusals, and technical errors — each visually distinct.

DEPENDENCIES:
- streamlit
- html, json, logging, re, threading, time, io, pathlib (stdlib)
- config (get_settings, ConfigurationError, PROJECT_ROOT)
- rag.pipeline (answer_question) — the ONLY RAG function used here
- rag.schemas (status constants, validate_response_dict)
- pymupdf / pypdf — OPTIONAL, imported lazily and only to cut ONE cited page
  out of a PDF so a judge can verify a citation. No retrieval, prompt or
  ingestion logic lives in this file.

RUN:
    streamlit run app.py
Mock mode (default, no API key, no index needed): RAG_MODE=mock in .env.
Real mode: RAG_MODE=real + LLM_API_KEY + a built index.

ERROR-HANDLING PRINCIPLES (every case below is handled, none shows a traceback):
- Broken configuration (.env)                -> red banner, app stops cleanly.
- RAG package fails to import (P1 mid-edit)  -> red banner with the error, app stops.
- answer_question() raises (contract bug)    -> converted to a local system_error.
- Malformed response dict                    -> "Integration contract mismatch" box.
- One corrupted message in the history       -> that message shows a warning; the
                                                rest of the chat still renders.
- Missing / unsafe / unreadable source PDF   -> caption instead of a download button.
- Missing / corrupted manifest or index meta -> sidebar shows the problem.
- Feedback / stats file cannot be written    -> toast warning; chat unaffected.
- Double Enter / double click                -> duplicate ignored for 3 seconds.
- A new question while one is running        -> question and answer are stored
                                                together, so history never has a
                                                question without its answer.
"""

from __future__ import annotations

import html
import io
import json
import logging
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import streamlit as st

from config import PROJECT_ROOT, ConfigurationError, get_settings
from rag.schemas import (
    STATUS_ANSWERED,
    STATUS_INSUFFICIENT_EVIDENCE,
    STATUS_INVALID_INPUT,
    STATUS_SYSTEM_ERROR,
    validate_response_dict,
)

# The RAG package is owned by Partner 1 and changes all day. If it cannot be
# imported (syntax error, missing dependency) the UI must explain why instead
# of crashing with a raw traceback.
try:
    from rag.pipeline import answer_question

    _PIPELINE_IMPORT_ERROR: str | None = None
except Exception as _exc:  # noqa: BLE001
    answer_question = None  # type: ignore[assignment]
    _PIPELINE_IMPORT_ERROR = f"{type(_exc).__name__}: {_exc}"

logger = logging.getLogger(__name__)

APP_TITLE = "Smart Academic Advisor — Birzeit University"
APP_SUBTITLE = (
    "Ask about study plans, prerequisites, credit hours and academic regulations, "
    "in Arabic or English. Every answer cites the official document and page."
)
AI_NOTE = "Built with AI assistance — see the README for the AI usage disclosure."

MAX_QUESTION_CHARS = 1000
MAX_EXCERPT_CHARS = 300
DUPLICATE_WINDOW_SECONDS = 3.0
MAX_FULL_PDF_DOWNLOAD_BYTES = 5 * 1024 * 1024  # bigger files: one-page export only

ENABLE_FEEDBACK = True          # 👍/👎 per answer -> storage/feedback.jsonl
ENABLE_QUESTION_STATS = True    # anonymous "most asked" counter -> storage/question_stats.json
STORAGE_DIR = PROJECT_ROOT / "storage"
FEEDBACK_FILE = STORAGE_DIR / "feedback.jsonl"
STATS_FILE = STORAGE_DIR / "question_stats.json"
MOCK_DOCUMENT_PREFIX = "MOCK_"

_ARABIC_LETTER = re.compile(r"[؀-ۿݐ-ݿࢠ-ࣿ]")
_LATIN_LETTER = re.compile(r"[A-Za-z]")
_FILE_LOCK = threading.Lock()  # Streamlit sessions are threads of one process

# Example questions (VERIFIED/pre-filled cases from tests/questions.json:
# Q01 English, Q05 Arabic, Q04 English, Q16 out of scope).
# Keep in sync with Partner 3 when the final verified list is ready.
EXAMPLE_QUESTIONS: list[str] = [
    "How many credit hours are required to graduate in Computer Engineering?",
    "ما هو المتطلب السابق لمساق مشروع التخرج ENCS5300؟",
    "What is the prerequisite of COMP433 Software Engineering?",
    "What is the weather in Ramallah tomorrow?",
]

_CUSTOM_CSS = """
<style>
/* Long course codes / file names must wrap on small screens (~400 px). */
[data-testid="stChatMessage"] div[dir] { overflow-wrap: anywhere; word-break: break-word; }
[data-testid="stChatMessage"] code { white-space: pre-wrap; word-break: break-all; }
/* Example buttons: full width and left/right text that wraps instead of overflowing. */
section[data-testid="stSidebar"] button p { white-space: normal; text-align: start; }
</style>
"""


# ---------------------------------------------------------------------------
# Pure helpers (no Streamlit calls)
# ---------------------------------------------------------------------------
def text_direction(text: Any) -> str:
    """Return "rtl" when Arabic letters dominate, else "ltr". Never raises."""
    text = "" if text is None else str(text)
    arabic = len(_ARABIC_LETTER.findall(text))
    latin = len(_LATIN_LETTER.findall(text))
    return "rtl" if arabic > 0 and arabic >= latin * 0.5 else "ltr"


def to_safe_html(text: Any) -> str:
    """Escape user/LLM text and wrap it with the right direction.

    ALWAYS escape before unsafe_allow_html: answers contain LLM output and
    questions contain user input; unescaped HTML would be an injection hole.
    """
    text = "" if text is None else str(text)
    direction = text_direction(text)
    body = html.escape(text).replace("\n", "<br>")
    align = "right" if direction == "rtl" else "left"
    return f'<div dir="{direction}" style="text-align:{align}; line-height:1.7">{body}</div>'


def truncate(text: Any, limit: int = MAX_EXCERPT_CHARS) -> str:
    """Shorten text to `limit` characters, cutting at a word boundary, adding "…"."""
    text = "" if text is None else " ".join(str(text).split())
    if len(text) <= limit:
        return text
    cut = text[:limit]
    space = cut.rfind(" ")
    if space > limit * 0.6:
        cut = cut[:space]
    return cut.rstrip() + "…"


def normalize_question(text: Any) -> str:
    """Key for duplicate detection and statistics (case/space-insensitive)."""
    return " ".join(str(text or "").split()).casefold()


def resolve_document_path(document: Any, docs_dir: Path) -> Path | None:
    """Return the PDF path for a cited document name, or None if unsafe/missing.

    The name comes from the RAG response, so it is treated as untrusted:
    only a plain "*.pdf" file name located directly inside docs_dir is allowed
    (no "..", no "/", no "\\", no absolute paths, no symlink escapes).
    """
    if not isinstance(document, str) or not document.strip():
        return None
    name = document.strip()
    if name != Path(name).name or "/" in name or "\\" in name or name in {".", ".."}:
        return None
    if not name.lower().endswith(".pdf"):
        return None
    try:
        base = docs_dir.resolve()
        candidate = (base / name).resolve()
    except (OSError, RuntimeError):
        return None
    if candidate.parent != base or not candidate.is_file():
        return None
    return candidate


def system_error_response(detail: str) -> dict[str, Any]:
    """A contract-valid system_error built locally (used when the pipeline misbehaves)."""
    return {
        "answer": (
            "Something went wrong on our side, so I could not answer. Please try again. / "
            "حدث خطأ تقني ولم أتمكن من الإجابة. يرجى المحاولة مرة أخرى."
        ),
        "sources": [],
        "supported": False,
        "status": STATUS_SYSTEM_ERROR,
        "error": detail,
        "is_mock": False,
    }


def safe_answer(question: str) -> dict[str, Any]:
    """Call the pipeline; convert ANY failure into a valid system_error dict."""
    if answer_question is None:
        return system_error_response(f"RAG pipeline could not be imported: {_PIPELINE_IMPORT_ERROR}")
    try:
        response = answer_question(question)
    except Exception as exc:  # noqa: BLE001 — contract says it never raises; be defensive
        logger.exception("answer_question raised despite the contract")
        return system_error_response(f"answer_question raised {type(exc).__name__} (contract violation)")
    if not isinstance(response, dict):
        return system_error_response(
            f"answer_question returned {type(response).__name__}, expected dict (contract violation)"
        )
    return response


# ---------------------------------------------------------------------------
# File-backed helpers (cached, all failures returned as data, never raised)
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False, max_entries=64)
def export_single_page(pdf_path: str, mtime: float, page: int) -> bytes | None:
    """Return a one-page PDF containing `page` (1-based) of `pdf_path`, or None.

    `mtime` is part of the cache key so a replaced PDF is re-read.
    Tries PyMuPDF, then pypdf. Any error -> None (the UI shows a caption).
    """
    del mtime  # cache key only
    try:
        import fitz  # PyMuPDF

        with fitz.open(pdf_path) as src:
            if src.needs_pass or not 1 <= page <= src.page_count:
                return None
            with fitz.open() as out:
                out.insert_pdf(src, from_page=page - 1, to_page=page - 1)
                return out.tobytes()
    except ImportError:
        pass
    except Exception:  # noqa: BLE001
        logger.warning("PyMuPDF page export failed for %s p%s", pdf_path, page, exc_info=True)
    try:
        from pypdf import PdfReader, PdfWriter

        reader = PdfReader(pdf_path)
        if reader.is_encrypted or not 1 <= page <= len(reader.pages):
            return None
        writer = PdfWriter()
        writer.add_page(reader.pages[page - 1])
        buffer = io.BytesIO()
        writer.write(buffer)
        return buffer.getvalue()
    except Exception:  # noqa: BLE001 — ImportError included
        logger.warning("pypdf page export failed for %s p%s", pdf_path, page, exc_info=True)
        return None


@st.cache_data(show_spinner=False, ttl=60)
def load_knowledge_base(docs_dir: str) -> dict[str, Any]:
    """Describe the documents: manifest entries + PDFs on disk + problems found."""
    base = Path(docs_dir)
    result: dict[str, Any] = {"documents": [], "problems": []}
    if not base.is_dir():
        result["problems"].append(f"Documents folder not found: {base}")
        return result

    manifest: dict[str, Any] = {}
    manifest_path = base / "manifest.json"
    if manifest_path.is_file():
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            docs = data.get("documents", {}) if isinstance(data, dict) else {}
            if isinstance(docs, dict):
                manifest = docs
            else:
                result["problems"].append("manifest.json: 'documents' is not an object")
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            result["problems"].append(f"manifest.json unreadable: {type(exc).__name__}")
    else:
        result["problems"].append("manifest.json missing")

    try:
        on_disk = sorted(p.name for p in base.iterdir() if p.is_file() and p.suffix.lower() == ".pdf")
    except OSError as exc:
        result["problems"].append(f"Cannot list documents: {type(exc).__name__}")
        on_disk = []

    for name in sorted(set(on_disk) | set(manifest)):
        meta = manifest.get(name, {}) if isinstance(manifest.get(name), dict) else {}
        result["documents"].append(
            {
                "file": name,
                "title": str(meta.get("doc_title", "") or name),
                "version": str(meta.get("doc_version", "") or "unknown version"),
                "on_disk": name in on_disk,
                "in_manifest": name in manifest,
            }
        )
    if not on_disk:
        result["problems"].append("No PDF files in the documents folder")
    return result


def read_index_health(index_dir: Path) -> tuple[str, str]:
    """Return (level, message) with level in {"ok", "warning", "error"}.

    Reads index_meta.json directly — does NOT import faiss.
    """
    required = ["faiss.index", "chunks.jsonl", "index_meta.json"]
    try:
        missing = [f for f in required if not (index_dir / f).is_file()]
    except OSError as exc:
        return "error", f"Cannot read the index folder ({type(exc).__name__})."
    if missing:
        return "error", "Index missing — run `python -m rag.pipeline --build-index`."
    try:
        meta = json.loads((index_dir / "index_meta.json").read_text(encoding="utf-8"))
        chunks = int(meta.get("num_chunks", 0))
        model = str(meta.get("embedding_model", "?"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError, AttributeError):
        return "error", "Index metadata is corrupted — rebuild the index."
    if chunks <= 0:
        return "warning", "Index is empty — rebuild the index."
    return "ok", f"Index ready: {chunks} chunks ({model})."


def _atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def record_feedback(question: str, response: dict[str, Any], rating: str) -> bool:
    """Append one feedback line (no personal data). Returns False on failure."""
    row = {
        "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "question": question,
        "status": response.get("status"),
        "sources": [
            {"document": s.get("document"), "page": s.get("page")}
            for s in response.get("sources", [])
            if isinstance(s, dict)
        ],
        "is_mock": bool(response.get("is_mock")),
        "rating": rating,
    }
    try:
        with _FILE_LOCK:
            FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
            with FEEDBACK_FILE.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        return True
    except OSError:
        logger.warning("Could not write feedback", exc_info=True)
        return False


def load_question_stats() -> dict[str, dict[str, Any]]:
    """{normalized_question: {"text": str, "count": int}}; {} on any problem."""
    try:
        data = json.loads(STATS_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        logger.warning("question_stats.json unreadable; starting fresh")
        return {}
    if not isinstance(data, dict):
        return {}
    return {
        k: v
        for k, v in data.items()
        if isinstance(v, dict) and isinstance(v.get("count"), int) and isinstance(v.get("text"), str)
    }


def record_question(question: str) -> bool:
    """Increment the anonymous counter for this question. Returns False on failure."""
    key = normalize_question(question)
    if not key:
        return False
    try:
        with _FILE_LOCK:
            stats = load_question_stats()
            entry = stats.get(key, {"text": " ".join(question.split()), "count": 0})
            entry["count"] += 1
            stats[key] = entry
            _atomic_write_json(STATS_FILE, stats)
        return True
    except OSError:
        logger.warning("Could not write question stats", exc_info=True)
        return False


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def render_sources(sources: list[dict[str, Any]], msg_index: int, docs_dir: Path, expanded: bool) -> None:
    """Show numbered sources with document name, page, excerpt and a download."""
    if not sources:
        return
    with st.expander(f"Sources ({len(sources)})", expanded=expanded):
        for i, src in enumerate(sources, start=1):
            if not isinstance(src, dict):
                continue
            document = str(src.get("document", "unknown"))
            page = src.get("page")
            st.markdown(f"**[{i}]** `{html.escape(document)}` — page **{html.escape(str(page))}**")

            excerpt = truncate(src.get("excerpt", ""))
            if excerpt:
                st.markdown(to_safe_html(excerpt), unsafe_allow_html=True)

            if document.startswith(MOCK_DOCUMENT_PREFIX):
                st.caption("Mock source — there is no real file to open.")
                continue
            path = resolve_document_path(document, docs_dir)
            if path is None or not isinstance(page, int):
                st.caption("Source file is not available on this server.")
                continue

            try:
                mtime = path.stat().st_mtime
                size = path.stat().st_size
            except OSError:
                st.caption("Source file could not be read.")
                continue

            page_pdf = export_single_page(str(path), mtime, page)
            if page_pdf:
                st.download_button(
                    f"Download page {page} (PDF)",
                    data=page_pdf,
                    file_name=f"{path.stem}_page{page}.pdf",
                    mime="application/pdf",
                    key=f"dl::{msg_index}::{i}",
                )
            elif size <= MAX_FULL_PDF_DOWNLOAD_BYTES:
                try:
                    st.download_button(
                        f"Download {path.name}",
                        data=path.read_bytes(),
                        file_name=path.name,
                        mime="application/pdf",
                        key=f"dlfull::{msg_index}::{i}",
                    )
                except OSError:
                    st.caption("Source file could not be read.")
            else:
                st.caption(f"Open `{html.escape(path.name)}` at page {page} to verify.")


def render_feedback(msg_index: int, message: dict[str, Any], question: str) -> None:
    """👍/👎 buttons for real answers (not for mocks, refusals of bad input or errors)."""
    response = message.get("content", {})
    if not ENABLE_FEEDBACK or response.get("is_mock") or response.get("status") not in (
        STATUS_ANSWERED,
        STATUS_INSUFFICIENT_EVIDENCE,
    ):
        return
    given = message.get("feedback")
    if given:
        st.caption("Thanks for your feedback." if given != "error" else "Feedback could not be saved.")
        return
    up_col, down_col, _ = st.columns([1, 1, 6])
    rating = None
    if up_col.button("👍", key=f"fb_up::{msg_index}", help="Helpful"):
        rating = "up"
    if down_col.button("👎", key=f"fb_down::{msg_index}", help="Not helpful"):
        rating = "down"
    if rating:
        ok = record_feedback(question, response, rating)
        message["feedback"] = rating if ok else "error"
        if ok:
            st.toast("Thanks for your feedback.")
        else:
            st.toast("Feedback could not be saved (storage not writable).")


def render_response(response: Any, msg_index: int, docs_dir: Path, latest: bool) -> None:
    """Render one assistant response according to its status."""
    try:
        validate_response_dict(response)
    except ValueError as exc:
        st.error(f"Integration contract mismatch: {exc}")
        try:
            st.json(response)
        except Exception:  # noqa: BLE001 — not JSON-serializable
            st.code(repr(response)[:2000])
        return

    status = response["status"]
    if response["is_mock"]:
        st.caption("MOCK RESPONSE — simulated, not taken from university documents.")

    if status == STATUS_ANSWERED:
        st.markdown(to_safe_html(response["answer"]), unsafe_allow_html=True)
        render_sources(response["sources"], msg_index, docs_dir, expanded=latest)
    elif status == STATUS_INSUFFICIENT_EVIDENCE:
        st.info(response["answer"], icon="📄")
    elif status == STATUS_INVALID_INPUT:
        st.warning(response["answer"], icon="✏️")
    elif status == STATUS_SYSTEM_ERROR:
        st.error(response["answer"], icon="⚠️")
        if response.get("error"):
            with st.expander("Technical details"):
                st.code(str(response["error"]))


def render_sidebar(rag_mode: str, settings: Any) -> None:
    with st.sidebar:
        st.header("About")
        st.write(
            "Answers come only from official Birzeit University documents. "
            "If the documents do not contain the answer, the advisor says so."
        )
        st.write(f"Mode: **{rag_mode.upper()}**")

        if rag_mode == "real":
            level, message = read_index_health(settings.index_dir)
            {"ok": st.success, "warning": st.warning, "error": st.error}[level](message)

        st.subheader("Try a question")
        for q in EXAMPLE_QUESTIONS:
            if st.button(q, key=f"example::{q}"):
                st.session_state.pending_question = q

        if ENABLE_QUESTION_STATS:
            stats = load_question_stats()
            if stats:
                st.subheader("Most asked")
                top = sorted(stats.values(), key=lambda v: v["count"], reverse=True)[:5]
                for entry in top:
                    label = f"{truncate(entry['text'], 70)} ({entry['count']})"
                    if st.button(label, key=f"top::{normalize_question(entry['text'])}"):
                        st.session_state.pending_question = entry["text"]

        st.subheader("Knowledge base")
        kb = load_knowledge_base(str(settings.docs_dir))
        for doc in kb["documents"]:
            flags = []
            if not doc["on_disk"]:
                flags.append("file missing")
            if not doc["in_manifest"]:
                flags.append("not in manifest")
            suffix = f" — ⚠️ {', '.join(flags)}" if flags else ""
            st.markdown(f"- **{html.escape(doc['title'])}** ({html.escape(doc['version'])}){suffix}")
        for problem in kb["problems"]:
            st.warning(problem)

        if st.button("Clear conversation"):
            st.session_state.messages = []
            st.session_state.last_question = ""
            st.session_state.last_question_time = 0.0
            st.rerun()

        st.caption(AI_NOTE)


def _is_valid_message(msg: Any) -> bool:
    return (
        isinstance(msg, dict)
        and msg.get("role") in ("user", "assistant")
        and (isinstance(msg.get("content"), str) if msg.get("role") == "user" else True)
    )


def render_history(docs_dir: Path) -> None:
    """Replay the conversation. A broken message never breaks the whole page."""
    messages = st.session_state.messages
    last_assistant = max((i for i, m in enumerate(messages) if _is_valid_message(m) and m["role"] == "assistant"), default=-1)
    for idx, msg in enumerate(messages):
        if not _is_valid_message(msg):
            st.warning("A message in this conversation could not be displayed.")
            continue
        with st.chat_message(msg["role"]):
            try:
                if msg["role"] == "user":
                    st.markdown(to_safe_html(msg["content"]), unsafe_allow_html=True)
                else:
                    render_response(msg["content"], idx, docs_dir, latest=(idx == last_assistant))
                    question = messages[idx - 1]["content"] if idx > 0 and _is_valid_message(messages[idx - 1]) else ""
                    render_feedback(idx, msg, question if isinstance(question, str) else "")
            except Exception as exc:  # noqa: BLE001 — isolate one bad message
                logger.exception("Failed to render message %s", idx)
                st.warning(f"This message could not be displayed ({type(exc).__name__}).")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def _init_state() -> None:
    defaults: dict[str, Any] = {
        "messages": [],
        "pending_question": None,
        "last_question": "",
        "last_question_time": 0.0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    if not isinstance(st.session_state.messages, list):
        st.session_state.messages = []


def _is_duplicate(question: str) -> bool:
    key = normalize_question(question)
    now = time.monotonic()
    duplicate = (
        key == st.session_state.last_question
        and now - float(st.session_state.last_question_time or 0.0) < DUPLICATE_WINDOW_SECONDS
    )
    st.session_state.last_question = key
    st.session_state.last_question_time = now
    return duplicate


def main() -> None:
    st.set_page_config(page_title="Smart Academic Advisor", page_icon="🎓", layout="centered")
    st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)
    st.title(APP_TITLE)
    st.caption(APP_SUBTITLE)

    try:
        settings = get_settings()
        rag_mode = settings.rag_mode
    except ConfigurationError as exc:
        st.error(f"Configuration error: {exc}")
        st.info("Fix your .env file (see .env.example), then reload the page.")
        st.stop()
        return
    except Exception as exc:  # noqa: BLE001 — e.g. unreadable .env
        st.error(f"Could not load configuration ({type(exc).__name__}).")
        st.stop()
        return

    if _PIPELINE_IMPORT_ERROR is not None:
        st.error("The RAG pipeline could not be loaded, so questions cannot be answered.")
        with st.expander("Technical details"):
            st.code(_PIPELINE_IMPORT_ERROR)
        st.stop()
        return

    if rag_mode == "mock":
        st.warning(
            "MOCK MODE: answers are simulated for interface testing. "
            "Set RAG_MODE=real in .env to use the real RAG pipeline.",
            icon="🧪",
        )

    _init_state()
    render_sidebar(rag_mode, settings)
    render_history(settings.docs_dir)

    typed = st.chat_input("Ask an academic question… / اكتب سؤالك الأكاديمي…", max_chars=MAX_QUESTION_CHARS)
    question = typed if typed is not None else st.session_state.pending_question
    st.session_state.pending_question = None

    if question is None:
        return
    if not isinstance(question, str):
        question = str(question)
    if question.strip() and _is_duplicate(question):
        st.toast("This question was just submitted — ignoring the duplicate.")
        return

    with st.chat_message("user"):
        st.markdown(to_safe_html(question), unsafe_allow_html=True)
    with st.chat_message("assistant"):
        with st.spinner("Searching the official documents… / جارٍ البحث في الوثائق…"):
            response = safe_answer(question)

        # Store question + answer TOGETHER before rendering, so a rerun triggered
        # by a new input never leaves a question without its answer in history.
        st.session_state.messages.append({"role": "user", "content": question})
        st.session_state.messages.append({"role": "assistant", "content": response})
        idx = len(st.session_state.messages) - 1

        render_response(response, idx, settings.docs_dir, latest=True)
        render_feedback(idx, st.session_state.messages[idx], question)

    if (
        ENABLE_QUESTION_STATS
        and isinstance(response, dict)
        and not response.get("is_mock")
        and response.get("status") in (STATUS_ANSWERED, STATUS_INSUFFICIENT_EVIDENCE)
    ):
        record_question(question)  # failure only logs; never blocks the chat


# `streamlit run app.py` executes this file with __name__ == "__main__".
if __name__ == "__main__":
    main()