import argparse
from functools import partial
import json
from importlib.metadata import version
from pathlib import Path

from app.core.config import get_settings
from app.db.connection import make_engine
from evaluation.dataset import load_dataset, verify_ground_truth
from evaluation.provenance import verify_citation
from evaluation.runner import run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8001")
    parser.add_argument("--output", type=Path, default=Path("evaluation/results/milestone9.json"))
    parser.add_argument("--pause-seconds", type=float, default=65)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    settings = get_settings()
    dataset = load_dataset()
    manifest = verify_ground_truth(dataset)
    print(json.dumps({"verified_source_manifest": manifest}))
    engine = make_engine()
    try:
        secrets = [value.get_secret_value() for value in (settings.GROQ_API_KEY, settings.POSTGRES_PASSWORD)
                   if value and value.get_secret_value()]
        report = run(dataset, args.output, args.base, partial(verify_citation, engine), secrets,
            args.pause_seconds, resume=args.resume,
            credential_available=bool(settings.GROQ_API_KEY and settings.GROQ_API_KEY.get_secret_value().strip()))
        report["source_manifest"] = manifest
        report["public_configuration"] = {name: getattr(settings, name) for name in (
            "GROQ_MODEL", "GROQ_TEMPERATURE", "GROQ_TIMEOUT_SECONDS", "GROQ_MAX_OUTPUT_TOKENS",
            "RETRIEVAL_MIN_SIMILARITY", "RAG_MAX_RETRIEVED_CHUNKS", "RAG_MAX_CONTEXT_CHARS",
            "RAG_MAX_PROMPT_CHARS", "MEMORY_HISTORY_TURNS", "MEMORY_HISTORY_CHARS")}
        report["package_versions"] = {name: version(name) for name in (
            "groq", "langgraph", "sqlalchemy", "psycopg", "sentence-transformers", "fastapi")}
        from evaluation.runner import redact
        args.output.write_text(json.dumps(redact(report, secrets), indent=2), encoding="utf-8")
        return 0 if report["overall_status"] == "complete" else 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
