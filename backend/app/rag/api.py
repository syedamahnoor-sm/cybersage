from threading import Lock

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.config import get_settings
from app.llm.base import LLMUnavailableError
from app.llm.groq_provider import GroqProvider
from app.rag.schemas import AskRequest, AskResponse
from app.rag.service import RAGService
from app.retrieval.api import get_retrieval_service
from app.retrieval.service import RetrievalService, RetrievalUnavailableError

router = APIRouter(prefix="/api/v1/rag", tags=["RAG"])
_provider_lock = Lock()


def get_rag_service(request: Request,
                    retrieval: RetrievalService = Depends(get_retrieval_service)) -> RAGService:
    with _provider_lock:
        provider = getattr(request.app.state, "llm_provider", None)
        if provider is None:
            provider = GroqProvider(get_settings())
            request.app.state.llm_provider = provider
    return RAGService(retrieval, provider, get_settings())


@router.post("/ask", response_model=AskResponse,
             responses={503: {"description": "Retrieval or generation unavailable"},
                        504: {"description": "Generation timed out"}})
def ask(request: AskRequest, service: RAGService = Depends(get_rag_service)) -> AskResponse:
    try:
        return service.ask(request.question, request.top_k)
    except LLMUnavailableError as error:
        code = 504 if error.kind == "timeout" else 503
        raise HTTPException(status_code=code, detail="Answer generation is temporarily unavailable.") from None
    except RetrievalUnavailableError:
        raise HTTPException(status_code=503, detail="Retrieval is temporarily unavailable.") from None
