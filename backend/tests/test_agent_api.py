from unittest.mock import Mock

from fastapi.testclient import TestClient
import pytest

from app.agent import api
from app.agent.service import AgentService
from app.llm.base import LLMUnavailableError
from app.main import app


def test_risk_api_needs_no_database_or_provider(monkeypatch):
    factory = Mock(side_effect=AssertionError("Risk must not initialize RAG"))
    monkeypatch.setattr(api, "get_retrieval_service", factory)
    with TestClient(app) as client:
        response = client.post("/api/v1/agent/invoke", json={
            "message": "Calculate risk", "likelihood": 4, "impact": 5,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["capability"] == "risk" and data["status"] == "assessed"
        assert data["assessment"]["score"] == 20 and data["assessment"]["category"] == "Critical"
        assert data["citations"] == [] and data["model"] is None
        assert "raw_request" not in data and "risk_inputs" not in data
        assert app.state.retrieval_engine is None and app.state.llm_provider is None
    factory.assert_not_called()


@pytest.mark.parametrize("body", [{}, {"message": " "}, {"message": 42}, {"message": "x" * 2001},
    {"message": "Calculate risk", "likelihood": True, "impact": 5},
    {"message": "Calculate risk", "likelihood": "4", "impact": 5},
    {"message": "Calculate risk", "likelihood": 4.0, "impact": 5},
    {"message": "Calculate risk", "likelihood": 4, "impact": 0},
    {"message": "Calculate risk", "likelihood": 6, "impact": 5},
    {"message": "What does NIST say?", "top_k": 21},
    {"message": "What does NIST say?", "tools": ["shell"]}])
def test_request_validation(body):
    with TestClient(app) as client:
        assert client.post("/api/v1/agent/invoke", json=body).status_code == 422


def test_missing_and_ambiguous_responses():
    with TestClient(app) as client:
        missing = client.post("/api/v1/agent/invoke", json={"message": "Calculate risk"})
        assert missing.status_code == 200 and missing.json()["status"] == "missing_input"
        assert missing.json()["error"]["missing_inputs"] == ["likelihood", "impact"]
        ambiguous = client.post("/api/v1/agent/invoke", json={"message": "Do something"})
        assert ambiguous.status_code == 200 and ambiguous.json()["status"] == "needs_clarification"


def test_inline_invalid_inputs_return_safe_422():
    with TestClient(app) as client:
        response = client.post("/api/v1/agent/invoke", json={"message": "Calculate risk likelihood 9 impact 5"})
    assert response.status_code == 422 and response.json()["status"] == "invalid_input"


@pytest.mark.parametrize("kind,status", [("timeout", 504), ("rate_limit", 503),
                                        ("configuration", 503), ("model", 503)])
def test_provider_error_status_is_preserved(kind, status):
    rag = Mock()
    rag.ask.side_effect = LLMUnavailableError(kind)
    app.dependency_overrides[api.get_agent_service] = lambda: AgentService(lambda: rag)
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/agent/invoke", json={"message": "What does NIST say?"})
        assert response.status_code == status
        assert response.json()["capability"] == "knowledge"
        assert response.json()["error"]["message"] == "Answer generation is temporarily unavailable."
    finally:
        app.dependency_overrides.clear()
