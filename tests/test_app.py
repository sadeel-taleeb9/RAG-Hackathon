"""
File: tests/test_app.py

OWNER: Partner 2 — Full-Stack & Integration Engineer

PURPOSE:
Tests for the pure / file-backed helpers in app.py (no browser needed):
RTL detection, HTML escaping, excerpt truncation, safe document paths,
pipeline failure conversion, index health, knowledge base, stats/feedback files.

Skipped automatically if streamlit is not installed.
Run:  pytest tests/test_app.py -v
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
import app  # noqa: E402

from rag.schemas import STATUS_SYSTEM_ERROR, validate_response_dict  # noqa: E402

DOCS = Path(__file__).resolve().parent.parent / "data" / "university_docs"
PLAN = "1_Computer_Engineering_4_YEAR_PLAN_APRIL_25_2026.pdf"


@pytest.mark.parametrize(
    "text,expected",
    [
        ("ما هو المتطلب السابق لمساق ENCS5300؟", "rtl"),
        ("How many credit hours?", "ltr"),
        ("", "ltr"),
        (None, "ltr"),
        (12345, "ltr"),
    ],
)
def test_text_direction(text, expected):
    assert app.text_direction(text) == expected


def test_to_safe_html_escapes_html():
    out = app.to_safe_html('<script>alert("x")</script>\nline2')
    assert "<script>" not in out and "&lt;script&gt;" in out and "<br>" in out


def test_truncate():
    assert app.truncate("short") == "short"
    long = "word " * 200
    out = app.truncate(long, 50)
    assert len(out) <= 51 and out.endswith("…")
    assert app.truncate(None) == ""


@pytest.mark.parametrize(
    "name,ok",
    [
        (PLAN, True),
        ("BZU.pdf", True),
        ("../app.py", False),
        ("../../etc/passwd.pdf", False),
        ("/etc/passwd", False),
        ("sub/BZU.pdf", False),
        ("..\\BZU.pdf", False),
        ("missing.pdf", False),
        ("README.md", False),
        ("", False),
        (None, False),
        (42, False),
    ],
)
def test_resolve_document_path_is_safe(name, ok):
    assert (app.resolve_document_path(name, DOCS) is not None) is ok


def test_safe_answer_converts_exceptions(monkeypatch):
    def boom(q):
        raise RuntimeError("Bearer sk-secret")

    monkeypatch.setattr(app, "answer_question", boom)
    r = app.safe_answer("q")
    validate_response_dict(r)
    assert r["status"] == STATUS_SYSTEM_ERROR and "sk-secret" not in r["error"]


def test_safe_answer_rejects_non_dict(monkeypatch):
    monkeypatch.setattr(app, "answer_question", lambda q: ["not", "a", "dict"])
    r = app.safe_answer("q")
    validate_response_dict(r)
    assert r["status"] == STATUS_SYSTEM_ERROR


def test_safe_answer_when_pipeline_import_failed(monkeypatch):
    monkeypatch.setattr(app, "answer_question", None)
    monkeypatch.setattr(app, "_PIPELINE_IMPORT_ERROR", "SyntaxError: boom")
    r = app.safe_answer("q")
    validate_response_dict(r)
    assert "SyntaxError" in r["error"]


def test_index_health(tmp_path):
    assert app.read_index_health(tmp_path)[0] == "error"
    for f in ("faiss.index", "chunks.jsonl"):
        (tmp_path / f).write_text("x")
    (tmp_path / "index_meta.json").write_text("{broken", encoding="utf-8")
    assert app.read_index_health(tmp_path)[0] == "error"
    (tmp_path / "index_meta.json").write_text('{"num_chunks": 0}', encoding="utf-8")
    assert app.read_index_health(tmp_path)[0] == "warning"
    (tmp_path / "index_meta.json").write_text('{"num_chunks": 1500, "embedding_model": "e5"}', encoding="utf-8")
    assert app.read_index_health(tmp_path) == ("ok", "Index ready: 1500 chunks (e5).")


def test_knowledge_base_lists_documents_and_problems(tmp_path):
    kb = app.load_knowledge_base(str(DOCS))
    files = {d["file"] for d in kb["documents"]}
    assert {PLAN, "BZU.pdf"} <= files
    (tmp_path / "manifest.json").write_text("{bad", encoding="utf-8")
    kb2 = app.load_knowledge_base(str(tmp_path))
    assert any("manifest.json" in p for p in kb2["problems"])
    assert any("No PDF" in p for p in kb2["problems"])


def test_question_stats_roundtrip_and_corruption(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "STATS_FILE", tmp_path / "stats.json")
    assert app.load_question_stats() == {}
    assert app.record_question("How  many hours?")
    assert app.record_question("how many HOURS?")
    stats = app.load_question_stats()
    assert list(stats.values())[0]["count"] == 2
    (tmp_path / "stats.json").write_text("{broken", encoding="utf-8")
    assert app.load_question_stats() == {}
    assert app.record_question("   ") is False


def test_feedback_written_without_crash(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "FEEDBACK_FILE", tmp_path / "fb.jsonl")
    resp = {"status": "answered", "sources": [{"document": "BZU.pdf", "page": 2}], "is_mock": False}
    assert app.record_feedback("q", resp, "up")
    row = json.loads((tmp_path / "fb.jsonl").read_text(encoding="utf-8"))
    assert row["rating"] == "up" and row["sources"] == [{"document": "BZU.pdf", "page": 2}]


def test_feedback_unwritable_returns_false(monkeypatch, tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    monkeypatch.setattr(app, "FEEDBACK_FILE", blocker / "fb.jsonl")  # parent is a file
    assert app.record_feedback("q", {"sources": []}, "down") is False


def test_export_single_page(tmp_path):
    path = DOCS / PLAN
    data = app.export_single_page(str(path), path.stat().st_mtime, 1)
    if data is None:
        pytest.skip("No PDF library installed (pymupdf/pypdf)")
    assert data.startswith(b"%PDF")
    assert app.export_single_page(str(path), path.stat().st_mtime, 9999) is None
    broken = tmp_path / "broken.pdf"
    broken.write_bytes(b"not a pdf")
    assert app.export_single_page(str(broken), 0.0, 1) is None