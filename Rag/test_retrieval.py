
from pdf_loader import extract_pdf
from chunker import chunk_documents
from embeddings import get_embedding_model
from retriever import FAISSRetriever

FILES = [
    "Rag/Data/raw/BZU.pdf",
    "Rag/Data/raw/computer_engineering_plan.pdf",
    "Rag/Data/raw/electrical_engineering_plan.pdf",
]

all_chunks = []

for file in FILES:
    print(f"Loading: {file}", flush=True)
    documents = extract_pdf(file)
    chunks = chunk_documents(documents)
    all_chunks.extend(chunks)

print(f"Total chunks: {len(all_chunks)}", flush=True)

model = get_embedding_model()
retriever = FAISSRetriever(model)
retriever.build_index(all_chunks)

questions = [
    "كم عدد الساعات المعتمدة لهندسة الحاسوب؟",
    "كم عدد الساعات المعتمدة لهندسة الحاسوب لدفعة 2025؟",
    "كم عدد الساعات المعتمدة لهندسة الحاسوب لدفعة 2023؟",
]

for question in questions:
    print("\n" + "=" * 60)
    print("QUESTION:", question)

    results = retriever.search(question, top_k=5)

    for i, result in enumerate(results, 1):
        print(f"\nResult {i}")
        print("Source:", result["source"])
        print("Page:", result["page"])
        print("Score:", round(result["score"], 4))
        print("Text:", result["text"][:350])
