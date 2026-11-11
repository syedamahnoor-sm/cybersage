"""Read-only verification scoped to the requested PDFs and their hashes."""

from sqlalchemy import bindparam, text


def verify_documents(engine, file_hashes: list[str]) -> dict:
    with engine.connect() as connection:
        totals = dict(connection.execute(text(
            "SELECT (SELECT count(*) FROM documents) AS documents, "
            "(SELECT count(*) FROM document_chunks) AS chunks"
        )).mappings().one())
        docs = connection.execute(text(
            "SELECT d.filename, d.file_hash, d.status, d.page_count, count(c.id) AS chunks "
            "FROM documents d LEFT JOIN document_chunks c ON c.document_id = d.id "
            "WHERE d.file_hash IN :hashes GROUP BY d.id ORDER BY d.filename"
        ).bindparams(bindparam("hashes", expanding=True)), {"hashes": file_hashes}).mappings().all()
        checks = dict(connection.execute(text(
            "SELECT count(*) AS chunks, "
            "count(*) FILTER (WHERE vector_dims(c.embedding) <> 384) AS invalid_dimensions, "
            "count(*) FILTER (WHERE c.page_number < 1 OR c.page_number > d.page_count "
            "OR d.page_count IS NULL) AS invalid_pages, "
            "count(*) FILTER (WHERE abs(vector_norm(c.embedding) - 1) > 0.00001) "
            "AS invalid_norms "
            "FROM document_chunks c JOIN documents d ON d.id = c.document_id "
            "WHERE d.file_hash IN :hashes"
        ).bindparams(bindparam("hashes", expanding=True)), {"hashes": file_hashes}).mappings().one())
        checks["orphan_chunks_in_database"] = connection.scalar(text(
            "SELECT count(*) FROM document_chunks c LEFT JOIN documents d "
            "ON d.id = c.document_id WHERE d.id IS NULL"
        ))
        checks["duplicate_indices"] = connection.scalar(text(
            "SELECT count(*) FROM (SELECT c.document_id, c.chunk_index "
            "FROM document_chunks c JOIN documents d ON d.id = c.document_id "
            "WHERE d.file_hash IN :hashes GROUP BY c.document_id, c.chunk_index "
            "HAVING count(*) > 1) duplicates"
        ).bindparams(bindparam("hashes", expanding=True)), {"hashes": file_hashes})
    return {"database_totals": totals, "source_documents": [dict(row) for row in docs],
            "source_checks": checks}
