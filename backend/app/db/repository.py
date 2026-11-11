"""Parameterized document operations; callers own the transaction boundary."""

from sqlalchemy import delete, func, insert, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.tables import document_chunks, documents


class DocumentRepository:
    def __init__(self, connection):
        self.connection = connection

    def lock_hash(self, file_hash: str) -> None:
        # Serialize workers ingesting identical bytes, including failed retries.
        key = int.from_bytes(bytes.fromhex(file_hash[:16]), "big", signed=True)
        self.connection.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})

    def get_or_create(self, file_hash: str, filename: str) -> dict:
        self.connection.execute(
            pg_insert(documents).values(
                filename=filename, file_hash=file_hash, status="pending"
            ).on_conflict_do_nothing(index_elements=[documents.c.file_hash])
        )
        return dict(self.connection.execute(
            select(documents).where(documents.c.file_hash == file_hash).with_for_update()
        ).mappings().one())

    def set_status(self, document_id, status: str, page_count: int | None = None) -> None:
        values = {"status": status, "updated_at": func.now()}
        if page_count is not None:
            values["page_count"] = page_count
        self.connection.execute(
            update(documents).where(documents.c.id == document_id).values(**values)
        )

    def replace_chunks(self, document_id, chunks: list[dict], embeddings: list[list[float]]) -> None:
        if not chunks or len(chunks) != len(embeddings):
            raise ValueError("Each nonempty chunk must have exactly one embedding")
        self.connection.execute(
            delete(document_chunks).where(document_chunks.c.document_id == document_id)
        )
        self.connection.execute(insert(document_chunks), [
            {"document_id": document_id, "chunk_index": chunk["chunk_index"],
             "page_number": chunk["page_number"], "content": chunk["content"],
             "embedding": embedding}
            for chunk, embedding in zip(chunks, embeddings, strict=True)
        ])
