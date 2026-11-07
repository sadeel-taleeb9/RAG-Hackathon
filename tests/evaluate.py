"""
File: tests/evaluate.py

OWNER: Partner 3 — QA, Evaluation & Business Lead

PURPOSE:
Run every case in tests/questions.json through rag.pipeline.answer_question()
and produce honest, reproducible evaluation evidence for the judges
(judging criterion "Evaluation", 5 points, and tie-breaker #2):
  - Retrieval: Precision@K and Hit@K against expected source pages.
  - Generation: must_contain / must_not_contain checks (answer correctness),
    citation faithfulness (are cited pages among the expected pages?),
    refusal correctness for out-of-scope questions.
  - Latency per question.
  - A list of failures with the reason, for docs/EVALUATION.md.

This file is NOT collected by pytest (its name does not start with "test_").

RUN (from the repository root):
    python -m tests.evaluate                       # all cases, current .env settings
    python -m tests.evaluate --only Q01,Q06        # a subset
    python -m tests.evaluate --out storage/eval_report.json

DEPENDENCIES:
- json, time, argparse, statistics, pathlib (stdlib)
- rag.pipeline.answer_question  (the ONLY RAG function this file may call)
- rag.schemas.validate_response_dict

RULES:
- NEVER fabricate or hand-edit scores. Every number in docs/EVALUATION.md and
  on the slides must come from a saved report produced by this script.
- Cases whose verification_status is TO_BE_VERIFIED are run but EXCLUDED from
  the headline metrics (reported separately), because their reference is not
  confirmed yet.
- One failing question must never stop the run.

METRIC DEFINITIONS (write these on the evaluation slide):
- Precision@K (per case) = (# returned sources whose (document, page) is in
  expected_sources) / (# returned sources), for cases with expected_sources.
  The response only exposes CITED sources, so this is "citation precision".
  If Partner 1 adds a debug option that returns all Top-K retrieved chunks,
  compute it on those instead and say so.
- Hit@K = 1 if at least one returned source is expected, else 0.
- Refusal accuracy = share of expected_behavior == "refuse" cases with status
  "insufficient_evidence".
- False refusal rate = share of expected_behavior == "answer" cases with
  status "insufficient_evidence".
- Faithfulness (automatic proxy) = answered cases that pass must_contain and
  must_not_contain AND cite an expected page. Also do a 10-minute MANUAL
  faithfulness review: for each answered case, check every sentence is
  supported by the cited page; record "supported / partially / unsupported".
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

QUESTIONS_PATH = Path(__file__).resolve().parent / "questions.json"
VALID_BEHAVIORS = {"answer", "refuse", "clarify_or_refuse"}
VALID_LANGUAGES = {"ar", "en"}


def load_cases(path: Path = QUESTIONS_PATH) -> list[dict[str, Any]]:
    """Load and validate the evaluation dataset.

    Returns:
        The list under "cases".

    Raises:
        ValueError: With the case id and field name for the first invalid case.
    """
    # TODO(PARTNER 3):
    # 1. Read with encoding="utf-8"; json.loads; on JSONDecodeError raise
    #    ValueError with line/column (a trailing comma is the usual culprit).
    # 2. cases = data["cases"]; require a list with at least 10 items.
    # 3. For each case call validate_case(case); collect ids and reject duplicates.
    # 4. Return cases.
    raise NotImplementedError("Partner 3 must implement load_cases().")


def validate_case(case: dict[str, Any]) -> None:
    """Validate one case against the schema used in questions.json.

    Required keys and types:
        id (str, unique), language ("ar"|"en"), category (str),
        question (non-empty str), expected_behavior (VALID_BEHAVIORS),
        reference_answer (str), must_contain (list[str]),
        must_not_contain (list[str]),
        expected_sources (list of {"document": str, "page": int >= 1}),
        verification_status (str), verified_by (str), notes (str).
    Extra rule: expected_behavior == "refuse" => expected_sources == [].
    """
    # TODO(PARTNER 3): implement the checks above; raise ValueError(f"{case_id}: <field> ...").
    raise NotImplementedError("Partner 3 must implement validate_case().")


def precision_at_k(returned: list[dict[str, Any]], expected: list[dict[str, Any]]) -> float | None:
    """Share of returned sources that are expected (by document + page).

    Returns:
        None when expected is empty (metric not applicable) or nothing was
        returned (report it as a miss in Hit@K instead of dividing by zero).

    Example:
        returned=[(plan,1),(BZU,570)], expected=[(plan,1)] -> 0.5
    """
    # TODO(PARTNER 3):
    # 1. expected_set = {(e["document"], e["page"]) for e in expected}
    # 2. if not expected_set or not returned: return None
    # 3. hits = sum((r["document"], r["page"]) in expected_set for r in returned)
    # 4. return hits / len(returned)
    raise NotImplementedError("Partner 3 must implement precision_at_k().")


def hit_at_k(returned: list[dict[str, Any]], expected: list[dict[str, Any]]) -> int | None:
    """1 if any returned source is expected, 0 if none, None if not applicable."""
    # TODO(PARTNER 3): implement like precision_at_k.
    raise NotImplementedError("Partner 3 must implement hit_at_k().")


def check_answer_text(answer: str, must_contain: list[str], must_not_contain: list[str]) -> list[str]:
    """Return a list of human-readable problems ([] = pass).

    Comparison is case-insensitive. Convert Arabic-Indic digits (٠-٩) to
    ASCII on BOTH sides first, so "١٣٨" matches "138".
    """
    # TODO(PARTNER 3): implement; e.g. problems.append("missing '138'").
    raise NotImplementedError("Partner 3 must implement check_answer_text().")


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    """Run one case and score it. Never raises.

    Returns a result row:
        {"id", "category", "language", "verification_status",
         "expected_behavior", "status", "supported", "latency_ms",
         "precision_at_k", "hit_at_k", "text_problems", "passed",
         "failure_reason", "answer", "sources"}
    """
    # TODO(PARTNER 3):
    # 1. from rag.pipeline import answer_question   (inside the function)
    # 2. t0 = time.perf_counter(); response = answer_question(case["question"])
    #    latency_ms = (time.perf_counter() - t0) * 1000
    #    Wrap in try/except Exception (answer_question should never raise, but
    #    the evaluator must survive anyway) -> passed=False,
    #    failure_reason="exception: <type>".
    # 3. validate_response_dict(response) in try/except -> failure_reason="contract: ...".
    # 4. If response["status"] == "system_error" -> passed=False,
    #    failure_reason="system_error: <error>" (this is NOT a model failure;
    #    fix it and re-run before reporting).
    # 5. Scoring by expected_behavior:
    #    "answer": passed = status=="answered" and hit_at_k==1 and no text problems
    #    "refuse": passed = status=="insufficient_evidence"
    #    "clarify_or_refuse": passed = status=="insufficient_evidence" or (status
    #        =="answered" and the answer asks a question, e.g. contains "?" / "؟"
    #        and names no specific course code). Mark these for MANUAL review too.
    # 6. Keep the full answer and sources in the row (needed for the manual
    #    faithfulness review and for the error-analysis slide).
    raise NotImplementedError("Partner 3 must implement evaluate_case().")


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate metrics, computed ONLY over rows whose verification_status is
    VERIFIED or PREFILLED_CONFIRM_VISUALLY or NOT_APPLICABLE (label clearly
    which ones were included).

    Returns:
        {"n_cases", "n_scored", "pass_rate", "mean_precision_at_k",
         "hit_rate", "refusal_accuracy", "false_refusal_rate",
         "system_errors", "latency_ms": {"mean", "p50", "max"},
         "by_category": {category: pass_rate}, "by_language": {...},
         "failures": [{"id", "failure_reason"}]}
    """
    # TODO(PARTNER 3):
    # 1. Ignore None values when averaging precision/hit.
    # 2. Use statistics.mean / statistics.median; guard empty lists.
    # 3. Round to 2 decimals only when printing, not in the saved JSON.
    raise NotImplementedError("Partner 3 must implement summarize().")


def main() -> None:
    """CLI: run, print a table, save a JSON report (implemented scaffolding)."""
    parser = argparse.ArgumentParser(description="Evaluate the Smart Academic Advisor.")
    parser.add_argument("--only", help="comma-separated case ids, e.g. Q01,Q06")
    parser.add_argument("--out", default="storage/eval_report.json", help="where to save the report")
    args = parser.parse_args()

    cases = load_cases()
    if args.only:
        wanted = {x.strip() for x in args.only.split(",")}
        cases = [c for c in cases if c["id"] in wanted]

    rows = [evaluate_case(c) for c in cases]
    summary = summarize(rows)

    for r in rows:
        mark = "PASS" if r.get("passed") else "FAIL"
        print(f"{r['id']:>4} {mark} status={r.get('status')} p@k={r.get('precision_at_k')} "
              f"{r.get('latency_ms', 0):.0f}ms {r.get('failure_reason') or ''}")
    print(json.dumps({k: v for k, v in summary.items() if k != "failures"}, indent=2, ensure_ascii=False))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved report to {out}")
    # TODO(PARTNER 3): also record the settings used (TOP_K, MIN_SIMILARITY,
    # CHUNK_SIZE, models) via config.get_settings().redacted(), so before/after
    # comparisons in docs/EVALUATION.md are reproducible.


if __name__ == "__main__":
    main()
