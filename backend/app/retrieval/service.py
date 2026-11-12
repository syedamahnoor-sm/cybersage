"""Query embedding, cosine search, and citations without answer generation."""

from math import isfinite

from app.embeddings import embed_text
from app.retrieval.repository import search_chunks
from app.retrieval.schemas import Citation, RetrievedChunk, SearchRequest, SearchResponse


class RetrievalUnavailableError(RuntimeError):
    """Safe public error; never contains a driver exception or SQL parameters."""


def make_citation(row: dict) -> Citation:
    title = row["document_title"]
    has_title = isinstance(title, str) and bool(title.strip())
    display_title = title.strip() if has_title else row["filename"]
    return Citation(
        document_id=row["document_id"], document_title=title,
        filename=row["filename"], page_number=row["page_number"],
        display_title=display_title, title_source="metadata" if has_title else "filename",
        label=f"[{display_title}, p. {row['page_number']}]",
    )


class RetrievalService:
    def __init__(self, engine, min_similarity: float = 0.2):
        # Validate configuration even when used outside the API.
        SearchRequest(query="configuration", min_similarity=min_similarity)
        self.engine = engine
        self.min_similarity = min_similarity

    def search(self, query: str, top_k: int = 5,
               min_similarity: float | None = None) -> SearchResponse:
        request = SearchRequest(query=query, top_k=top_k, min_similarity=min_similarity)
        threshold = self.min_similarity if request.min_similarity is None else request.min_similarity
        try:
            embedding = embed_text(request.query)
            if (len(embedding) != 384 or not all(isfinite(value) for value in embedding)
                    or not any(value != 0 for value in embedding)):
                raise ValueError("Invalid query embedding")
            with self.engine.connect() as connection:
                rows = search_chunks(connection, embedding, request.top_k, threshold)
            results = [RetrievedChunk(
                **row, similarity_score=1.0 - row["cosine_distance"],
                citation=make_citation(row),
            ) for row in rows]
        except Exception:
            # Keep model paths, driver details, SQL, and credentials private.
            raise RetrievalUnavailableError("Retrieval is temporarily unavailable.") from None
        return SearchResponse(query=request.query, results=results,
                              result_count=len(results), min_similarity=threshold)
