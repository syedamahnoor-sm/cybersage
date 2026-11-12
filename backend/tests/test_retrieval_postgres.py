from uuid import UUID

import pytest
from sqlalchemy import insert

from app.db.tables import document_chunks, documents
from app.retrieval import service


@pytest.fixture
def corpus(database, monkeypatch):
    engine, connection = database
    for number, filename, status in [(1, "a.pdf", "indexed"), (2, "b.pdf", "indexed"),
                                       (3, "failed.pdf", "failed")]:
        connection.execute(insert(documents).values(
            id=UUID(int=number), filename=filename, title="Overlapping Policy",
            file_hash=str(number) * 64, status=status, page_count=10,
        ))
    rows = [
        (11, 1, 0, 2, [1.0] + [0.0] * 383),
        (12, 2, 0, 7, [1.0] + [0.0] * 383),
        (13, 1, 1, 3, [0.0, 1.0] + [0.0] * 382),
        (14, 1, 2, 4, [-1.0] + [0.0] * 383),
        (15, 3, 0, 1, [1.0] + [0.0] * 383),
    ]
    connection.execute(insert(document_chunks), [
        {"id": UUID(int=chunk), "document_id": UUID(int=doc), "chunk_index": index,
         "page_number": page, "content": "Overlapping security content", "embedding": vector}
        for chunk, doc, index, page, vector in rows
    ])
    monkeypatch.setattr(service, "embed_text", lambda query: [1.0] + [0.0] * 383)
    return service.RetrievalService(engine)


def test_exact_cosine_distance_similarity_order_and_status(corpus):
    response = corpus.search("Security", top_k=20, min_similarity=-1.0)
    assert response.result_count == 4  # failed document is excluded
    assert [row.cosine_distance for row in response.results] == pytest.approx([0, 0, 1, 2])
    assert [row.similarity_score for row in response.results] == pytest.approx([1, 1, 0, -1])
    assert [row.chunk_id for row in response.results] == [UUID(int=n) for n in [11, 12, 13, 14]]


def test_top_k_and_deterministic_equal_distance_ties(corpus):
    for _ in range(3):
        response = corpus.search("Security", top_k=1)
        assert response.result_count == 1 and response.results[0].chunk_id == UUID(int=11)


def test_inclusive_threshold_returns_fewer_than_top_k(corpus):
    assert corpus.search("Security", top_k=20, min_similarity=1.0).result_count == 2
    assert corpus.search("Security", top_k=20, min_similarity=0.0).result_count == 3


def test_no_evidence_above_threshold(corpus, monkeypatch):
    monkeypatch.setattr(service, "embed_text", lambda query: [0.0, 0.0, 1.0] + [0.0] * 381)
    assert corpus.search("Unrelated query").results == []


def test_overlapping_documents_keep_distinct_citations(corpus):
    first, second = corpus.search("Security", top_k=2).results
    assert first.document_title == second.document_title == "Overlapping Policy"
    assert first.document_id != second.document_id
    assert first.citation.filename == "a.pdf" and second.citation.filename == "b.pdf"
    assert first.citation.page_number == 2 and second.citation.page_number == 7
