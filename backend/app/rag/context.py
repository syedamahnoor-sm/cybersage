"""Select whole passages; retain stable IDs and trusted citation metadata."""

from dataclasses import dataclass
import json
import re

from app.retrieval.schemas import RetrievedChunk

# Defense in depth, not a complete prompt-injection detector. Quarantine a whole
# passage on these obvious instruction attempts rather than editing its meaning.
INSTRUCTION_ATTACK = re.compile(
    r"ignore\s+(?:all\s+)?(?:previous|prior|system)\s+instructions"
    r"|(?:reveal|print|expose)\s+(?:the\s+)?(?:api\s*key|system\s+prompt|secret)"
    r"|<\|(?:system|im_start)\|>", re.IGNORECASE,
)


def normalize(text: str) -> str:
    return " ".join(text.split())


def source_kind(chunk: RetrievedChunk) -> str:
    name = f"{chunk.filename} {chunk.document_title or ''}".lower()
    if "casebook" in name or "synthetic security incident" in chunk.content.lower():
        return "synthetic_incident"
    if "policy" in name:
        return "policy"
    if "nist" in name or "framework" in name:
        return "framework"
    return "source_evidence"


@dataclass(frozen=True)
class Evidence:
    chunk: RetrievedChunk
    evidence_id: str
    text: str
    kind: str

    def prompt_data(self) -> dict:
        # The model never supplies page numbers, titles, or filenames.
        return {"evidence_id": self.evidence_id, "source_kind": self.kind, "text": self.text}


def context_json(evidence: list[Evidence]) -> str:
    return json.dumps([item.prompt_data() for item in evidence], ensure_ascii=True)


def select_evidence(chunks: list[RetrievedChunk], max_chunks: int,
                    max_chars: int) -> list[Evidence]:
    selected = []
    for chunk in chunks:
        text = normalize(chunk.content)
        if not text or INSTRUCTION_ATTACK.search(text):
            continue
        # Remove identical/contained passages, but never merge source metadata.
        if any(text.casefold() in item.text.casefold() for item in selected):
            continue
        item = Evidence(chunk, f"E_{chunk.chunk_id.hex}", text, source_kind(chunk))
        if len(context_json([*selected, item])) <= max_chars:
            selected.append(item)
        if len(selected) == max_chunks:
            break
    return selected
