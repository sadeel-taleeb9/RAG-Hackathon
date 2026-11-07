
from pdf_loader import extract_pdf
from chunker import chunk_documents

files = [
    "Rag/Data/raw/BZU.pdf",
    "Rag/Data/raw/computer_engineering_plan.pdf",
    "Rag/Data/raw/electrical_engineering_plan.pdf"
]

for file in files:
    print(f"\nProcessing: {file}")

    documents = extract_pdf(file)

    chunks = chunk_documents(
        documents,
        chunk_size=1000,
        overlap=150
    )

    print(f"Pages extracted: {len(documents)}")
    print(f"Total chunks: {len(chunks)}")

    if chunks:
        print(f"First chunk ID: {chunks[0]['chunk_id']}")
        print(f"Source: {chunks[0]['source']}")
        print(f"Page: {chunks[0]['page']}")
        print(f"Chunk length: {len(chunks[0]['text'])}")
