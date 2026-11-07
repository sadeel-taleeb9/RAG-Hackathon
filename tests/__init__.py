"""
File: tests/__init__.py

OWNER: Partner 2 — Full-Stack & Integration Engineer

Makes `tests` a package so pytest puts the repository root on sys.path and
`import config` / `import rag...` work when running `pytest` from the root.

Test ownership:
    tests/test_ingest.py     Partner 1  (ingestion, normalization, golden PDF checks)
    tests/test_retriever.py  Partner 1  (chunking, vector store, retrieval)
    tests/test_pipeline.py   Partner 2  (contract, config, mock mode, error mapping)
    tests/questions.json     Partner 3  (evaluation dataset)
    tests/evaluate.py        Partner 3  (evaluation runner, not collected by pytest)

Convention for unfinished work: tests that exercise a function still raising
NotImplementedError are marked with `pending` (xfail on NotImplementedError
only). Once the function is implemented the test runs for real: a wrong
implementation FAILS (it is not hidden), a correct one shows as XPASS —
then delete the `@pending` marker.
"""
