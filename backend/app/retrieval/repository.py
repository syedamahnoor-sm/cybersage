"""Read-only, parameterized cosine search over fully indexed documents."""

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import bindparam, select

from app.db.tables import document_chunks, documents


def search_chunks(connection, embedding: list[float], top_k: int,
                  min_similarity: float) -> list[dict]:
    distance = document_chunks.c.embedding.cosine_distance(
        bindparam("query_embedding", type_=VECTOR(384))
    ).label("cosine_distance")
    # Score the complete small corpus before limiting. MATERIALIZED deliberately
    # avoids approximate HNSW candidate selection, preserving exact top-k and ties.
    scored = select(
        document_chunks.c.id.label("chunk_id"),
        document_chunks.c.document_id,
        documents.c.title.label("document_title"),
        documents.c.filename,
        document_chunks.c.page_number,
        document_chunks.c.chunk_index,
        document_chunks.c.content,
        distance,
    ).join(documents, document_chunks.c.document_id == documents.c.id).where(
        documents.c.status == "indexed"
    ).cte("scored").prefix_with("MATERIALIZED")
    statement = select(scored).where(
        scored.c.cosine_distance <= bindparam("max_distance")
    ).order_by(
        scored.c.cosine_distance.asc(), scored.c.document_id.asc(),
        scored.c.chunk_index.asc(), scored.c.chunk_id.asc(),
    ).limit(bindparam("top_k"))
    return [dict(row) for row in connection.execute(statement, {
        "query_embedding": embedding, "max_distance": 1.0 - min_similarity,
        "top_k": top_k,
    }).mappings()]
