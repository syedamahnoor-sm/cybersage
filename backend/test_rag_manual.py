"""Explicit live Groq smoke test; skips safely when credentials are absent."""

import json
from pathlib import Path
from time import sleep

from fastapi.testclient import TestClient
import pymupdf

from app.core.config import get_settings
from app.main import app

QUESTIONS = [
    "How does NIST CSF 2.0 address incident response?",
    "What does Pakistan's National Cyber Security Policy say about critical infrastructure?",
    "Describe the ransomware incident in the CyberSage casebook.",
    "What is the cybersecurity policy of Mars in 2050?",
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
        for index, question in enumerate(QUESTIONS):
            if index:
                # Leave time for a modest account's per-minute token allowance.
                # This is smoke-test pacing, not an SDK retry or API behavior.
                sleep(35)
                sleep(30)
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
            if any(citation["source_kind"] == "synthetic_incident" for citation in data["citations"]):
                assert "not a real event" in data["answer"]
            reports.append(data)
    assert reports[-1]["status"] == "insufficient_evidence", "Unanswerable question was not rejected"
    print(json.dumps({"live_llm_status": "executed", "results": reports}, indent=2))


if __name__ == "__main__":
    main()
