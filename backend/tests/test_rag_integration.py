"""Real PostgreSQL/retrieval/RAG/API tests, with only model inference mocked."""

import json
from unittest.mock import Mock

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import func, select

from app.core.config import Settings
from app.db.repository import DocumentRepository
from app.db.tables import document_chunks, documents
from app.main import app
from app.rag import api
from app.rag.service import RAGService
from app.retrieval import service as retrieval_service
from app.retrieval.api import get_retrieval_service

TEXT = "The incident response plan is executed in coordination with relevant third parties once an incident is declared."


@pytest.fixture
def integrated(database, monkeypatch):
    engine, connection = database
    repository = DocumentRepository(connection)
    document = repository.get_or_create("b" * 64, "NIST.CSWP.29.pdf")
    repository.replace_chunks(document["id"], [
        {"chunk_index": 0, "page_number": 27, "content": TEXT}
    ], [[1.0] + [0.0] * 383])
    repository.set_status(document["id"], "indexed", 32)
    monkeypatch.setattr(retrieval_service, "embed_text", lambda query: [1.0] + [0.0] * 383)
    provider = Mock(model="mock-integration-model")
    def generate(system, data):
        payload = json.loads(data)
        evidence_id = payload["evidence"][0]["evidence_id"]
        if "claims" in payload:
            return json.dumps({"supported": True, "relevant": True, "evidence_ids": [evidence_id]})
        return json.dumps({"status": "answered", "claims": [{"evidence_id": evidence_id, "quote": TEXT}]})
    provider.generate_json.side_effect = generate
    return retrieval_service.RetrievalService(engine), provider, connection, document


def test_database_to_answer_preserves_provenance_without_mutation(integrated):
    retrieval, provider, connection, document = integrated
    response = RAGService(retrieval, provider, Settings(_env_file=None)).ask("Incident response?")
    assert response.status == "answered"
    citation = response.citations[0]
    assert citation.document_id == document["id"]
    assert citation.page_number == 27 and citation.chunk_index == 0
    assert citation.quote == TEXT
    assert citation.chunk_id == str(connection.scalar(select(document_chunks.c.id)))
    assert citation.evidence_id == "E_" + citation.chunk_id.replace("-", "")
    assert connection.scalar(select(func.count()).select_from(documents)) == 1
    assert connection.scalar(select(func.count()).select_from(document_chunks)) == 1


def test_actual_rag_api_with_real_pg_and_mocked_provider(integrated, monkeypatch):
    retrieval, provider, _, _ = integrated
    app.dependency_overrides[get_retrieval_service] = lambda: retrieval
    monkeypatch.setattr(api, "GroqProvider", Mock(return_value=provider))
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/rag/ask", json={"question": "Incident response?", "top_k": 5})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "answered" and data["model"] == "mock-integration-model"
        assert data["citations"][0]["label"] == "[NIST.CSWP.29.pdf, p. 27]"
        provider.close.assert_called_once()
    finally:
        app.dependency_overrides.clear()
