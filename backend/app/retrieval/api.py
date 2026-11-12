"""FastAPI transport for retrieval; embedding and DB work run in a worker thread."""

from threading import Lock

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.config import get_settings
from app.db.connection import make_engine
from app.retrieval.schemas import SearchRequest, SearchResponse
from app.retrieval.service import RetrievalService, RetrievalUnavailableError

router = APIRouter(prefix="/api/v1/retrieval", tags=["Retrieval"])
_engine_lock = Lock()


def get_retrieval_service(request: Request) -> RetrievalService:
    try:
        with _engine_lock:
            engine = getattr(request.app.state, "retrieval_engine", None)
            if engine is None:
                engine = make_engine()
                request.app.state.retrieval_engine = engine
        return RetrievalService(engine, get_settings().RETRIEVAL_MIN_SIMILARITY)
    except Exception:
        raise HTTPException(status_code=503, detail="Retrieval is temporarily unavailable.") from None


@router.post("/search", response_model=SearchResponse,
             responses={503: {"description": "Model or database temporarily unavailable"}})
def search(request: SearchRequest,
           service: RetrievalService = Depends(get_retrieval_service)) -> SearchResponse:
    try:
        return service.search(request.query, request.top_k, request.min_similarity)
    except RetrievalUnavailableError:
        raise HTTPException(status_code=503, detail="Retrieval is temporarily unavailable.") from None
