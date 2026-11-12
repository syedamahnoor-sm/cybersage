"""Validated retrieval inputs, evidence, and PDF citation metadata."""

from uuid import UUID
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_QUERY_LENGTH = 2000
MAX_TOP_K = 20


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(strict=True, min_length=1, max_length=MAX_QUERY_LENGTH)
    top_k: int = Field(default=5, strict=True, ge=1, le=MAX_TOP_K)
    min_similarity: float | None = Field(
        default=None, strict=True, ge=-1, le=1, allow_inf_nan=False,
        description="Cosine similarity cutoff, not a calibrated probability. "
                    "Omit to use the server setting.",
    )

    @field_validator("query", mode="before")
    @classmethod
    def strip_query(cls, value):
        return value.strip() if isinstance(value, str) else value


class Citation(BaseModel):
    document_id: UUID
    document_title: str | None
    filename: str
    page_number: int = Field(ge=1)
    display_title: str
    title_source: Literal["metadata", "filename"]
    label: str


class RetrievedChunk(BaseModel):
    chunk_id: UUID
    document_id: UUID
    document_title: str | None
    filename: str
    page_number: int = Field(ge=1)
    chunk_index: int = Field(ge=0)
    content: str
    cosine_distance: float = Field(ge=0, le=2, allow_inf_nan=False)
    similarity_score: float = Field(ge=-1, le=1, allow_inf_nan=False)
    citation: Citation


class SearchResponse(BaseModel):
    query: str
    results: list[RetrievedChunk]
    result_count: int = Field(ge=0)
    min_similarity: float
