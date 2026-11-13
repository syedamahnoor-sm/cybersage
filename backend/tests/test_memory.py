from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.agent.schemas import AgentRequest, AgentResponse
from app.agent.service import AgentService
from app.core.config import Settings
from app.memory.context import ContextTurn
from app.memory.service import ConversationService
from app.rag.schemas import AskResponse


@pytest.fixture
def memory():
    repository = Mock()
    repository.snapshot.return_value = (uuid4(), None, [])
    repository.replay.return_value = None
    repository.commit_turn.side_effect = lambda *args: args[-1]
    agent = Mock()
    agent.invoke.return_value = AgentResponse(capability="risk", status="assessed")
    return ConversationService(agent, repository, Settings(_env_file=None)), agent, repository


def test_new_conversation_and_request_ids_are_returned(memory):
    service, agent, repository = memory
    response = service.invoke(AgentRequest(message="Calculate risk", likelihood=4, impact=5))
    assert response.conversation_id == repository.snapshot.return_value[0]
    assert response.request_id is not None
    agent.invoke.assert_called_once()
    repository.commit_turn.assert_called_once()


def test_replay_does_not_regenerate_or_save_duplicate(memory):
    service, agent, repository = memory
    cached = AgentResponse(capability="knowledge", status="answered", answer="Stored answer")
    repository.replay.return_value = cached
    assert service.invoke(AgentRequest(message="What does NIST say?", request_id=uuid4())) == cached
    agent.invoke.assert_not_called()
    repository.commit_turn.assert_not_called()


def test_provider_error_is_never_saved(memory):
    service, agent, repository = memory
    agent.invoke.return_value = AgentResponse(capability="knowledge", status="error")
    response = service.invoke(AgentRequest(message="What does NIST say?"))
    assert response.conversation_id is None
    repository.commit_turn.assert_not_called()


def test_secrets_are_rejected_before_storage_or_model(memory):
    service, agent, repository = memory
    response = service.invoke(AgentRequest(message="Here is gsk_" + "a" * 32))
    assert response.status == "invalid_input"
    assert "gsk_" not in response.model_dump_json()
    repository.snapshot.assert_not_called()
    agent.invoke.assert_not_called()


def test_followup_passes_only_resolved_question_to_fresh_rag():
    rag = Mock()
    rag.ask.return_value = AskResponse(question="resolved", answer="Fresh evidence.", status="answered",
        citations=[], retrieved_evidence_count=1, selected_evidence_count=1)
    agent = AgentService(lambda: rag)
    history = [ContextTurn("What does NIST CSF 2.0 say about incident response?",
                          "What does NIST CSF 2.0 say about incident response?", "knowledge", "answered")]
    response = agent.invoke({"message": "What about recovery?"}, history=history)
    assert response.context_used is True
    rag.ask.assert_called_once_with("What does NIST CSF 2.0 say about recovery?", 5)


def test_risk_followup_requires_current_impact():
    agent = AgentService(Mock(side_effect=AssertionError("No RAG")))
    history = [ContextTurn("Calculate risk likelihood 4 impact 5", "Calculate risk likelihood 4 impact 5", "risk", "assessed")]
    response = agent.invoke({"message": "Calculate risk", "likelihood": 2}, history=history)
    assert response.status == "missing_input" and response.error.missing_inputs == ["impact"]
