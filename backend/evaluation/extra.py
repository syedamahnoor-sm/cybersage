"""Separate risk/memory assignment evidence. Run after the 10-question evaluation."""

import argparse
from functools import partial
import json
from pathlib import Path

from app.core.config import get_settings
from app.db.connection import make_engine
from evaluation.provenance import verify_citation
from evaluation.runner import pause, redact
from evaluation.supplementary import run_memory, run_risk, verify_memory_restart


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8001")
    parser.add_argument("--output", type=Path, default=Path("evaluation/results/supplementary.json"))
    parser.add_argument("--verify-after-restart", action="store_true")
    args = parser.parse_args()
    private_path = Path(".cache/evaluation-memory-private.json")
    settings = get_settings()
    secrets = [value.get_secret_value() for value in (settings.GROQ_API_KEY, settings.POSTGRES_PASSWORD)
               if value and value.get_secret_value()]
    if args.verify_after_restart:
        report = json.loads(args.output.read_text(encoding="utf-8"))
        verified = verify_memory_restart(args.base, private_path)
        report["memory_demonstration"]["persistence_verified_after_restart"] = verified
        args.output.write_text(json.dumps(redact(report,secrets),indent=2),encoding="utf-8")
        print("Memory history re-read after restart:", verified)
        return 0 if verified else 1
    if args.output.exists():
        raise ValueError("Supplement report exists; choose another path rather than overwrite evidence")
    report = {"risk_tool_results": run_risk(args.base)}
    if settings.GROQ_API_KEY and settings.GROQ_API_KEY.get_secret_value().strip():
        # Also leave room after a preceding evaluation process's last provider call.
        pause(65)
        engine = make_engine()
        try:
            report["memory_demonstration"] = run_memory(args.base, partial(verify_citation,engine),private_path,secrets)
        finally:
            engine.dispose()
    else:
        report["memory_demonstration"] = {"status":"incomplete_missing_credentials"}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(redact(report,secrets),indent=2),encoding="utf-8")
    print("Risk checks passed:",sum(row["passed"] for row in report["risk_tool_results"]))
    print("Memory history persisted:",report["memory_demonstration"].get("history_persisted",False))
    return 0 if all(row["passed"] for row in report["risk_tool_results"]) and report["memory_demonstration"].get("history_persisted") else 1


if __name__ == "__main__":
    raise SystemExit(main())
