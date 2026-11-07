"""
File: tests/test_pipeline.py

OWNER: Partner 2 — Full-Stack & Integration Engineer

PURPOSE:
Application-level tests:
- the integration contract (rag/schemas.validate_response_dict),
- configuration loading and validation (config.py),
- answer_question() in mock mode,
- strict separation of invalid input / insufficient evidence / system error,
- error mapping in real mode with mocked internals (no API calls, no index).

Most tests here exercise IMPLEMENTED infrastructure and must pass now.
Tests marked `pending` wait for Partner 1's real pipeline.

Run:  pytest tests/test_pipeline.py -v
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

import config
from config import ConfigurationError, Settings, load_settings
from rag import pipeline
from rag.schemas import (
    REQUIRED_RESPONSE_KEYS,
    STATUS_ANSWERED,
    STATUS_INSUFFICIENT_EVIDENCE,
    STATUS_INVALID_INPUT,
    STATUS_SYSTEM_ERROR,
    LLMServiceError,
    RAGResponse,
    validate_response_dict,
)

pending = pytest.mark.xfail(
    raises=NotImplementedError, reason="Pending Partner 1 implementation", strict=False
)

MOCK = Settings(rag_mode="mock")
REAL = Settings(rag_mode="real", llm_api_key="test-key-not-real")


# --------------------------------------------------------------------------
# Contract validator
# --------------------------------------------------------------------------
def _ok() -> dict:
    return {
        "answer": "Grounded answer [1]",
        "sources": [{"document": "BZU.pdf", "page": 570, "excerpt": "..."}],
        "supported": True,
        "status": STATUS_ANSWERED,
        "error": None,
        "is_mock": False,
    }


def test_contract_accepts_valid_response():
    validate_response_dict(_ok())


@pytest.mark.parametrize(
    "mutate",
    [
        lambda r: r.pop("sources"),
        lambda r: r.update(sources=None),
        lambda r: r.update(supported="yes"),
        lambda r: r.update(status="ok"),
        lambda r: r.update(answer="  "),
        lambda r: r.update(sources=[{"document": "BZU.pdf", "page": 0}]),
        lambda r: r.update(sources=[{"document": "BZU.pdf", "page": "12"}]),
        lambda r: r.update(sources=[{"document": "", "page": 1}]),
        lambda r: r.update(sources=[]),  # answered without sources
        lambda r: r.update(supported=False),  # answered but not supported
        lambda r: r.update(error="boom"),  # error on a non-error status
        lambda r: r.update(status=STATUS_INSUFFICIENT_EVIDENCE, supported=False),  # refusal with sources
    ],
)
def test_contract_rejects_invalid_responses(mutate):
    r = _ok()
    mutate(r)
    with pytest.raises(ValueError):
        validate_response_dict(r)


def test_rag_response_to_dict_has_all_keys():
    d = RAGResponse(answer="x").to_dict()
    assert set(REQUIRED_RESPONSE_KEYS) == set(d)


# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------
@pytest.fixture
def clean_env(monkeypatch, tmp_path):
    for key in list(os.environ):
        if key in {
            "RAG_MODE", "TOP_K", "CHUNK_SIZE", "CHUNK_OVERLAP", "LLM_API_KEY", "MIN_SIMILARITY",
            "PDF_EXTRACTOR", "DOCS_DIR", "INDEX_DIR", "LLM_BASE_URL", "LLM_MODEL",
        }:
            monkeypatch.delenv(key, raising=False)
    return tmp_path / "no.env"  # non-existent .env file -> only os.environ is used


def test_config_defaults_to_mock(clean_env):
    s = load_settings(clean_env)
    assert s.rag_mode == "mock"
    assert s.top_k >= 1 and s.chunk_overlap < s.chunk_size


@pytest.mark.parametrize(
    "key,value",
    [("TOP_K", "five"), ("TOP_K", "0"), ("RAG_MODE", "prod"), ("PDF_EXTRACTOR", "ocr"), ("MIN_SIMILARITY", "2")],
)
def test_config_rejects_invalid_values(clean_env, monkeypatch, key, value):
    monkeypatch.setenv(key, value)
    with pytest.raises(ConfigurationError) as info:
        load_settings(clean_env)
    assert key in str(info.value)


def test_config_rejects_overlap_not_smaller_than_size(clean_env, monkeypatch):
    monkeypatch.setenv("CHUNK_SIZE", "500")
    monkeypatch.setenv("CHUNK_OVERLAP", "500")
    with pytest.raises(ConfigurationError):
        load_settings(clean_env)


def test_config_real_mode_requires_api_key(clean_env, monkeypatch):
    monkeypatch.setenv("RAG_MODE", "real")
    with pytest.raises(ConfigurationError) as info:
        load_settings(clean_env)
    assert "LLM_API_KEY" in str(info.value)


def test_secrets_never_appear_in_repr_or_redacted(clean_env, monkeypatch):
    secret = "sk-THIS-SHOULD-NEVER-BE-PRINTED"
    monkeypatch.setenv("LLM_API_KEY", secret)
    s = load_settings(clean_env)
    assert secret not in repr(s)
    assert secret not in str(s.redacted())
    assert s.redacted()["llm_api_key"] == "***set***"


def test_relative_paths_resolve_against_project_root(clean_env, monkeypatch):
    monkeypatch.setenv("DOCS_DIR", "data/university_docs")
    s = load_settings(clean_env)
    assert s.docs_dir == (config.PROJECT_ROOT / "data" / "university_docs").resolve()


# --------------------------------------------------------------------------
# Input validation
# --------------------------------------------------------------------------
@pytest.mark.parametrize("bad", ["", "   ", "\n\t", "???", "12345", None, 42, "x" * 1001])
def test_invalid_input_is_reported_as_invalid_input(bad):
    r = pipeline.answer_question(bad, settings=MOCK)
    validate_response_dict(r)
    assert r["status"] == STATUS_INVALID_INPUT
    assert r["supported"] is False and r["sources"] == [] and r["error"] is None


def test_validate_question_collapses_whitespace():
    clean, problem = pipeline.validate_question("  How   many\nhours?  ")
    assert problem is None and clean == "How many hours?"


# --------------------------------------------------------------------------
# Mock mode
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "question", ["How many credit hours are required?", "ما هي متطلبات التخرج؟"]
)
def test_mock_answer_follows_contract_and_is_labeled(question):
    r = pipeline.answer_question(question, settings=MOCK)
    validate_response_dict(r)
    assert r["status"] == STATUS_ANSWERED and r["supported"] is True
    assert r["is_mock"] is True
    assert r["answer"].startswith("[MOCK]")
    assert all(s["document"] == "MOCK_DOCUMENT.pdf" for s in r["sources"])


def test_mock_unsupported_trigger():
    r = pipeline.answer_question("What is the cafeteria menu? #unsupported", settings=MOCK)
    validate_response_dict(r)
    assert r["status"] == STATUS_INSUFFICIENT_EVIDENCE
    assert r["supported"] is False and r["sources"] == []


def test_mock_error_trigger():
    r = pipeline.answer_question("trigger #error please", settings=MOCK)
    validate_response_dict(r)
    assert r["status"] == STATUS_SYSTEM_ERROR and r["error"]


# --------------------------------------------------------------------------
# Real mode — error mapping with mocked internals (no network, no index)
# --------------------------------------------------------------------------
def test_llm_failure_becomes_system_error_not_refusal(monkeypatch):
    def boom(question, settings):
        raise LLMServiceError("LLM request timed out")

    monkeypatch.setattr(pipeline, "_answer_real", boom)
    r = pipeline.answer_question("How many credit hours?", settings=REAL)
    validate_response_dict(r)
    assert r["status"] == STATUS_SYSTEM_ERROR
    assert "LLMServiceError" in r["error"] and "timed out" in r["error"]
    assert r["status"] != STATUS_INSUFFICIENT_EVIDENCE


def test_unknown_exception_details_are_hidden(monkeypatch):
    def boom(question, settings):
        raise RuntimeError("Authorization: Bearer sk-secret-123")

    monkeypatch.setattr(pipeline, "_answer_real", boom)
    r = pipeline.answer_question("How many credit hours?", settings=REAL)
    assert r["status"] == STATUS_SYSTEM_ERROR
    assert "sk-secret-123" not in r["error"] and "sk-secret-123" not in r["answer"]


def test_contract_violation_from_real_path_is_caught(monkeypatch):
    # An "answered" response without sources breaks the contract -> system_error.
    monkeypatch.setattr(
        pipeline,
        "_answer_real",
        lambda q, s: RAGResponse(answer="made up", supported=True, status=STATUS_ANSWERED),
    )
    r = pipeline.answer_question("How many credit hours?", settings=REAL)
    validate_response_dict(r)
    assert r["status"] == STATUS_SYSTEM_ERROR


def test_real_mode_not_implemented_is_reported_cleanly():
    """Until Partner 1 finishes, real mode must still return a valid
    system_error response instead of crashing the UI."""
    r = pipeline.answer_question("How many credit hours?", settings=REAL)
    validate_response_dict(r)
    # Once implemented this will usually be answered/system_error (no index); both are valid.
    assert r["status"] in {STATUS_SYSTEM_ERROR, STATUS_ANSWERED, STATUS_INSUFFICIENT_EVIDENCE}


@pending
def test_real_mode_empty_retrieval_returns_refusal_without_llm(monkeypatch):
    """When retrieval finds nothing, the pipeline must refuse and must NOT call the LLM."""
    import rag.generator as generator
    import rag.retriever as retriever

    monkeypatch.setattr(pipeline, "get_resources", lambda s: {"store": None, "embed_fn": None, "doc_priority": {}})
    monkeypatch.setattr(retriever, "retrieve", lambda *a, **k: [])
    monkeypatch.setattr(retriever, "detect_language", lambda q: "en")

    def must_not_call(*a, **k):
        raise AssertionError("LLM must not be called when retrieval is empty")

    monkeypatch.setattr(generator, "call_llm", must_not_call)
    r = pipeline._answer_real("What is the weather tomorrow?", REAL).to_dict()
    validate_response_dict(r)
    assert r["status"] == STATUS_INSUFFICIENT_EVIDENCE


# --------------------------------------------------------------------------
# Live end-to-end (opt-in: needs API key + built index). Run with:
#   RUN_LIVE_TESTS=1 pytest tests/test_pipeline.py -k live -v
# --------------------------------------------------------------------------
live = pytest.mark.skipif(os.getenv("RUN_LIVE_TESTS") != "1", reason="set RUN_LIVE_TESTS=1 to run")


@live
def test_live_answer_cites_study_plan():
    settings = config.override_settings(rag_mode="real")
    r = pipeline.answer_question(
        "How many credit hours are required to graduate in Computer Engineering?", settings
    )
    validate_response_dict(r)
    assert r["status"] == STATUS_ANSWERED, r
    assert any(Path(s["document"]).name.startswith("1_Computer_Engineering") for s in r["sources"])


@live
def test_live_out_of_scope_is_refused():
    settings = config.override_settings(rag_mode="real")
    r = pipeline.answer_question("Who won the 2022 FIFA World Cup?", settings)
    validate_response_dict(r)
    assert r["status"] == STATUS_INSUFFICIENT_EVIDENCE, r
