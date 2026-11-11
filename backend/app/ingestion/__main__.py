"""Run with python -m app.ingestion from backend/."""

import argparse
import json
from pathlib import Path

from app.db.connection import check_database, make_engine
from app.db.verification import verify_documents
from app.ingestion.pipeline import DEFAULT_INPUT_DIR, discover_pdfs, hash_pdf, ingest_directory


def positive_integer(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def main() -> int:
    parser = argparse.ArgumentParser(description="Index local PDFs into CyberSage PostgreSQL")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--batch-size", type=positive_integer, default=32)
    parser.add_argument("--check-db", action="store_true", help="Check database and exit")
    parser.add_argument("--verify", action="store_true", help="Verify source records without ingestion")
    args = parser.parse_args()
    engine = None
    try:
        engine = make_engine()
        print(json.dumps({"database": check_database(engine)}))
        if args.check_db:
            return 0
        paths = discover_pdfs(args.input_dir)
        if not paths:
            print("No PDF files found in input directory.")
            return 1
        if args.verify:
            report = verify_documents(engine, [hash_pdf(path) for path in paths])
            print(json.dumps(report, indent=2))
            checks = report["source_checks"]
            valid = (len(report["source_documents"]) == len({hash_pdf(path) for path in paths})
                     and all(row["status"] == "indexed" and row["chunks"] > 0
                             for row in report["source_documents"])
                     and all(value == 0 for name, value in checks.items() if name != "chunks"))
            return 0 if valid else 1
        summary = ingest_directory(engine, args.input_dir, args.batch_size)
        for result in summary.results:
            print(json.dumps(vars(result)))
        print(json.dumps(summary.as_dict()))
        return 1 if summary.as_dict()["failures"] else 0
    except Exception as error:
        # Never print driver exceptions, SQL parameters, or secret settings.
        print(f"Command failed ({type(error).__name__}). Check database settings, "
              "connectivity, schema, and input directory.")
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
