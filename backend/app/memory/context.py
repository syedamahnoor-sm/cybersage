"""Deterministic, source-scoped follow-ups. No assistant prose or numerical carryover."""

from dataclasses import dataclass
import re

from app.agent.routing import CALCULATE, RISK
from app.agent.schemas import AgentRequest


@dataclass(frozen=True)
class ContextTurn:
    user_message: str
    resolved_message: str
    capability: str
    status: str


def sources(text: str) -> list[str]:
    result = []
    if re.search(r"\bnist\b|\bcsf\s*2\.0\b", text, re.I):
        result.append("NIST CSF 2.0" if re.search(r"\bcsf\s*2\.0\b", text, re.I) else "NIST")
    if (re.search(r"\bpakistan\b", text, re.I) and re.search(r"\bpolicy\b", text, re.I)
            and re.search(r"\bcyber[\s-]*security\b", text, re.I)):
        result.append("Pakistan's National Cyber Security Policy")
    if re.search(r"\bcybersage\b", text, re.I) and re.search(r"\bcasebook\b", text, re.I):
        result.append("CyberSage casebook")
    return result


FOLLOWUP = re.compile(r"^(?:what|how)\s+about\b|^and\b|\b(?:it|its|they|them|their|this|that|those)\b"
                      r"|\bthe\s+(?:policy|framework|casebook)\b", re.I)


def resolve(request: AgentRequest, history: list[ContextTurn]) -> tuple[str, bool, bool]:
    """Return resolved question, context-used flag, clarification-needed flag."""
    message = request.message
    # Risk inputs must always come from this request. Never consult prior numbers.
    if request.likelihood is not None or request.impact is not None or CALCULATE.search(message):
        return message, False, False
    if sources(message) or not FOLLOWUP.search(message):
        return message, False, False
    # Unknown explicit source references should not be replaced with known history.
    if re.search(r"\b(?:policy|framework|casebook|nist|pakistan)\b", message, re.I):
        return message, False, True
    if not history:
        return message, False, True
    latest = history[-1]
    previous = latest.resolved_message or latest.user_message
    if (re.search(r"\bpakistan\b", previous, re.I) and re.search(r"\bpolicy\b", previous, re.I)
            and not re.search(r"\bcyber[\s-]*security\b", previous, re.I)):
        return message, False, True
    anchors = sources(previous)
    if (latest.capability != "knowledge" or latest.status not in ("answered", "insufficient_evidence")
            or len(anchors) != 1):
        return message, False, True
    anchor = anchors[0]
    about = re.fullmatch(r"(?:what|how)\s+about\s+(.+?)[?.!]*", message, re.I)
    if about:
        topic = about.group(1).rstrip("?.! ")
        # Deictic references without an actual topic remain ambiguous.
        if not topic or re.fullmatch(r"(?:it|that|this|them|those)", topic, re.I) or RISK.search(topic):
            return message, False, True
        resolved = f"What does {anchor} say about {topic}?"
    elif re.search(r"\bit\b", message, re.I):
        resolved = re.sub(r"\bit\b", lambda _: anchor, message, flags=re.I)
    else:
        return message, False, True
    if len(resolved) > 2000:
        return message, False, True
    return resolved, True, False
