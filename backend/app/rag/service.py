"""Provider-neutral orchestration with fail-closed evidence validation."""

import json

from pydantic import ValidationError

from app.core.config import Settings
from app.llm.base import InvalidModelOutputError, LLMProvider
from app.rag.context import INSTRUCTION_ATTACK, normalize, select_evidence
from app.rag.prompts import SELECT_PROMPT, VERIFY_PROMPT
from app.rag.schemas import AnswerCitation, AskRequest, AskResponse, DraftAnswer, RelevanceVerdict
from app.retrieval.service import make_citation

ABSTENTION = "The available source evidence is insufficient to answer this question reliably."
MAX_MODEL_JSON_CHARS = 65536
SOURCE_LABELS = {
    "policy": "Policy source",
    "framework": "Framework guidance",
    "synthetic_incident": "Synthetic incident example (not a real event)",
    "source_evidence": "Source excerpt (source type unverified)",
}


class ContextLimitError(ValueError):
    pass


class RAGService:
    def __init__(self, retrieval, provider: LLMProvider, settings: Settings):
        self.retrieval = retrieval
        self.provider = provider
        self.settings = settings

    def _generate(self, system: str, payload: dict) -> str:
        data = json.dumps(payload, ensure_ascii=True)
        if len(system) + len(data) > self.settings.RAG_MAX_PROMPT_CHARS:
            raise ContextLimitError()
        output = self.provider.generate_json(system, data)
        if len(output) > MAX_MODEL_JSON_CHARS:
            raise InvalidModelOutputError("Oversized response")
        return output

    def ask(self, question: str, top_k: int = 5) -> AskResponse:
        request = AskRequest(question=question, top_k=top_k)
        retrieved = self.retrieval.search(
            request.question, min(request.top_k, self.settings.RAG_MAX_RETRIEVED_CHUNKS),
        )
        selected = select_evidence(retrieved.results, self.settings.RAG_MAX_RETRIEVED_CHUNKS,
                                   self.settings.RAG_MAX_CONTEXT_CHARS)
        model = None

        def abstain(reason: str) -> AskResponse:
            return AskResponse(
                question=request.question, answer=ABSTENTION, status="insufficient_evidence",
                citations=[], retrieved_evidence_count=len(retrieved.results),
                selected_evidence_count=len(selected), model=model, abstention_reason=reason,
            )

        if not retrieved.results:
            return abstain("no_evidence")
        if not selected:
            return abstain("context_unusable")
        payload = {"question": request.question,
                   "evidence": [item.prompt_data() for item in selected]}
        generation_completed = False
        try:
            model = self.provider.model
            draft = DraftAnswer.model_validate_json(self._generate(SELECT_PROMPT, payload))
            generation_completed = True
            if draft.status == "insufficient_evidence":
                return abstain("model_abstained")
            if not draft.claims:
                return abstain("invalid_output")
            by_id = {item.evidence_id: item for item in selected}
            citations = []
            seen = set()
            for claim in draft.claims:
                item = by_id.get(claim.evidence_id)
                quote = normalize(claim.quote)
                if item is None:
                    return abstain("invalid_citations")
                if (len(quote) < 20 or quote not in item.text or INSTRUCTION_ATTACK.search(quote)
                        or quote.endswith(("\u2019", "'", "-", "\u2013", "\u2014", ",", ":"))):
                    return abstain("unsupported_evidence")
                if (claim.evidence_id, quote) in seen:
                    continue
                seen.add((claim.evidence_id, quote))
                chunk = item.chunk
                citation = make_citation(chunk.model_dump())
                citations.append(AnswerCitation(
                    **citation.model_dump(), evidence_id=item.evidence_id,
                    chunk_id=str(chunk.chunk_id), chunk_index=chunk.chunk_index,
                    quote=quote, source_kind=item.kind,
                ))
            verdict = RelevanceVerdict.model_validate_json(self._generate(VERIFY_PROMPT, {
                **payload, "claims": [claim.model_dump() for claim in draft.claims],
            }))
            if (not verdict.supported or not verdict.relevant
                    or set(verdict.evidence_ids) != {item.evidence_id for item in citations}):
                return abstain("unsupported_evidence")
        except ContextLimitError:
            if not generation_completed:
                model = None
            return abstain("context_limit")
        except (ValidationError, InvalidModelOutputError):
            return abstain("invalid_output")
        # Render only locally verified source quotes and database-derived labels.
        # No free-form generated prose, page numbers, or titles are returned.
        answer = "\n\n".join(
            f"{SOURCE_LABELS[citation.source_kind]}: \"{citation.quote}\" "
            f"{citation.label} ({citation.evidence_id})" for citation in citations
        )
        return AskResponse(
            question=request.question, answer=answer, status="answered", citations=citations,
            retrieved_evidence_count=len(retrieved.results), selected_evidence_count=len(selected),
            model=model,
        )
