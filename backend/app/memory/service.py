"""Atomic completed turns, explicit idempotency, and no stored provider failures."""

from hashlib import sha256
import json
import re
from uuid import uuid4

from app.agent.schemas import AgentProblem, AgentRequest, AgentResponse

KEY_PATTERN = re.compile(r"gsk_[A-Za-z0-9]{20,}")


class ConversationService:
    def __init__(self, agent, repository, settings):
        self.agent = agent
        self.repository = repository
        self.settings = settings
        self._secrets = [item.get_secret_value() for item in
                         (settings.GROQ_API_KEY, settings.POSTGRES_PASSWORD)
                         if item and item.get_secret_value()]

    def sensitive(self, text: str) -> bool:
        return bool(KEY_PATTERN.search(text) or any(value in text for value in self._secrets))

    def invoke(self, request: AgentRequest) -> AgentResponse:
        if self.sensitive(request.message):
            return AgentResponse(capability="none", status="invalid_input", error=AgentProblem(
                code="sensitive_input", message="Do not include API keys or configured credentials in messages."))
        request_id = request.request_id or uuid4()
        payload = request.model_dump(mode="json", exclude={"conversation_id", "request_id"})
        digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        # Validate explicit scope/existence even on replay; ownership is not authenticated.
        conversation_id, revision, history = self.repository.snapshot(request.conversation_id,
            self.settings.MEMORY_HISTORY_TURNS, self.settings.MEMORY_HISTORY_CHARS)
        replay = self.repository.replay(request_id, digest, request.conversation_id)
        if replay is not None:
            return replay
        response = self.agent.invoke(request, history=history)
        if response.status in ("error", "invalid_input"):
            # Nothing is committed after failed provider/graph/semantic validation.
            return response.model_copy(update={"conversation_id": request.conversation_id, "request_id": request_id})
        response = response.model_copy(update={"conversation_id": conversation_id, "request_id": request_id})
        if self.sensitive(response.model_dump_json()):
            return AgentResponse(capability="none", status="error", error=AgentProblem(
                code="agent_unavailable", message="The assistant could not safely store this response."))
        return self.repository.commit_turn(conversation_id, revision, request_id, digest, request, response)
