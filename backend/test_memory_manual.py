"""Live multi-turn smoke against a running server; phases permit a real restart.

Run --phase start, restart Uvicorn, then --phase resume. Reports stay in .cache/.
"""

import argparse
import json
from pathlib import Path
from time import perf_counter, sleep
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

from app.core.config import get_settings
from test_agent_manual import check_citations

REPORT = Path(".cache/milestone8-live.json")


def call(base, path, payload=None):
    request = Request(base + path, data=json.dumps(payload).encode() if payload is not None else None,
                      headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=180) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        return error.code, json.load(error)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["start", "resume"], required=True)
    parser.add_argument("--base", default="http://127.0.0.1:8001")
    args = parser.parse_args()
    settings = get_settings()
    key = settings.GROQ_API_KEY.get_secret_value() if settings.GROQ_API_KEY else ""
    if not key.strip():
        print(json.dumps({"live_status": "skipped_missing_credentials"}))
        return
    if args.phase == "start":
        report = {"phase": "start", "conversations": {}, "records": []}
        cases = [("A", "What does NIST CSF 2.0 say about incident response?", 1),
                 ("B", "What does Pakistan's National Cyber Security Policy say about critical infrastructure?", 5)]
    else:
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        assert report["phase"] == "start"
        # Check durable history and idempotent replay before any new inference.
        for name, conversation in report["conversations"].items():
            code, history = call(args.base, f"/api/v1/conversations/{conversation['id']}/messages")
            assert code == 200 and len(history["messages"]) == 2
            code, replay = call(args.base, "/api/v1/agent/invoke", conversation["request"])
            assert code == 200 and replay == conversation["first_response"]
        report["restart_history_and_replay_verified"] = True
        cases = [("A", "What about recovery?", 1), ("B", "What response measures does it describe?", 5)]
    for index, (name, message, top_k) in enumerate(cases):
        if index:
            sleep(35)
            sleep(30)
        payload = {"message": message, "top_k": top_k, "request_id": str(uuid4())}
        if args.phase == "resume":
            payload["conversation_id"] = report["conversations"][name]["id"]
        start = perf_counter()
        code, data = call(args.base, "/api/v1/agent/invoke", payload)
        assert code == 200, f"Conversation request failed: HTTP {code}"
        assert data["capability"] == "knowledge" and data["status"] in ("answered", "insufficient_evidence")
        checks = check_citations(data)
        if args.phase == "start":
            report["conversations"][name] = {"id": data["conversation_id"], "request": payload,
                                               "first_response": data}
        else:
            assert data["context_used"]
            assert ("NIST" in data["resolved_message"]) if name == "A" else ("Pakistan" in data["resolved_message"])
        report["records"].append({"conversation": name, "message": message, "response": data,
                                  "seconds": round(perf_counter() - start, 2), "citations_verified": checks})
        REPORT.parent.mkdir(exist_ok=True)
        REPORT.write_text(json.dumps(report, indent=2).replace(key, "[REDACTED]"), encoding="utf-8")
        print(json.dumps(report["records"][-1]).replace(key, "[REDACTED]"), flush=True)
    assert report["conversations"]["A"]["id"] != report["conversations"]["B"]["id"]
    if args.phase == "resume":
        for name, conversation in report["conversations"].items():
            code, history = call(args.base, f"/api/v1/conversations/{conversation['id']}/messages")
            assert code == 200 and len(history["messages"]) == 4
            expected = [row["message"] for row in report["records"] if row["conversation"] == name]
            assert [row["content"] for row in history["messages"] if row["role"] == "user"] == expected
        assert call(args.base, f"/api/v1/conversations/{uuid4()}/messages")[0] == 404
        assert call(args.base, "/api/v1/conversations")[0] == 404
        report["phase"] = "complete"
    REPORT.write_text(json.dumps(report, indent=2).replace(key, "[REDACTED]"), encoding="utf-8")


if __name__ == "__main__":
    main()
