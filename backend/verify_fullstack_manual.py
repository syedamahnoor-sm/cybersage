"""Audit the opt-in live browser run; never print credentials or history-access IDs."""

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import text

from app.core.config import get_settings
from app.db.connection import check_database, make_engine
from evaluation.provenance import verify_citation
from evaluation.runner import redact

ROOT = Path(__file__).resolve().parents[1]


def audit(private_path: Path, destination: Path) -> dict:
    # Node writes UTF-8 JSON. Windows' locale default can corrupt bullet characters.
    run = json.loads(private_path.read_text(encoding="utf-8"))
    if not run.get("completed"):
        raise RuntimeError("The live browser run is incomplete")
    engine = make_engine()
    try:
        database = check_database(engine)
        checks = [verify_citation(engine, citation, SimpleNamespace(
            expected_source="NIST.CSWP.29.pdf", expected_pages=[20, 27, 28]))
            for scenario in run["scenarios"]
            for citation in scenario.get("response", {}).get("citations", [])]
        if not checks or not all(c["provenance_valid"] and c["source_relevant"] for c in checks):
            raise RuntimeError("Live citation provenance audit failed")
        with engine.connect() as connection:
            corpus = {
                "documents": connection.scalar(text("SELECT count(*) FROM documents")),
                "chunks": connection.scalar(text("SELECT count(*) FROM document_chunks")),
                "indexed": connection.scalar(text("SELECT count(*) FROM documents WHERE status='indexed'")),
            }
    finally:
        engine.dispose()
    settings = get_settings()
    secrets = [v.get_secret_value() for v in (settings.GROQ_API_KEY, settings.POSTGRES_PASSWORD)
               if v and v.get_secret_value()]
    files = [p for p in (ROOT / "frontend/.next/static").rglob("*") if p.is_file()]
    if not files:
        raise RuntimeError("Build the frontend before auditing browser bundles")
    if any(any(secret.encode() in path.read_bytes() for secret in secrets) for path in files):
        raise RuntimeError("Configured secret detected in browser output")
    report = redact(run, secrets)
    report.update(citation_audit=checks, corpus_after_run=corpus, database=database,
                  browser_bundle_secret_review={"files_checked": len(files), "configured_secrets_found": False})
    content = json.dumps(report, indent=2)
    access_ids = [s.get("response", {}).get("conversation_id") for s in run["scenarios"]]
    if any(cid and cid in content for cid in access_ids):
        raise RuntimeError("Private conversation ID remains in public output")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "frontend/.cache/milestone11/live-private.json")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/milestone11-live-results.json")
    args = parser.parse_args()
    report = audit(args.input, args.output)
    print("Verified source quotes:", len(report["citation_audit"]))
    print("Corpus:", report["corpus_after_run"])
    print("Browser bundle files checked:", report["browser_bundle_secret_review"]["files_checked"])
    print("No configured secrets or private conversation IDs in public evidence.")


if __name__ == "__main__":
    main()
