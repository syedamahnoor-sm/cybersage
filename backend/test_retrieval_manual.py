"""Real-model API checks and PDF citation verification for the original corpus.

Run from backend: python test_retrieval_manual.py
This is an explicit smoke test, not part of ordinary offline unit tests.
Relevance still needs human review of the returned passages.
"""

import json
from pathlib import Path

from fastapi.testclient import TestClient
import pymupdf

from app.main import app

QUERIES = [
    "What does Pakistan's cyber security policy say about critical infrastructure?",
    "How does NIST CSF 2.0 address incident response?",
    "What happened in the ransomware incidents described in the CyberSage casebook?",
]
RAW_DIRECTORY = Path(__file__).resolve().parents[1] / "data" / "raw"


def main() -> None:
    reports = []
    with TestClient(app) as client:
        assert client.get("/api/v1/health").status_code == 200
        for query in QUERIES:
            response = client.post("/api/v1/retrieval/search", json={"query": query, "top_k": 5})
            assert response.status_code == 200, f"Search failed: HTTP {response.status_code}"
            data = response.json()
            assert data["result_count"] == len(data["results"])
            for result in data["results"]:
                # Source metadata is checked against local files, never a URL.
                path = (RAW_DIRECTORY / result["filename"]).resolve()
                assert path.parent == RAW_DIRECTORY.resolve()
                with pymupdf.open(path) as pdf:
                    page_number = result["page_number"]
                    assert 1 <= page_number <= pdf.page_count
                    page_text = " ".join(pdf[page_number - 1].get_text("text").split())
                assert " ".join(result["content"].split()) in page_text
                citation = result["citation"]
                assert citation["document_id"] == result["document_id"]
                assert citation["filename"] == result["filename"]
                assert citation["document_title"] == result["document_title"]
                assert citation["page_number"] == page_number
                assert citation["label"] == f"[{citation['display_title']}, p. {page_number}]"
                assert abs(result["similarity_score"] - (1 - result["cosine_distance"])) < 1e-12
            reports.append(data)
        no_evidence = client.post("/api/v1/retrieval/search", json={
            "query": QUERIES[0], "top_k": 5, "min_similarity": 1.0,
        })
        assert no_evidence.status_code == 200
        assert no_evidence.json()["results"] == []
        assert client.post("/api/v1/retrieval/search", json={"query": " "}).status_code == 422
        assert client.post("/api/v1/retrieval/search", json={"query": "x", "top_k": 21}).status_code == 422
    print(json.dumps({"queries": reports, "pdf_citations_checked": sum(
        report["result_count"] for report in reports), "api_checks": "passed"}, indent=2))


if __name__ == "__main__":
    main()
