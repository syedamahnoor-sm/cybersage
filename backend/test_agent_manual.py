"""Explicit real agent/API smoke test; external calls require configured Groq key."""

import json
from pathlib import Path
from time import perf_counter, sleep
from uuid import UUID

from fastapi.testclient import TestClient
import pymupdf
from sqlalchemy import select

from app.core.config import get_settings
from app.db.connection import make_engine
from app.db.tables import document_chunks, documents
from app.main import app


def check_citations(data: dict) -> int:
    raw = Path(__file__).resolve().parents[1] / "data" / "raw"
    engine = make_engine()
    try:
        for citation in data["citations"]:
            with engine.connect() as connection:
                row = connection.execute(select(
                    document_chunks.c.content, document_chunks.c.document_id,
                    document_chunks.c.page_number, document_chunks.c.chunk_index,
                    documents.c.filename, documents.c.title,
                ).join(documents).where(document_chunks.c.id == UUID(citation["chunk_id"]))).mappings().one()
            assert str(row["document_id"]) == citation["document_id"]
            assert row["page_number"] == citation["page_number"]
            assert row["chunk_index"] == citation["chunk_index"]
            assert row["filename"] == citation["filename"] and row["title"] == citation["document_title"]
            quote = " ".join(citation["quote"].split())
            assert quote in " ".join(row["content"].split())
            assert citation["evidence_id"] == "E_" + citation["chunk_id"].replace("-", "")
            path = (raw / citation["filename"]).resolve()
            assert path.parent == raw.resolve()
            with pymupdf.open(path) as pdf:
                assert 1 <= citation["page_number"] <= pdf.page_count
                assert quote in " ".join(pdf[citation["page_number"] - 1].get_text().split())
    finally:
        engine.dispose()
    return len(data["citations"])


def main() -> None:
    settings = get_settings()
    key = settings.GROQ_API_KEY.get_secret_value() if settings.GROQ_API_KEY else ""
    reports = []
    with TestClient(app) as client:
        for likelihood, impact, score, category in [(1, 2, 2, "Low"), (2, 4, 8, "Medium"),
                                                     (3, 5, 15, "High"), (4, 5, 20, "Critical")]:
            response = client.post("/api/v1/agent/invoke", json={
                "message": "Calculate risk", "likelihood": likelihood, "impact": impact,
            })
            data = response.json()
            assert response.status_code == 200 and data["capability"] == "risk"
            assert data["assessment"]["score"] == score and data["assessment"]["category"] == category
            assert data["citations"] == [] and data["model"] is None
            reports.append({"http_status": 200, "response": data})
        invalid = client.post("/api/v1/agent/invoke", json={
            "message": "Calculate risk", "likelihood": 6, "impact": 5,
        })
        assert invalid.status_code == 422
        reports.append({"check": "invalid risk", "http_status": 422, "response": invalid.json()})
        for message, status in [("Calculate risk", "missing_input"), ("Do something", "needs_clarification")]:
            response = client.post("/api/v1/agent/invoke", json={"message": message})
            assert response.status_code == 200 and response.json()["status"] == status
            reports.append({"http_status": 200, "response": response.json()})
        if key.strip():
            for index, question in enumerate([
                "How does NIST CSF 2.0 address incident response?",
                "What is the cybersecurity policy of Mars in 2050?",
            ]):
                if index:
                    sleep(35)
                    sleep(30)
                start = perf_counter()
                # Narrow the grounded smoke query to its highest-ranked passage;
                # default top-k=5 can produce extra model-altered excerpts.
                response = client.post("/api/v1/agent/invoke", json={"message": question,
                                                                     "top_k": 1 if index == 0 else 5})
                assert response.status_code == 200, f"Agent unavailable: HTTP {response.status_code}"
                data = response.json()
                assert data["capability"] == "knowledge"
                if index == 0:
                    assert data["status"] == "answered" and data["citations"]
                else:
                    assert data["status"] == "insufficient_evidence" and data["citations"] == []
                checks = check_citations(data)
                reports.append({"question": question, "http_status": 200,
                                "seconds": round(perf_counter() - start, 2),
                                "citations_verified": checks, "response": data})
    output = json.dumps({"live_knowledge_status": "executed" if key.strip() else "skipped_missing_credentials",
                         "results": reports}, indent=2)
    print(output.replace(key, "[REDACTED]") if key else output)


if __name__ == "__main__":
    main()
