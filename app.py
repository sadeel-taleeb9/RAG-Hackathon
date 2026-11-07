"""
File: app.py

OWNER: Partner 2 — Full-Stack & Integration Engineer

PURPOSE:
Streamlit chat interface for the Smart Academic Advisor. Accepts Arabic and
English questions, calls rag.pipeline.answer_question(), and renders the
answer, its sources (document + page + excerpt), refusals, and technical
errors — each visually distinct.

DEPENDENCIES:
- streamlit
- html (stdlib) — escaping before any unsafe_allow_html rendering
- config (get_settings, ConfigurationError)
- rag.pipeline (answer_question) — the ONLY RAG import allowed here
- rag.schemas (status constants, validate_response_dict)

RUN:
    streamlit run app.py
Mock mode (default, no API key, no index needed): RAG_MODE=mock in .env.
Real mode: RAG_MODE=real + LLM_API_KEY + a built index.

STATUS:
A minimal, WORKING baseline is implemented so the UI runs in mock mode from
minute 10. The TODO(PARTNER 2) blocks list the remaining UI work in priority
order. Keep app.py free of RAG logic: no retrieval, no prompts, no PDF code.
"""

from __future__ import annotations

import html
import re
from typing import Any

import streamlit as st

from config import ConfigurationError, get_settings
from rag.pipeline import answer_question
from rag.schemas import (
    STATUS_ANSWERED,
    STATUS_INSUFFICIENT_EVIDENCE,
    STATUS_INVALID_INPUT,
    STATUS_SYSTEM_ERROR,
    validate_response_dict,
)

APP_TITLE = "Smart Academic Advisor — Birzeit University"
APP_SUBTITLE = (
    "Ask about study plans, prerequisites, credit hours and academic regulations, "
    "in Arabic or English. Every answer cites the official document and page."
)
_ARABIC_LETTER = re.compile(r"[؀-ۿ]")
_LATIN_LETTER = re.compile(r"[A-Za-z]")

# Example questions shown in the sidebar (taken from tests/questions.json).
# TODO(PARTNER 2): keep this list in sync with 3–4 VERIFIED questions from
# Partner 3's tests/questions.json (one Arabic, one English, one out-of-scope).
EXAMPLE_QUESTIONS: list[str] = [
    "How many credit hours are required to graduate in Computer Engineering?",
    "ما هو المتطلب السابق لمساق مشروع التخرج ENCS5300؟",
    "What is the prerequisite of COMP433 Software Engineering?",
    "What is the weather in Ramallah tomorrow?",
]


# ---------------------------------------------------------------------------
# Pure helpers (no Streamlit calls) — easy to reason about and to test.
# ---------------------------------------------------------------------------
def text_direction(text: str) -> str:
    """Return "rtl" when Arabic letters dominate, else "ltr"."""
    arabic = len(_ARABIC_LETTER.findall(text))
    latin = len(_LATIN_LETTER.findall(text))
    return "rtl" if arabic > 0 and arabic >= latin * 0.5 else "ltr"


def to_safe_html(text: str) -> str:
    """Escape user/LLM text and wrap it with the right direction.

    ALWAYS escape before unsafe_allow_html: answers contain LLM output and
    questions contain user input; unescaped HTML would be an injection hole.
    """
    direction = text_direction(text)
    body = html.escape(text).replace("\n", "<br>")
    align = "right" if direction == "rtl" else "left"
    return f'<div dir="{direction}" style="text-align:{align}; line-height:1.7">{body}</div>'


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def render_sources(sources: list[dict[str, Any]]) -> None:
    """Show numbered sources with document name, page and excerpt."""
    if not sources:
        return
    with st.expander(f"Sources ({len(sources)})", expanded=True):
        for i, src in enumerate(sources, start=1):
            st.markdown(f"**[{i}]** `{html.escape(src['document'])}` — page **{src['page']}**")
            excerpt = src.get("excerpt", "")
            if excerpt:
                st.markdown(to_safe_html(excerpt), unsafe_allow_html=True)
    # TODO(PARTNER 2):
    # 1. Make each source verifiable in one click: add a st.download_button or
    #    a link that opens data/university_docs/<document> (serve the PDF with
    #    st.download_button(data=path.read_bytes(), file_name=...)). Never build
    #    a path from the document string without checking it is a plain file
    #    name inside settings.docs_dir (no "..", no "/").
    # 2. Truncate excerpts > 300 chars with "…" (Partner 1 already limits them;
    #    this is defense in depth).


def render_response(response: dict[str, Any]) -> None:
    """Render one assistant response according to its status."""
    try:
        validate_response_dict(response)
    except ValueError as exc:
        st.error(f"Integration contract mismatch: {exc}")
        st.json(response)
        return

    status = response["status"]
    if response["is_mock"]:
        st.caption("MOCK RESPONSE — simulated, not taken from university documents.")

    if status == STATUS_ANSWERED:
        st.markdown(to_safe_html(response["answer"]), unsafe_allow_html=True)
        render_sources(response["sources"])
    elif status == STATUS_INSUFFICIENT_EVIDENCE:
        st.info(response["answer"], icon="📄")
    elif status == STATUS_INVALID_INPUT:
        st.warning(response["answer"], icon="✏️")
    elif status == STATUS_SYSTEM_ERROR:
        st.error(response["answer"], icon="⚠️")
        if response.get("error"):
            with st.expander("Technical details"):
                st.code(response["error"])


def render_sidebar(rag_mode: str) -> None:
    with st.sidebar:
        st.header("About")
        st.write(
            "Answers come only from official Birzeit University documents. "
            "If the documents do not contain the answer, the advisor says so."
        )
        st.write(f"Mode: **{rag_mode.upper()}**")
        st.subheader("Try a question")
        for q in EXAMPLE_QUESTIONS:
            if st.button(q, key=f"example::{q}"):
                st.session_state.pending_question = q
        if st.button("Clear conversation"):
            st.session_state.messages = []
            st.rerun()
        # TODO(PARTNER 2):
        # 1. Show the list of indexed documents (filename + version) from
        #    data/university_docs/manifest.json so judges see the knowledge base.
        # 2. In real mode, show an index health line: "Index ready: N chunks"
        #    or "Index missing — run python -m rag.pipeline --build-index".
        #    Read storage/index/index_meta.json directly (do not import faiss here).
        # 3. Add the AI-usage note "Built with AI assistance — see README".


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    st.set_page_config(page_title="Smart Academic Advisor", page_icon="🎓", layout="centered")
    st.title(APP_TITLE)
    st.caption(APP_SUBTITLE)

    try:
        settings = get_settings()
        rag_mode = settings.rag_mode
    except ConfigurationError as exc:
        st.error(f"Configuration error: {exc}")
        st.stop()
        return

    if rag_mode == "mock":
        st.warning(
            "MOCK MODE: answers are simulated for interface testing. "
            "Set RAG_MODE=real in .env to use the real RAG pipeline.",
            icon="🧪",
        )

    if "messages" not in st.session_state:
        st.session_state.messages = []  # list[{"role": "user"|"assistant", "content": str|dict}]
    if "pending_question" not in st.session_state:
        st.session_state.pending_question = None

    render_sidebar(rag_mode)

    # Replay chat history (Streamlit reruns the whole script on every interaction).
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "user":
                st.markdown(to_safe_html(msg["content"]), unsafe_allow_html=True)
            else:
                render_response(msg["content"])

    typed = st.chat_input("Ask an academic question… / اكتب سؤالك الأكاديمي…", max_chars=1000)
    question = typed or st.session_state.pending_question
    st.session_state.pending_question = None

    if question:
        # TODO(PARTNER 2) — duplicate submission guard:
        # 1. Keep st.session_state.last_question and last_question_time.
        # 2. If the same normalized question arrives again within 3 seconds,
        #    ignore it (double Enter / double click on an example button).
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(to_safe_html(question), unsafe_allow_html=True)
        with st.chat_message("assistant"):
            with st.spinner("Searching the official documents… / جارٍ البحث في الوثائق…"):
                response = answer_question(question)
            render_response(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

    # TODO(PARTNER 2), in priority order:
    # 1. [P1] Run `streamlit run app.py` in mock mode and click through all
    #    four states: normal question, "#unsupported", "#error", empty input
    #    (send spaces). Each must look different and never show a traceback.
    # 2. [P1] Switch to RAG_MODE=real at minute ~120 and repeat with the
    #    questions in EXAMPLE_QUESTIONS. Report contract mismatches to Partner 1
    #    with the exact message shown by render_response().
    # 3. [P1] RTL check: Arabic question + Arabic answer render right-aligned;
    #    mixed lines with course codes (ENCS5300) stay readable.
    # 4. [P2] Small screens: check the page at ~400 px width (browser dev
    #    tools). layout="centered" already avoids wide tables; keep sources in
    #    the expander, not in st.columns.
    # 5. [P2] Optional bonus features ONLY after minute 165 is safe:
    #    a) 👍/👎 feedback per answer appended to storage/feedback.jsonl
    #       (question, status, sources, rating — no personal data);
    #    b) "Most asked questions" counter in the sidebar (judging guide bonus idea
    #       for this problem).
    #
    # EDGE CASES:
    # - Question > 1000 chars -> chat_input max_chars blocks it; the pipeline
    #   also validates (invalid_input).
    # - Pipeline raises?      -> impossible by contract (answer_question never
    #   raises); render_response still guards against malformed dicts.
    # - Very slow LLM          -> spinner stays visible; timeout comes back as
    #   system_error after LLM_TIMEOUT_SECONDS.


# `streamlit run app.py` executes this file with __name__ == "__main__".
if __name__ == "__main__":
    main()
