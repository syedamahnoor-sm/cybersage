"""Evaluation helpers use existing APIs and preserve private memory evidence."""

import json
from uuid import uuid4

from evaluation.supplementary import run_memory, run_risk, verify_memory_restart
from evaluation.report import response_hash, write_report
from evaluation.dataset import load_dataset
import pytest


def test_risk_suite_checks_categories_and_strict_invalid_inputs():
    def caller(base, path, payload):
        likelihood = payload["likelihood"]
        if type(likelihood) is not int or not 1 <= likelihood <= 5:
            return 422, {"detail": "invalid"}
        score = likelihood * payload["impact"]
        category = "Low" if score <= 5 else "Medium" if score <= 10 else "High" if score <= 15 else "Critical"
        return 200, {"capability": "risk", "assessment": {"score": score, "category": category}, "citations": [], "model": None}
    results = run_risk("http://local", caller)
    assert len(results) == 7 and all(r["passed"] for r in results)
    assert {r.get("expected_category") for r in results[:4]} == {"Low", "Medium", "High", "Critical"}


def test_memory_demo_keeps_private_id_local_and_verifies_unchanged_history(tmp_path):
    cid = str(uuid4())
    payloads = []
    history = {"messages": [
        {"role": "user", "content": "What does NIST CSF 2.0 say about incident response?"},
        {"role": "assistant", "content": "First answer"},
        {"role": "user", "content": "What about recovery?"},
        {"role": "assistant", "content": "Second answer"}]}
    def caller(base, path, payload=None):
        if payload is None:
            assert cid in path
            return 200, history
        payloads.append(payload)
        return 200, {"conversation_id": cid, "status": "answered", "citations": [],
            "resolved_message": "What does NIST CSF 2.0 say about recovery?" if len(payloads) == 2 else payload["message"]}
    private = tmp_path / "private.json"
    pauses = []
    report = run_memory("http://local", lambda *_: {}, private, [], caller, pauses.append)
    assert "conversation_id" not in payloads[0] and payloads[1]["conversation_id"] == cid
    assert report["resolved_correctly"] and report["history_persisted"] and pauses == [65]
    assert cid not in json.dumps(report) and cid in private.read_text()
    assert verify_memory_restart("http://local", private, caller)
    assert not verify_memory_restart("http://local", private, lambda *_: (200, {"messages": []}))


def test_render_rejects_reviews_from_a_different_answer(tmp_path):
    data = load_dataset()
    results = tmp_path / "results.json"
    reviews = tmp_path / "reviews.json"
    results.write_text(json.dumps({"results": [{"question_id": "P01", "response": {"answer": "new"}}]}))
    reviews.write_text(json.dumps({"reviews": {"P01": {"response_sha256": response_hash({"answer": "old"})}}}))
    with pytest.raises(ValueError, match="does not match"):
        write_report(results, reviews, tmp_path / "report.md")
