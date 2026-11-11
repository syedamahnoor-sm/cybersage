from pathlib import Path

from app.ingestion.pdf_loader import load_pdf
from app.ingestion.chunker import chunk_pages

pdf_files = sorted(Path("../data/raw").glob("*.pdf"))

for pdf_path in pdf_files:
    pages = load_pdf(pdf_path)
    chunks = chunk_pages(pages)

    print(f"\nDocument: {pdf_path.name}")
    print(f"Extracted pages: {len(pages)}")
    print(f"Generated chunks: {len(chunks)}")

    if chunks:
        first = chunks[0]
        print(f"First chunk index: {first['chunk_index']}")
        print(f"Source page: {first['page_number']}")
        print(f"Chunk length: {len(first['content'])}")
        print(f"Preview: {first['content'][:150]}")
