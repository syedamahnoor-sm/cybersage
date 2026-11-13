from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.rag.schemas import AnswerCitation
from app.retrieval.schemas import MAX_QUERY_LENGTH, MAX_TOP_K

RiskValue = Annotated[int, Field(strict=True, ge=1, le=5)]
Capability = Literal["knowledge", "risk", "none"]
AgentStatus = Literal["answered", "assessed", "insufficient_evidence", "missing_input",
                      "needs_clarification", "invalid_input", "error"]


class AgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(strict=True, min_length=1, max_length=MAX_QUERY_LENGTH)
    likelihood: RiskValue | None = None
    impact: RiskValue | None = None
    top_k: int = Field(default=5, strict=True, ge=1, le=MAX_TOP_K)
    conversation_id: UUID | None = None
    request_id: UUID | None = None

    @field_validator("message", mode="before")
    @classmethod
    def strip_message(cls, value):
        return value.strip() if isinstance(value, str) else value


class RiskInputs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    likelihood: RiskValue
    impact: RiskValue


class RiskAssessment(RiskInputs):
    score: int = Field(ge=1, le=25)
    category: Literal["Low", "Medium", "High", "Critical"]
    interpretation: str
    disclaimer: str = "Illustrative qualitative matrix; not a validated prediction of real-world cyber risk."


class AgentProblem(BaseModel):
    code: str
    message: str
    missing_inputs: list[Literal["likelihood", "impact"]] = Field(default_factory=list)


class AgentResponse(BaseModel):
    capability: Capability
    status: AgentStatus
    answer: str | None = None
    assessment: RiskAssessment | None = None
    citations: list[AnswerCitation] = Field(default_factory=list)
    error: AgentProblem | None = None
    model: str | None = None
    retrieved_evidence_count: int = Field(default=0, ge=0)
    selected_evidence_count: int = Field(default=0, ge=0)
    abstention_reason: str | None = None
    conversation_id: UUID | None = None
    request_id: UUID | None = None
    resolved_message: str | None = None
    context_used: bool = False
