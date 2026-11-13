from unittest.mock import Mock
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.memory.api import get_conversation_repository
from app.memory.repository import (ConversationConflict, ConversationNotFound,
                                   ConversationRepository, MemoryUnavailableError)
from app.agent import api as agent_api


@pytest.fixture
def client():
    repository = Mock()
    repository.snapshot.side_effect = lambda cid, *args: (cid or uuid4(), None, [])
    repository.replay.return_value = None
    repository.commit_turn.side_effect = lambda *args: args[-1]
    app.dependency_overrides[get_conversation_repository] = lambda: repository
    try:
        with TestClient(app) as client:
            yield client, repository
    finally:
        app.dependency_overrides.clear()


def test_backward_compatible_request_now_returns_ids(client):
    client, repository = client
    response = client.post("/api/v1/agent/invoke", json={"message": "Calculate risk", "likelihood": 4, "impact": 5})
    assert response.status_code == 200
    data = response.json()
    assert data["assessment"]["score"] == 20 and data["conversation_id"] and data["request_id"]
    repository.commit_turn.assert_called_once()


@pytest.mark.parametrize("field", ["conversation_id", "request_id"])
def test_invalid_ids_rejected(field, client):
    client, _ = client
    response = client.post("/api/v1/agent/invoke", json={"message": "Calculate risk", field: "invalid"})
    assert response.status_code == 422


@pytest.mark.parametrize("failure,code", [(ConversationNotFound(), 404),
                                         (ConversationConflict(), 409), (MemoryUnavailableError(), 503)])
def test_safe_memory_failures(failure, code, client):
    client, repository = client
    repository.snapshot.side_effect = failure
    response = client.post("/api/v1/agent/invoke", json={"message": "Calculate risk", "conversation_id": str(uuid4())})
    assert response.status_code == code and "traceback" not in response.text.lower()


def test_no_conversation_enumeration_and_bounded_history(client):
    client, repository = client
    cid = uuid4()
    repository.history.return_value = {"conversation_id": cid, "messages": [], "has_more": False, "next_before_turn": None}
    assert client.get("/api/v1/conversations").status_code == 404
    assert client.get(f"/api/v1/conversations/{cid}/messages?limit=21").status_code == 422
    response = client.get(f"/api/v1/conversations/{cid}/messages?limit=2")
    assert response.status_code == 200 and response.json()["conversation_id"] == str(cid)
    repository.history.assert_called_once_with(cid, 2, None)
    repository.history.side_effect = ConversationNotFound()
    assert client.get(f"/api/v1/conversations/{uuid4()}/messages").status_code == 404


def test_api_multi_turn_and_restart_with_real_pg(memory_database, monkeypatch):
    from app.rag.schemas import AskResponse
    from app.agent.service import AgentService
    engine, _ = memory_database
    repository = ConversationRepository(engine)
    rag = Mock()
    rag.ask.side_effect = lambda q, k: AskResponse(question=q, answer="Fresh source excerpt.", status="answered",
        citations=[], retrieved_evidence_count=1, selected_evidence_count=1)
    app.dependency_overrides[get_conversation_repository] = lambda: repository
    app.dependency_overrides[agent_api.get_agent_service] = lambda: AgentService(lambda: rag)
    try:
        with TestClient(app) as first_client:
            first = first_client.post("/api/v1/agent/invoke", json={"message": "What does NIST CSF 2.0 say?"}).json()
        with TestClient(app) as restarted_client:
            response = restarted_client.post("/api/v1/agent/invoke", json={
                "message": "What about recovery?", "conversation_id": first["conversation_id"]})
            assert response.status_code == 200 and response.json()["context_used"]
            history = restarted_client.get(f"/api/v1/conversations/{first['conversation_id']}/messages").json()
            assert len(history["messages"]) == 4
            assert history["messages"][2]["content"] == "What about recovery?"
    finally:
        app.dependency_overrides.clear()
