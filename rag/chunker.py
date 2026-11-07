
import re


def clean_text(text):
    """Remove unnecessary whitespace without changing word order."""
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_documents(documents, chunk_size=1000, overlap=150):
    """
    Split PDF documents into overlapping chunks.

    documents: list of dictionaries from extract_pdf()
    chunk_size: maximum number of characters per chunk
    overlap: characters shared between neighboring chunks
    """

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and < chunk_size")

    chunks = []

    for document in documents:
        text = clean_text(document["text"])

        if not text:
            continue

        start = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))

            # Prefer splitting at a whitespace boundary.
            if end < len(text):
                split_at = text.rfind(" ", start + 1, end)

                if split_at > start + chunk_size // 2:
                    end = split_at

            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append({
                    "chunk_id": len(chunks),
                    "text": chunk_text,
                    "source": document["source"],
                    "page": document["page"]
                })

            if end >= len(text):
                break

            start = max(start + 1, end - overlap)

    return chunks