from unittest.mock import Mock
from uuid import UUID

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.retrieval import api
from app.retrieval.schemas import SearchResponse
from app.retrieval.service import RetrievalUnavailableError


@pytest.fixture
def client():
    fake = Mock()
    fake.search.return_value = SearchResponse(query="Security", results=[], result_count=0,
                                            min_similarity=0.2)
    app.dependency_overrides[api.get_retrieval_service] = lambda: fake
    try:
        with TestClient(app) as connection:
            yield connection, fake
    finally:
        app.dependency_overrides.clear()


def test_api_empty_response_and_health(client):
    connection, fake = client
    response = connection.post("/api/v1/retrieval/search", json={"query": "Security"})
    assert response.status_code == 200
    assert response.json() == {"query": "Security", "results": [], "result_count": 0,
                               "min_similarity": 0.2}
    fake.search.assert_called_once_with("Security", 5, None)
    assert connection.get("/api/v1/health").status_code == 200


@pytest.mark.parametrize("payload", [{}, {"query": " "}, {"query": None}, {"query": 2},
    {"query": "x", "top_k": 0}, {"query": "x", "top_k": 21},
    {"query": "x", "top_k": True}, {"query": "x", "top_k": "5"},
    {"query": "x", "min_similarity": 1.1}, {"query": "x", "extra": "ignored?"},
    {"query": "x" * 2001}])
def test_api_rejects_invalid_input(payload, client):
    connection, fake = client
    assert connection.post("/api/v1/retrieval/search", json=payload).status_code == 422
    fake.search.assert_not_called()


def test_api_serializes_evidence_and_citation(client):
    connection, fake = client
    fake.search.return_value = SearchResponse.model_validate({
        "query": "Security", "result_count": 1, "min_similarity": 0.2,
        "results": [{
            "chunk_id": UUID(int=2), "document_id": UUID(int=1), "document_title": None,
            "filename": "policy.pdf", "page_number": 8, "chunk_index": 0,
            "content": "Security controls.", "cosine_distance": 0.25, "similarity_score": 0.75,
            "citation": {"document_id": UUID(int=1), "document_title": None,
                "filename": "policy.pdf", "page_number": 8, "display_title": "policy.pdf",
                "title_source": "filename", "label": "[policy.pdf, p. 8]"},
        }],
    })
    response = connection.post("/api/v1/retrieval/search", json={"query": "Security", "top_k": 1})
    assert response.status_code == 200
    data = response.json()
    assert data["result_count"] == 1
    assert data["results"][0]["document_id"] == str(UUID(int=1))
    assert data["results"][0]["citation"]["label"] == "[policy.pdf, p. 8]"


def test_api_returns_safe_503(client):
    connection, fake = client
    fake.search.side_effect = RetrievalUnavailableError("internal details")
    response = connection.post("/api/v1/retrieval/search", json={"query": "Security"})
    assert response.status_code == 503
    assert response.json() == {"detail": "Retrieval is temporarily unavailable."}


def test_engine_initialization_failure_is_sanitized(monkeypatch):
    monkeypatch.setattr(api, "make_engine", Mock(side_effect=ValueError("secret-password")))
    with TestClient(app) as connection:
        response = connection.post("/api/v1/retrieval/search", json={"query": "Security"})
    assert response.status_code == 503
    assert "secret-password" not in response.text


def test_engine_is_reused_and_disposed_on_shutdown(monkeypatch):
    engine = Mock()
    factory = Mock(return_value=engine)
    monkeypatch.setattr(api, "make_engine", factory)
    retriever = Mock()
    retriever.search.return_value = SearchResponse(query="Security", results=[], result_count=0,
                                                 min_similarity=0.2)
    monkeypatch.setattr(api, "RetrievalService", Mock(return_value=retriever))
    with TestClient(app) as connection:
        for _ in range(2):
            assert connection.post("/api/v1/retrieval/search", json={"query": "Security"}).status_code == 200
        factory.assert_called_once()
        engine.dispose.assert_not_called()
    engine.dispose.assert_called_once()
