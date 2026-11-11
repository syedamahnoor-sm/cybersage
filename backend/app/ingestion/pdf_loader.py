from pathlib import Path
import pymupdf


def load_pdf(file_path: str | Path) -> list[dict]:
    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(f"PDF not found: {path}")

    pages = []

    with pymupdf.open(path) as document:
        for page_index, page in enumerate(document):
            text = page.get_text("text").strip()

            if not text:
                continue

            pages.append({
                "page_number": page_index + 1,
                "content": text,
            })

    return pages
