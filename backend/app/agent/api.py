from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.agent.schemas import AgentRequest, AgentResponse
from app.agent.service import AgentService
from app.rag.api import get_rag_service
from app.retrieval.api import get_retrieval_service
from app.retrieval.service import RetrievalUnavailableError
from app.core.config import get_settings
from app.memory.api import get_conversation_repository, memory_http_error
from app.memory.repository import ConversationConflict, ConversationNotFound, MemoryUnavailableError
from app.memory.service import ConversationService

router = APIRouter(prefix="/api/v1/agent", tags=["Agent"])


def get_agent_service(request: Request) -> AgentService:
    def rag_factory():
        # Lazy composition reuses the existing RAG, engine, provider, and shutdown
        # lifecycle. Risk execution skips RAG; conversation storage still uses PostgreSQL.
        try:
            return get_rag_service(request, get_retrieval_service(request))
        except HTTPException:
            raise RetrievalUnavailableError("Retrieval is temporarily unavailable.") from None
    return AgentService(rag_factory)


def get_memory_agent_service(agent: AgentService = Depends(get_agent_service),
                             repository=Depends(get_conversation_repository)) -> ConversationService:
    return ConversationService(agent, repository, get_settings())


@router.post("/invoke", response_model=AgentResponse,
             responses={500: {"description": "Bounded agent execution failed"},
                        404: {"description": "Conversation not found"},
                        409: {"description": "Concurrent turn or idempotency conflict"},
                        503: {"description": "Knowledge or conversation storage unavailable"},
                        504: {"description": "Answer generation timed out"}})
def invoke(request: AgentRequest, service: ConversationService = Depends(get_memory_agent_service)):
    try:
        response = service.invoke(request)
    except (ConversationConflict, ConversationNotFound, MemoryUnavailableError) as error:
        raise memory_http_error(error) from None
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
