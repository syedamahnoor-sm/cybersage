"""Explicit live Groq smoke test; skips safely when credentials are absent."""

import json
from pathlib import Path

from fastapi.testclient import TestClient
import pymupdf

from app.core.config import get_settings
from app.main import app

QUESTIONS = [
    "What does Pakistan's cyber security policy say about critical infrastructure?",
    "How does NIST CSF 2.0 address incident response?",
    "What happened in the ransomware incidents described in the CyberSage casebook?",
    "What is the exact SHA-256 hash of the malware used in case CS-INC-002?",
]


def main() -> None:
    settings = get_settings()
    if not settings.GROQ_API_KEY or not settings.GROQ_API_KEY.get_secret_value().strip():
        print(json.dumps({"live_llm_status": "skipped_missing_credentials",
                          "model": settings.GROQ_MODEL}))
        return
    raw_directory = Path(__file__).resolve().parents[1] / "data" / "raw"
    reports = []
    with TestClient(app) as client:
        for question in QUESTIONS:
            response = client.post("/api/v1/rag/ask", json={"question": question, "top_k": 5})
            assert response.status_code == 200, f"RAG unavailable: HTTP {response.status_code}"
            data = response.json()
            for citation in data["citations"]:
                path = (raw_directory / citation["filename"]).resolve()
                assert path.parent == raw_directory.resolve()
                with pymupdf.open(path) as pdf:
                    text = " ".join(pdf[citation["page_number"] - 1].get_text("text").split())
                assert " ".join(citation["quote"].split()) in text
                assert citation["evidence_id"] == "E_" + citation["chunk_id"].replace("-", "")
            if data["status"] == "insufficient_evidence":
                assert not data["citations"]
            reports.append(data)
    assert reports[-1]["status"] == "insufficient_evidence", "Unanswerable question was not rejected"
    print(json.dumps({"live_llm_status": "executed", "results": reports}, indent=2))


if __name__ == "__main__":
    main()
