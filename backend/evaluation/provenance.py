"""External audit of returned citation metadata and exact source quote provenance."""

from uuid import UUID

import pymupdf
from sqlalchemy import select

from app.db.tables import document_chunks, documents
from evaluation.dataset import normalize, ROOT


def verify_citation(engine, citation, question, raw_directory=ROOT / "data" / "raw"):
    check = {"evidence_id": citation.get("evidence_id"), "metadata_valid": False,
             "quote_in_chunk": False, "quote_in_pdf": False, "provenance_valid": False,
             "source_relevant": citation.get("filename") == question.expected_source,
             "expected_page": citation.get("page_number") in question.expected_pages}
    try:
        chunk_id = UUID(citation["chunk_id"])
        with engine.connect() as connection:
            row = connection.execute(select(document_chunks.c.document_id, document_chunks.c.page_number,
                document_chunks.c.chunk_index, document_chunks.c.content, documents.c.filename,
                documents.c.title).join(documents).where(document_chunks.c.id == chunk_id)).mappings().one()
        check["metadata_valid"] = (str(row["document_id"]) == citation["document_id"]
            and row["page_number"] == citation["page_number"] and row["chunk_index"] == citation["chunk_index"]
            and row["filename"] == citation["filename"] and row["title"] == citation["document_title"]
            and citation["evidence_id"] == "E_" + chunk_id.hex)
        quote = normalize(citation["quote"])
        check["quote_in_chunk"] = bool(quote) and quote in normalize(row["content"])
        # Use the database's filename/page, never a provider-controlled filesystem path.
        path = (raw_directory / row["filename"]).resolve()
        if path.parent != raw_directory.resolve():
            return check
        with pymupdf.open(path) as pdf:
            check["quote_in_pdf"] = quote in normalize(pdf[row["page_number"] - 1].get_text())
        check["provenance_valid"] = all(check[name] for name in ("metadata_valid", "quote_in_chunk", "quote_in_pdf"))
    except Exception as error:
        check["check_error"] = type(error).__name__  # Never persist driver exception bodies.
    return check
