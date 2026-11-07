"""
File: rag/__init__.py

OWNER: Partner 1 — RAG & AI Engineer

PURPOSE:
Marks `rag` as a package. Intentionally EMPTY of imports.

Do NOT add `from .pipeline import answer_question` (or any other import)
here: importing the package would then load the embedding model / FAISS /
PDF libraries as a side effect, slow down every test, and make it easy to
create circular imports. Always import explicitly:

    from rag.pipeline import answer_question
"""
