from unittest.mock import MagicMock, Mock
from uuid import UUID

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import OperationalError

from app.retrieval import service
from app.retrieval.schemas import SearchRequest


@pytest.fixture
def retrieval(monkeypatch):
    row = {
        "chunk_id": UUID(int=11), "document_id": UUID(int=1),
        "document_title": "Security Policy", "filename": "policy.pdf",
        "page_number": 8, "chunk_index": 4, "content": "Protect critical infrastructure.",
        "cosine_distance": 0.25,
    }
    embedder = Mock(return_value=[1.0] + [0.0] * 383)
    searcher = Mock(return_value=[row])
    monkeypatch.setattr(service, "embed_text", embedder)
    monkeypatch.setattr(service, "search_chunks", searcher)
    engine = MagicMock()
    return service.RetrievalService(engine), embedder, searcher, row


@pytest.mark.parametrize("query", ["", " \n\t", None, 42, ["security"], "a" * 2001])
def test_invalid_query_does_not_embed(query, retrieval):
    retriever, embedder, searcher, _ = retrieval
    with pytest.raises(ValidationError):
        retriever.search(query)
    embedder.assert_not_called()
    searcher.assert_not_called()


@pytest.mark.parametrize("top_k", [0, -1, 21, True, "5", 1.5])
def test_invalid_top_k(top_k):
    with pytest.raises(ValidationError):
        SearchRequest(query="Security", top_k=top_k)


@pytest.mark.parametrize("threshold", [-1.1, 1.1, float("nan"), float("inf"), True, "0.2"])
def test_invalid_threshold(threshold):
    with pytest.raises(ValidationError):
        SearchRequest(query="Security", min_similarity=threshold)


def test_embedding_integration_similarity_and_citation(retrieval):
    retriever, embedder, searcher, row = retrieval
    response = retriever.search("  Critical infrastructure?  ", top_k=3, min_similarity=0.3)
    embedder.assert_called_once_with("Critical infrastructure?")
    assert searcher.call_args.args[1:] == (embedder.return_value, 3, 0.3)
    assert response.query == "Critical infrastructure?"
    assert response.result_count == 1 and response.min_similarity == 0.3
    match = response.results[0]
    assert match.cosine_distance == 0.25
    assert match.similarity_score == 0.75
    assert match.citation.label == "[Security Policy, p. 8]"
    assert match.citation.title_source == "metadata"
    assert match.citation.document_id == row["document_id"]
    assert match.chunk_index == 4


@pytest.mark.parametrize("title", [None, "", "  "])
def test_citation_falls_back_to_exact_filename(title, retrieval):
    _, _, _, row = retrieval
    row["document_title"] = title
    citation = service.make_citation(row)
    assert citation.document_title == title
    assert citation.display_title == "policy.pdf"
    assert citation.label == "[policy.pdf, p. 8]"
    assert citation.title_source == "filename"


def test_empty_results_and_default_threshold(retrieval):
    retriever, _, searcher, _ = retrieval
    searcher.return_value = []
    response = retriever.search("No relevant evidence")
    assert response.results == [] and response.result_count == 0
    assert searcher.call_args.args[-1] == 0.2


def test_zero_threshold_override_is_respected(retrieval):
    retriever, _, searcher, _ = retrieval
    retriever.search("Evidence", min_similarity=0.0)
    assert searcher.call_args.args[-1] == 0.0


@pytest.mark.parametrize("stage", ["embedding", "database"])
def test_failures_do_not_expose_internal_details(stage, retrieval):
    retriever, embedder, searcher, _ = retrieval
    target = embedder if stage == "embedding" else searcher
    target.side_effect = OperationalError("internal SQL", {}, Exception("secret-password"))
    with pytest.raises(service.RetrievalUnavailableError) as captured:
        retriever.search("Security")
    assert str(captured.value) == "Retrieval is temporarily unavailable."
    assert "secret" not in str(captured.value)


@pytest.mark.parametrize("embedding", [[0.0] * 384, [1.0] * 383, [float("nan")] * 384])
def test_invalid_embedding_is_not_queried(embedding, retrieval):
    retriever, embedder, searcher, _ = retrieval
    embedder.return_value = embedding
    with pytest.raises(service.RetrievalUnavailableError):
        retriever.search("Security")
    searcher.assert_not_called()
