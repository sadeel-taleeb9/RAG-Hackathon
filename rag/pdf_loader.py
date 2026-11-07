
from pathlib import Path
import pymupdf as fitz

def extract_pdf(pdf_path):
    documents = []

    if not Path(pdf_path).is_file():
        raise FileNotFoundError(
            f"PDF not found: {pdf_path}"
        )

    with fitz.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf, start=1):
            text = page.get_text("text", sort=True)

            if not text.strip():
                print(f"Empty page: {page_number}")
                continue

            documents.append({
                "text": text,
                "source": Path(pdf_path).name,
                "page": page_number
            })

    return documents


if __name__ == "__main__":
    files = [
    "Rag/Data/raw/BZU.pdf",
    "Rag/Data/raw/computer_engineering_plan.pdf"
]
    

    for file in files:
        documents = extract_pdf(file)

        print(f"\nFile: {file}")
        print(f"Extracted pages: {len(documents)}")

        if documents:
            print("First page preview:")
            print(documents[0]["text"][:500])
