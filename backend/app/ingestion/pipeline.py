"""Idempotent ingestion, with one atomic chunk replacement per document."""

from dataclasses import dataclass, field
from hashlib import file_digest
from pathlib import Path

import pymupdf
from sqlalchemy.engine import Engine

from app.db.repository import DocumentRepository
from app.embeddings import embed_texts
from app.ingestion.chunker import chunk_pages
from app.ingestion.pdf_loader import load_pdf

DEFAULT_INPUT_DIR = Path(__file__).resolve().parents[3] / "data" / "raw"


def hash_pdf(path: Path) -> str:
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def discover_pdfs(directory: Path) -> list[Path]:
    if not directory.is_dir():
        raise FileNotFoundError("PDF input directory does not exist")
    return sorted(path for path in directory.iterdir()
                  if path.is_file() and path.suffix.lower() == ".pdf")


@dataclass
class IngestionResult:
    filename: str
    status: str
    chunks_inserted: int = 0
    error: str | None = None


@dataclass
class IngestionSummary:
    results: list[IngestionResult] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "documents_processed": sum(r.status == "indexed" for r in self.results),
            "documents_skipped": sum(r.status == "skipped" for r in self.results),
            "chunks_inserted": sum(r.chunks_inserted for r in self.results),
            "failures": sum(r.status == "failed" for r in self.results),
        }


def ingest_pdf(engine: Engine, path: Path, batch_size: int = 32) -> IngestionResult:
    """Commit indexed + chunks together, or commit failed with no partial writes.

    A transaction-level hash lock prevents concurrent duplicate workers. The
    savepoint preserves the document row while rolling back all processing writes
    on failure. A terminated process rolls back the outer transaction entirely.
    """
    file_hash = hash_pdf(path)
    with engine.begin() as connection:
        repository = DocumentRepository(connection)
        repository.lock_hash(file_hash)
        document = repository.get_or_create(file_hash, path.name)
        if document["status"] == "indexed":
            return IngestionResult(path.name, "skipped")
        try:
            with connection.begin_nested():
                repository.set_status(document["id"], "processing")
                pages = load_pdf(path)
                chunks = chunk_pages(pages)
                if not chunks:
                    raise ValueError("PDF contains no extractable text chunks")
                with pymupdf.open(path) as pdf:
                    page_count = pdf.page_count
                embeddings = embed_texts([chunk["content"] for chunk in chunks], batch_size)
                if hash_pdf(path) != file_hash:
                    raise ValueError("PDF changed during ingestion")
                repository.replace_chunks(document["id"], chunks, embeddings)
                repository.set_status(document["id"], "indexed", page_count)
        except Exception as error:
            repository.set_status(document["id"], "failed")
            # SQL exceptions may include credentials/content; expose type only.
            return IngestionResult(path.name, "failed", error=type(error).__name__)
    return IngestionResult(path.name, "indexed", len(chunks))


def ingest_directory(engine: Engine, directory: Path = DEFAULT_INPUT_DIR,
                     batch_size: int = 32) -> IngestionSummary:
    summary = IngestionSummary()
    for path in discover_pdfs(directory):
        try:
            result = ingest_pdf(engine, path, batch_size)
        except Exception as error:
            result = IngestionResult(path.name, "failed", error=type(error).__name__)
        summary.results.append(result)
    return summary
