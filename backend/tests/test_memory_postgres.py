from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.agent.schemas import AgentRequest, AgentResponse
from app.agent.service import AgentService
from app.core.config import Settings
from app.llm.base import LLMUnavailableError
from app.memory.repository import (ConversationConflict, ConversationNotFound,
                                   ConversationRepository, MemoryUnavailableError)
from app.memory.service import ConversationService
from app.memory.tables import conversations, messages, turns
from app.rag.schemas import AskResponse


class FakeRAG:
    def __init__(self):
        self.questions = []
    def ask(self, question, top_k):
        self.questions.append(question)
        return AskResponse(question=question, answer="An answer that is never used as evidence.",
            status="answered", citations=[], retrieved_evidence_count=1, selected_evidence_count=1)


@pytest.fixture
def service(memory_database):
    engine, connection = memory_database
    rag = FakeRAG()
    repository = ConversationRepository(engine)
    service = ConversationService(AgentService(lambda: rag), repository, Settings(_env_file=None))
    return service, repository, connection, rag


def test_turn_persistence_followup_original_message_and_restart(service, memory_database):
    service, repository, connection, rag = service
    first = service.invoke(AgentRequest(message="What does NIST CSF 2.0 say about incident response?"))
    # Reconstruct services to simulate loss of all in-process state.
    restarted = ConversationService(AgentService(lambda: rag), ConversationRepository(memory_database[0]),
                                    Settings(_env_file=None))
    second = restarted.invoke(AgentRequest(message="What about recovery?", conversation_id=first.conversation_id))
    assert second.resolved_message == "What does NIST CSF 2.0 say about recovery?"
    assert second.context_used and len(rag.questions) == 2
    history = repository.history(first.conversation_id, 10, None)
    assert [row["role"] for row in history["messages"]] == ["user", "assistant", "user", "assistant"]
    assert history["messages"][2]["content"] == "What about recovery?"
    assert history["messages"][3]["metadata"]["resolved_message"] == second.resolved_message
    assert all(row["created_at"] for row in history["messages"])


def test_cross_conversation_isolation_and_unknown_ids(service):
    service, repository, _, rag = service
    a = service.invoke(AgentRequest(message="What does NIST CSF 2.0 say?"))
    b = service.invoke(AgentRequest(message="What does Pakistan's National Cyber Security Policy say?"))
    response = service.invoke(AgentRequest(message="What response measures does it describe?", conversation_id=b.conversation_id))
    assert "Pakistan" in response.resolved_message and "NIST" not in response.resolved_message
    assert len(repository.history(a.conversation_id, 10, None)["messages"]) == 2
    with pytest.raises(ConversationNotFound):
        service.invoke(AgentRequest(message="What about recovery?", conversation_id=uuid4()))


def test_idempotency_new_and_existing_conversation_and_conflicts(service):
    service, repository, connection, rag = service
    key = uuid4()
    request = AgentRequest(message="What does NIST say?", request_id=key)
    first = service.invoke(request)
    assert service.invoke(request) == first
    assert service.invoke(request.model_copy(update={"conversation_id": first.conversation_id})) == first
    assert len(rag.questions) == 1
    assert connection.scalar(select(func.count()).select_from(messages)) == 2
    assert connection.scalar(select(func.count()).select_from(conversations)) == 1
    with pytest.raises(ConversationConflict):
        service.invoke(AgentRequest(message="A different request", request_id=key))
    other = service.invoke(AgentRequest(message="Calculate risk", likelihood=1, impact=2))
    with pytest.raises(ConversationConflict):
        service.invoke(request.model_copy(update={"conversation_id": other.conversation_id}))


def test_history_and_context_bounds(service):
    service, repository, _, _ = service
    first = service.invoke(AgentRequest(message="What does NIST CSF 2.0 say?"))
    for _ in range(3):
        service.invoke(AgentRequest(message="What about recovery?", conversation_id=first.conversation_id))
    cid, revision, history = repository.snapshot(first.conversation_id, 2, 8000)
    assert len(history) == 2 and revision == 4
    assert repository.snapshot(cid, 6, 1)[2] == []
    page = repository.history(cid, 2, None)
    assert page["has_more"] and len(page["messages"]) == 4
    assert len(repository.history(cid, 2, page["next_before_turn"])["messages"]) == 4


def test_failed_provider_does_not_save_or_advance_revision(service):
    service, repository, connection, _ = service
    first = service.invoke(AgentRequest(message="Calculate risk", likelihood=4, impact=5))
    def failure():
        raise LLMUnavailableError("timeout")
    service.agent = AgentService(failure)
    result = service.invoke(AgentRequest(message="What does NIST say?", conversation_id=first.conversation_id))
    assert result.status == "error" and result.conversation_id == first.conversation_id
    assert connection.scalar(select(func.count()).select_from(messages)) == 2
    assert connection.scalar(select(conversations.c.revision)) == 1


def test_failed_message_insert_rolls_back_entire_new_turn(service):
    _, repository, connection, _ = service
    request = AgentRequest(message="What does NIST say?")
    cid, revision, _ = repository.snapshot(None, 6, 8000)
    response = AgentResponse(capability="knowledge", status="answered", answer="x" * 20001)
    with pytest.raises(MemoryUnavailableError):
        repository.commit_turn(cid, revision, uuid4(), "a" * 64, request, response)
    for table in (conversations, turns, messages):
        assert connection.scalar(select(func.count()).select_from(table)) == 0


def test_optimistic_concurrency_rejects_stale_turn(service):
    service, repository, connection, _ = service
    first = service.invoke(AgentRequest(message="Calculate risk", likelihood=1, impact=2))
    cid, revision, _ = repository.snapshot(first.conversation_id, 6, 8000)
    request = AgentRequest(message="Calculate risk", likelihood=2, impact=3, conversation_id=cid)
    response = AgentResponse(capability="risk", status="assessed")
    repository.commit_turn(cid, revision, uuid4(), "a" * 64, request, response)
    with pytest.raises(ConversationConflict):
        repository.commit_turn(cid, revision, uuid4(), "b" * 64, request, response)
    assert connection.scalar(select(conversations.c.revision)) == 2
    assert connection.scalar(select(func.count()).select_from(messages)) == 4


def test_racing_retry_for_new_conversation_replays_without_orphans(service):
    service, repository, connection, _ = service
    request = AgentRequest(message="Calculate risk", likelihood=4, impact=5, request_id=uuid4())
    first = service.invoke(request)
    digest = connection.scalar(select(turns.c.request_hash))
    new_id, revision, _ = repository.snapshot(None, 6, 8000)
    result = repository.commit_turn(new_id, revision, request.request_id, digest, request, first)
    assert result == first
    assert connection.scalar(select(func.count()).select_from(conversations)) == 1
    assert connection.scalar(select(func.count()).select_from(messages)) == 2


def test_failed_existing_turn_insert_keeps_revision_and_messages(service):
    service, repository, connection, _ = service
    first = service.invoke(AgentRequest(message="Calculate risk", likelihood=4, impact=5))
    request = AgentRequest(message="What does NIST say?", conversation_id=first.conversation_id)
    response = AgentResponse(capability="knowledge", status="answered", answer="x" * 20001)
    with pytest.raises(MemoryUnavailableError):
        repository.commit_turn(first.conversation_id, 1, uuid4(), "a" * 64, request, response)
    assert connection.scalar(select(conversations.c.revision)) == 1
    assert connection.scalar(select(func.count()).select_from(messages)) == 2
