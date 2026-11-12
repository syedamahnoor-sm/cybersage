from unittest.mock import Mock

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.llm.base import LLMUnavailableError
from app.rag import api
from app.rag.schemas import AskResponse
from app.retrieval.service import RetrievalUnavailableError


@pytest.fixture
def client():
    service = Mock()
    service.ask.return_value = AskResponse(
        question="Incident response?", answer="Insufficient source evidence.",
        status="insufficient_evidence", citations=[], retrieved_evidence_count=0,
        selected_evidence_count=0, abstention_reason="no_evidence",
    )
    app.dependency_overrides[api.get_rag_service] = lambda: service
    try:
        with TestClient(app) as connection:
            yield connection, service
    finally:
        app.dependency_overrides.clear()


def test_response_structure_and_health(client):
    connection, service = client
    response = connection.post("/api/v1/rag/ask", json={"question": "Incident response?"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "insufficient_evidence" and data["citations"] == []
    assert data["retrieved_evidence_count"] == 0 and data["model"] is None
    assert data["grounding_mode"] == "verified_excerpts"
    service.ask.assert_called_once_with("Incident response?", 5)
    assert connection.get("/api/v1/health").status_code == 200


@pytest.mark.parametrize("body", [{}, {"question": " "}, {"question": None},
    {"question": 42}, {"question": "x" * 2001}, {"question": "x", "top_k": 21},
    {"question": "x", "top_k": True}, {"question": "x", "top_k": 0},
    {"question": "x", "extra": "value"}])
def test_api_validation(body, client):
    connection, service = client
    assert connection.post("/api/v1/rag/ask", json=body).status_code == 422
    service.ask.assert_not_called()


@pytest.mark.parametrize("kind,status", [("configuration", 503), ("timeout", 504),
    ("rate_limit", 503), ("model", 503), ("provider", 503)])
def test_provider_errors_return_safe_http_status(kind, status, client):
    connection, service = client
    service.ask.side_effect = LLMUnavailableError(kind)
    response = connection.post("/api/v1/rag/ask", json={"question": "Incident response?"})
    assert response.status_code == status
    assert response.json() == {"detail": "Answer generation is temporarily unavailable."}


def test_retrieval_failure_is_safe(client):
    connection, service = client
    service.ask.side_effect = RetrievalUnavailableError("sensitive internal error")
    response = connection.post("/api/v1/rag/ask", json={"question": "Incident response?"})
    assert response.status_code == 503 and "sensitive" not in response.text
