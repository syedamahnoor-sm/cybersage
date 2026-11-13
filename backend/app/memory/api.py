from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.memory.repository import (ConversationConflict, ConversationNotFound,
                                   ConversationRepository, MemoryUnavailableError)
from app.retrieval.api import get_retrieval_service

router = APIRouter(prefix="/api/v1/conversations", tags=["Conversations"])


def get_conversation_repository(request: Request):
    try:
        # Reuse the existing lazily initialized engine and shutdown lifecycle.
        return ConversationRepository(get_retrieval_service(request).engine)
    except Exception:
        raise HTTPException(503, "Conversation storage is temporarily unavailable.") from None


def memory_http_error(error):
    if isinstance(error, ConversationNotFound):
        return HTTPException(404, "Conversation not found.")
    if isinstance(error, ConversationConflict):
        return HTTPException(409, "Conversation or request changed. Retry with consistent inputs.")
    return HTTPException(503, "Conversation storage is temporarily unavailable.")


class HistoryMessage(BaseModel):
    id: UUID
    request_id: UUID
    role: str
    content: str
    metadata: dict
    created_at: datetime
    turn_number: int


class HistoryResponse(BaseModel):
    conversation_id: UUID
    messages: list[HistoryMessage]
    has_more: bool
    next_before_turn: int | None


@router.get("/{conversation_id}/messages", response_model=HistoryResponse)
def history(conversation_id: UUID, limit: int = Query(default=10, ge=1, le=20),
            before_turn: int | None = Query(default=None, ge=1),
            repository: ConversationRepository = Depends(get_conversation_repository)):
    try:
        return repository.history(conversation_id, limit, before_turn)
    except (ConversationNotFound, MemoryUnavailableError) as error:
        raise memory_http_error(error) from None
