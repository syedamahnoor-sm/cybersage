"""Run: python -m app.retrieval --query 'incident response' --top-k 5."""

import argparse
import json

from pydantic import ValidationError

from app.core.config import get_settings
from app.db.connection import make_engine
from app.retrieval.schemas import SearchRequest
from app.retrieval.service import RetrievalService


def main() -> int:
    parser = argparse.ArgumentParser(description="Search CyberSage evidence with PDF page citations")
    parser.add_argument("--query", required=True)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--min-similarity", type=float, default=None)
    args = parser.parse_args()
    try:
        request = SearchRequest(query=args.query, top_k=args.top_k,
                                min_similarity=args.min_similarity)
    except ValidationError:
        print("Invalid search: provide a nonblank query (max 2000 characters), "
              "top-k 1..20, and optional finite similarity -1..1.")
        return 2
    engine = None
    try:
        engine = make_engine()
        response = RetrievalService(engine, get_settings().RETRIEVAL_MIN_SIMILARITY).search(
            request.query, request.top_k, request.min_similarity,
        )
        # ASCII JSON escapes preserve PDF Unicode through Windows shell pipes.
        print(json.dumps(response.model_dump(mode="json"), indent=2))
        return 0
    except Exception:
        print("Retrieval is temporarily unavailable. Check local model and database setup.")
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
