"""Conservative English routing; text can select only two fixed capabilities."""

import re

from app.agent.schemas import AgentRequest

SOURCE = re.compile(r"\b(nist|csf|policy|policies|framework|casebook|documents?)\b", re.I)
CALCULATE = re.compile(r"\b(calculate|compute|score|assess|evaluate|estimate)\b[^.!?]{0,60}\brisk\b", re.I)
RISK = re.compile(r"\b(risk|likelihood|impact)\b", re.I)
TOPIC = re.compile(r"\b(cybersecurity|cyber|security|ransomware|incident|malware|phishing|threat|"
                   r"network|vulnerability|encryption|authentication|backup|firewall|breach)\b", re.I)
QUESTION = re.compile(r"^(what|how|why|when|which|does|do|describe|explain|summari[sz]e|according)\b", re.I)


def select_capability(request: AgentRequest) -> str:
    text = request.message
    supplied = request.likelihood is not None or request.impact is not None
    source = bool(SOURCE.search(text))
    calculation = bool(CALCULATE.search(text))
    if source and (supplied or calculation):
        return "mixed"
    if source:
        return "knowledge"
    if supplied or calculation:
        return "risk"
    if TOPIC.search(text) and QUESTION.search(text):
        return "knowledge"
    if RISK.search(text):
        # Conceptual questions without numerical intent need disambiguation.
        return "risk" if not QUESTION.search(text) else "ambiguous"
    return "ambiguous"


class RiskTextError(ValueError):
    def __init__(self, conflict=False):
        super().__init__("Conflicting risk inputs" if conflict else "Invalid risk inputs")
        self.conflict = conflict


def risk_values(request: AgentRequest) -> dict:
    values = {}
    for label in ("likelihood", "impact"):
        matches = re.findall(
            rf"\b{label}\b\s*(?:[:=]|\b(?:is|of)\b)?\s*([^\s,;]+)", request.message, re.I,
        )
        if len(matches) > 1:
            raise RiskTextError(conflict=True)
        explicit = getattr(request, label)
        if matches:
            token = matches[0].rstrip(".!?")
            if not re.fullmatch(r"[1-5]", token):
                raise RiskTextError()
            parsed = int(token)
            if explicit is not None and explicit != parsed:
                raise RiskTextError(conflict=True)
            values[label] = parsed
        elif explicit is not None:
            values[label] = explicit
    return values
