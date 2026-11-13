"""Sequential HTTP evaluation. No new agent/retrieval/prompt implementation."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from time import perf_counter, sleep
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4
from urllib.parse import urlsplit

from evaluation.dataset import DATASET_PATH, verify_ground_truth
from evaluation.grading import classify_failure, lexical_coverage, metrics


def redact(value, secrets=()):
    if isinstance(value, dict):
        return {key: ("[PRIVATE]" if key in ("conversation_id", "request_id") and item else redact(item, secrets))
                for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item, secrets) for item in value]
    if isinstance(value, str):
        for secret in secrets:
            if secret:
                value = value.replace(secret, "[REDACTED]")
        return re.sub(r"gsk_[A-Za-z0-9]{20,}", "[REDACTED]", value)
    return value


def http_call(base, path, payload=None):
    request = Request(base + path, data=json.dumps(payload).encode() if payload is not None else None,
                      headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=180) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        return error.code, json.load(error)


def pause(seconds):
    while seconds > 0:
        chunk = min(seconds, 30)
        sleep(chunk)
        seconds -= chunk


def run(dataset, output: Path, base, verifier, secrets=(), pause_seconds=65,
        caller=http_call, sleeper=pause, resume=False, credential_available=True):
    if pause_seconds < 0:
        raise ValueError("Pause must not be negative")
    url = urlsplit(base)
    if url.scheme not in ("http", "https") or not url.hostname or url.username or url.password or url.query or url.fragment:
        raise ValueError("Use an HTTP(S) API base without credentials, query, or fragment")
    fingerprint = hashlib.sha256(DATASET_PATH.read_bytes()).hexdigest()
    if output.exists():
        if not resume:
            raise ValueError("Result file exists; use --resume or choose another file")
        report = json.loads(output.read_text(encoding="utf-8"))
        if report["dataset_sha256"] != fingerprint:
            raise ValueError("Dataset changed; start a separate evaluation")
    else:
        report = {"schema_version": 1, "dataset_sha256": fingerprint,
            "started_at": datetime.now(timezone.utc).isoformat(), "overall_status": "running",
            "parameters": {"top_k": dataset.top_k, "pause_seconds": pause_seconds,
                           "independent_requests": True, "base": base},
            "results": [{"question_id": q.id, "execution": "not_run"} for q in dataset.questions]}
    def save():
        report["metrics"] = metrics(dataset, report["results"])
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(output.suffix + ".tmp")
        temporary.write_text(json.dumps(redact(report, secrets), indent=2), encoding="utf-8")
        temporary.replace(output)
    if not credential_available:
        report["overall_status"] = "incomplete"
        report["incomplete_reason"] = "missing_credentials"
        save()
        return report
    report.pop("incomplete_reason", None)
    seen = {r["conversation_fingerprint"] for r in report["results"] if r.get("conversation_fingerprint")}
    for index, question in enumerate(dataset.questions):
        if report["results"][index]["execution"] != "not_run":
            continue
        if index:
            sleeper(pause_seconds)
        record = {"question_id": question.id, "execution": "executed", "error": None}
        agent_start = None
        try:
            # Independent, read-only diagnostic call. Its results are not evidence
            # supplied by the evaluator to generation; the agent retrieves itself.
            code, evidence = caller(base, "/api/v1/retrieval/search", {"query": question.question, "top_k": dataset.top_k})
            record["retrieval_diagnostic"] = evidence if code == 200 else {"http_status": code}
            agent_start = perf_counter()
            code, response = caller(base, "/api/v1/agent/invoke", {"message": question.question,
                "top_k": dataset.top_k, "request_id": str(uuid4())})
            record.update(http_status=code, duration_seconds=round(perf_counter() - agent_start, 4), response=response)
            if code != 200:
                record["error"] = f"http_{code}"
            else:
                cid = response.get("conversation_id")
                fingerprint = hashlib.sha256(cid.encode()).hexdigest() if cid else None
                if not fingerprint or fingerprint in seen or response.get("context_used"):
                    raise ValueError("Conversation isolation check failed")
                seen.add(fingerprint)
                record["conversation_fingerprint"] = fingerprint
                record["conversation_independence_verified"] = True
            checks = [verifier(citation, question) for citation in response.get("citations", [])]
            coverage = lexical_coverage(question, response)
            record.update(citation_checks=checks, lexical_coverage=coverage,
                failure_classification=classify_failure(question, response, checks, coverage, record["error"]))
        except Exception as error:
            record["error"] = type(error).__name__
            record["failure_classification"] = "provider_or_transport_error"
            record.setdefault("duration_seconds", round(perf_counter()-agent_start,4) if agent_start else None)
        report["results"][index] = redact(record, secrets)
        save()
        print(f"{question.id}: {record.get('response', {}).get('status', 'error')} / {record.get('failure_classification') or 'no automatic failure'}", flush=True)
    report["overall_status"] = ("complete" if all(r["execution"] == "executed" and not r.get("error")
                                                 for r in report["results"]) else "incomplete")
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    save()
    return report
