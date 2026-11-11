from pathlib import Path
from app.ingestion.pdf_loader import load_pdf

pdf_directory = Path("../data/raw")
pdf_files = sorted(pdf_directory.glob("*.pdf"))

if not pdf_files:
    raise FileNotFoundError("No PDF files found in data/raw")

for pdf_path in pdf_files:
    pages = load_pdf(pdf_path)

    print(f"\nDocument: {pdf_path.name}")
    print(f"Pages with extracted text: {len(pages)}")

    if pages:
        print(f"First page: {pages[0]['page_number']}")
        print(f"Preview: {pages[0]['content'][:200]}")
