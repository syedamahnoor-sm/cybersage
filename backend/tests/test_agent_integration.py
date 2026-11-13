"""Actual graph/API/RAG/pgvector path; only inference is mocked."""

import json
from unittest.mock import Mock

from fastapi.testclient import TestClient

from app.db.repository import DocumentRepository
from app.agent import api as agent_api
from app.main import app
from app.rag import api as rag_api
from app.retrieval import service as retrieval_module
from app.memory.api import get_conversation_repository
from app.memory.repository import ConversationRepository

TEXT = "The incident response plan is executed in coordination with relevant third parties once an incident is declared."


def test_agent_preserves_real_database_provenance(memory_database, monkeypatch):
    engine, connection = memory_database
    repository = DocumentRepository(connection)
    document = repository.get_or_create("c" * 64, "NIST.CSWP.29.pdf")
    repository.replace_chunks(document["id"], [{"chunk_index": 0, "page_number": 27,
                                               "content": TEXT}], [[1.0] + [0.0] * 383])
    repository.set_status(document["id"], "indexed", 32)
    monkeypatch.setattr(retrieval_module, "embed_text", lambda query: [1.0] + [0.0] * 383)
    provider = Mock(model="mock-agent-integration")
    def generate(system, data):
        payload = json.loads(data)
        evidence_id = payload["evidence"][0]["evidence_id"]
        if "claims" in payload:
            return json.dumps({"supported": True, "relevant": True, "evidence_ids": [evidence_id]})
        return json.dumps({"status": "answered", "claims": [{"evidence_id": evidence_id, "quote": TEXT}]})
    provider.generate_json.side_effect = generate
    monkeypatch.setattr(rag_api, "GroqProvider", Mock(return_value=provider))
    # The lazy agent composition invokes the existing factory only after routing;
    # patch that factory, rather than an eager FastAPI dependency override.
    monkeypatch.setattr(agent_api, "get_retrieval_service",
                        lambda request: retrieval_module.RetrievalService(engine))
    app.dependency_overrides[get_conversation_repository] = lambda: ConversationRepository(engine)
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/agent/invoke", json={
                "message": "What does NIST CSF 2.0 say about incident response?",
            })
            assert response.status_code == 200
            data = response.json()
            assert data["capability"] == "knowledge" and data["status"] == "answered"
            citation = data["citations"][0]
            assert citation["document_id"] == str(document["id"])
            assert citation["page_number"] == 27 and citation["chunk_index"] == 0
            assert citation["quote"] == TEXT and citation["label"] == "[NIST.CSWP.29.pdf, p. 27]"
            assert provider.generate_json.call_count == 2
            stored = client.get(f"/api/v1/conversations/{data['conversation_id']}/messages").json()
            assert stored["messages"][1]["metadata"]["citations"] == data["citations"]
            risk = client.post("/api/v1/agent/invoke", json={
                "message": "Calculate risk", "likelihood": 4, "impact": 5,
            })
            assert risk.json()["assessment"]["score"] == 20
            assert provider.generate_json.call_count == 2  # risk never calls it
    finally:
        app.dependency_overrides.clear()
