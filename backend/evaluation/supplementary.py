"""Separate risk and real memory evidence; never changes the 10-question dataset."""

from hashlib import sha256
import json
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace
from uuid import uuid4

from evaluation.runner import http_call, pause, redact


def run_risk(base, caller=http_call):
    records = []
    for likelihood, impact, score, category in [(1,2,2,"Low"), (2,4,8,"Medium"),
                                               (3,5,15,"High"), (4,5,20,"Critical")]:
        code, response = caller(base, "/api/v1/agent/invoke", {"message": "Calculate risk",
            "likelihood": likelihood, "impact": impact, "request_id": str(uuid4())})
        passed = (code == 200 and response.get("capability") == "risk"
            and response.get("assessment", {}).get("score") == score
            and response.get("assessment", {}).get("category") == category
            and response.get("citations") == [] and response.get("model") is None)
        records.append({"inputs": {"likelihood": likelihood, "impact": impact},
            "expected_score": score, "expected_category": category,
            "http_status": code, "response": response, "passed": passed})
    for likelihood in (0, True, "4"):
        code, response = caller(base, "/api/v1/agent/invoke", {
            "message": "Calculate risk", "likelihood": likelihood, "impact": 5})
        records.append({"inputs": {"likelihood": likelihood, "impact": 5},
            "expected_http_status": 422, "http_status": code, "response": response, "passed": code == 422})
    return records


def run_memory(base, verifier, private_path, secrets, caller=http_call, sleeper=pause):
    records = []
    cid = None
    for index, message in enumerate(["What does NIST CSF 2.0 say about incident response?", "What about recovery?"]):
        if index:
            sleeper(65)
        payload = {"message": message, "top_k": 1, "request_id": str(uuid4())}
        if cid:
            payload["conversation_id"] = cid
        start = perf_counter()
        code, response = caller(base, "/api/v1/agent/invoke", payload)
        if code != 200:
            records.append({"question": message, "http_status": code, "response": response})
            break
        if cid and response["conversation_id"] != cid:
            raise ValueError("Memory conversation scope changed")
        cid = response["conversation_id"]
        checks = [verifier(c, SimpleNamespace(expected_source="NIST.CSWP.29.pdf", expected_pages=list(range(1,33))))
                  for c in response.get("citations", [])]
        records.append({"question": message, "http_status": code, "duration_seconds": round(perf_counter()-start,4),
                        "response": response, "citation_checks": checks})
    code, history = caller(base, f"/api/v1/conversations/{cid}/messages") if cid else (0,{})
    persisted = (code == 200 and len(history.get("messages", [])) == 4
                 and [row["content"] for row in history["messages"] if row["role"] == "user"] ==
                     ["What does NIST CSF 2.0 say about incident response?", "What about recovery?"])
    public = {"conversation_id": "[PRIVATE: see backend/.cache/evaluation-memory-private.json]",
        "conversation_id_sha256": sha256(cid.encode()).hexdigest() if cid else None,
        "records": records, "history_persisted": persisted, "persistence_verified_after_restart": False,
        "resolved_correctly": len(records) == 2 and records[1].get("response", {}).get("resolved_message") ==
                             "What does NIST CSF 2.0 say about recovery?"}
    # Actual access IDs are captured locally for assignment evidence, never committed.
    private = {"conversation_id": cid, "history": history, "records": records}
    text = json.dumps(private, indent=2)
    for secret in secrets:
        text = text.replace(secret, "[REDACTED]")
    private_path.parent.mkdir(parents=True, exist_ok=True)
    private_path.write_text(text, encoding="utf-8")
    return redact(public, secrets)


def verify_memory_restart(base, private_path, caller=http_call):
    private = json.loads(private_path.read_text(encoding="utf-8"))
    code, history = caller(base, f"/api/v1/conversations/{private['conversation_id']}/messages")
    return code == 200 and history == private["history"]
