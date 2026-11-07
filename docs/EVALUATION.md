# Evaluation Report

**Owner:** Partner 3. Inputs from Partner 1 (settings, fixes).

> Rule: every number in this file comes from a saved `storage/eval_report.json` produced by `python -m tests.evaluate`. Copy the numbers and the date/time of the run. Never type in a number that was not measured. Mock-mode runs are never reported.

Judging context: "Evaluation" is worth 5 points and is the **second tie-breaker**. The guide asks for at least 10 questions with reference answers, metrics such as Precision@k and Faithfulness, and an analysis of system errors and what was improved because of them.

## 1. Dataset

TODO(PARTNER 3): fill from `tests/questions.json` after verification.

| Category | # cases | Languages | Verified |
|---|---|---|---|
| graduation_requirements | 2 | en, ar | TODO |
| conflicting_versions | 1 | en | TODO |
| course_prerequisites | 3 | en, ar | TODO |
| table_extraction | 2 | en, ar | TODO |
| study_plan | 1 | en | TODO |
| university_requirements | 1 | ar | TODO |
| academic_regulations | 2 | en | TODO |
| contact_information | 1 | en | TODO |
| dialect | 1 | ar (colloquial) | TODO |
| ambiguous | 1 | en | n/a |
| out_of_scope | 1 | en | n/a |
| insufficient_evidence | 1 | en | TODO |
| prompt_injection | 1 | en | TODO |
| **Total** | **18** (+ any added) | | |

## 2. Configuration of each run

TODO(PARTNER 3): paste `settings.redacted()` values that matter.

| Run | Time | PDF_EXTRACTOR | CHUNK_SIZE / OVERLAP | EMBEDDING_MODEL | TOP_K | MIN_SIMILARITY | LLM_MODEL |
|---|---|---|---|---|---|---|---|
| Baseline | TODO | | | | | | |
| After fixes | TODO | | | | | | |

## 3. Results

| Metric | Definition | Baseline | After fixes |
|---|---|---|---|
| Pass rate | cases passing their `expected_behavior` rule | TODO | TODO |
| Precision@K (citation precision) | cited sources that are expected / cited sources | TODO | TODO |
| Hit@K | ≥ 1 expected page cited | TODO | TODO |
| Refusal accuracy | `refuse` cases correctly refused | TODO | TODO |
| False refusal rate | `answer` cases wrongly refused | TODO | TODO |
| Faithfulness (automatic proxy) | must_contain ✓, must_not_contain ✓, expected page cited | TODO | TODO |
| Faithfulness (manual review) | sentences supported by the cited page | TODO | TODO |
| Mean / max latency | seconds per question | TODO | TODO |

## 4. Threshold calibration (with Partner 1)

TODO: list the top-1 retrieval score for each case (run `python -m rag.pipeline --mode real --verbose --ask "..."` or log it in `evaluate.py`).

| Lowest top-1 score among in-scope cases | Highest top-1 score among out-of-scope cases | Chosen `MIN_SIMILARITY` | Reason |
|---|---|---|---|
| TODO | TODO | TODO | TODO |

## 5. Error analysis (most valuable section for the judges)

For each failure: what happened, the root cause layer (extraction / chunking / retrieval / generation / UI), the fix, and the measured effect.

| Case | What went wrong | Root cause layer | Fix applied | Effect |
|---|---|---|---|---|
| e.g. Q06 | Answered "59" instead of "95" | Extraction (RTL number reversal in pypdf) | Switched extractor / fixed table rows | Q06 passes; golden check passes |
| TODO | | | | |

Known risks to check first (found while preparing the repo):
- Q06: number reversal in RTL tables (pypdf extracts 95 as 59).
- Q08: semester labels in merged table cells. Rows can attach to the wrong semester.
- Q03: version conflict (158 vs 138). Does the answer mention both and prefer 2026?
- Q09: table and course description disagree. Does the answer include "90 credit hours"?
- Q17: fees are not in the documents, the most likely trigger for a made-up answer.

## 6. Worst failure (prepare for judges' question 4)

TODO: one paragraph on the worst failing question, why it failed, and what you would do with more time.

## 7. Limitations of this evaluation

- Small dataset (≈ 20 questions) written by the team. Results indicate quality but are not statistically strong.
- Precision@K is measured on cited sources, not on all retrieved chunks (unless Partner 1 exposed debug retrieval output — say which).
- Automatic faithfulness is a keyword proxy and is complemented by a manual review.
