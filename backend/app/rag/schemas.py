from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.retrieval.schemas import Citation, MAX_QUERY_LENGTH, MAX_TOP_K

SourceKind = Literal["policy", "framework", "synthetic_incident", "source_evidence"]


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(strict=True, min_length=1, max_length=MAX_QUERY_LENGTH)
    top_k: int = Field(default=5, strict=True, ge=1, le=MAX_TOP_K)

    @field_validator("question", mode="before")
    @classmethod
    def strip_question(cls, value):
        return value.strip() if isinstance(value, str) else value


class ExcerptClaim(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    evidence_id: str = Field(min_length=1, max_length=40)
    quote: str = Field(min_length=20, max_length=1200)


class DraftAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    status: Literal["answered", "insufficient_evidence"]
    claims: list[ExcerptClaim] = Field(max_length=5)


class RelevanceVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    supported: bool
    relevant: bool
    evidence_ids: list[str] = Field(max_length=5)


class AnswerCitation(Citation):
    evidence_id: str
    chunk_id: str
    chunk_index: int = Field(ge=0)
    quote: str
    source_kind: SourceKind


class AskResponse(BaseModel):
    question: str
    answer: str
    status: Literal["answered", "insufficient_evidence"]
    citations: list[AnswerCitation]
    retrieved_evidence_count: int = Field(ge=0)
    selected_evidence_count: int = Field(ge=0)
    model: str | None = None
    grounding_mode: Literal["verified_excerpts"] = "verified_excerpts"
    abstention_reason: str | None = None
