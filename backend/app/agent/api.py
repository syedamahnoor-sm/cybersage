from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.agent.schemas import AgentRequest, AgentResponse
from app.agent.service import AgentService
from app.rag.api import get_rag_service
from app.retrieval.api import get_retrieval_service
from app.retrieval.service import RetrievalUnavailableError

router = APIRouter(prefix="/api/v1/agent", tags=["Agent"])


def get_agent_service(request: Request) -> AgentService:
    def rag_factory():
        # Lazy composition reuses the existing RAG, engine, provider, and shutdown
        # lifecycle. Pure risk requests require neither database nor credentials.
        try:
            return get_rag_service(request, get_retrieval_service(request))
        except HTTPException:
            raise RetrievalUnavailableError("Retrieval is temporarily unavailable.") from None
    return AgentService(rag_factory)


@router.post("/invoke", response_model=AgentResponse,
             responses={500: {"description": "Bounded agent execution failed"},
                        503: {"description": "Knowledge service unavailable"},
                        504: {"description": "Answer generation timed out"}})
def invoke(request: AgentRequest, service: AgentService = Depends(get_agent_service)):
    response = service.invoke(request)
    code = 200
    if response.status == "invalid_input":
        code = 422
    elif response.error:
        code = {"generation_timeout": 504, "generation_unavailable": 503,
                "retrieval_unavailable": 503, "agent_unavailable": 500,
                "execution_limit": 500}.get(response.error.code, 200)
    if code != 200:
        return JSONResponse(status_code=code, content=response.model_dump(mode="json"))
    return response
