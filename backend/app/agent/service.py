"""Acyclic StateGraph with explicit validation, routing, execution, and errors."""

from collections.abc import Callable
from typing import TypedDict

from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from app.agent.risk import assess_risk
from app.agent.routing import RiskTextError, risk_values, select_capability
from app.agent.schemas import AgentProblem, AgentRequest, AgentResponse, RiskAssessment
from app.llm.base import LLMUnavailableError
from app.rag.schemas import AskResponse
from app.rag.service import RAGService
from app.retrieval.service import RetrievalUnavailableError

MAX_GRAPH_STEPS = 8


class AgentState(TypedDict, total=False):
    raw_request: dict
    request: AgentRequest
    capability: str
    status: str
    risk_inputs: dict
    rag_result: AskResponse
    assessment: RiskAssessment
    problem: AgentProblem
    response: AgentResponse


def problem(status: str, code: str, message: str, **extra) -> dict:
    return {"status": status, "problem": AgentProblem(code=code, message=message, **extra)}


class AgentService:
    def __init__(self, rag_factory: Callable[[], RAGService]):
        self._rag_factory = rag_factory
        builder = StateGraph(AgentState)
        builder.add_node("validate", self._validate)
        builder.add_node("select", self._select)
        builder.add_node("rag", self._rag)
        builder.add_node("risk", self._risk)
        builder.add_node("error", self._error)
        builder.add_node("format", self._format)
        builder.add_edge(START, "validate")
        builder.add_conditional_edges("validate", lambda s: "error" if s.get("problem") else "select",
                                      {"error": "error", "select": "select"})
        builder.add_conditional_edges("select", lambda s: "error" if s.get("problem") else s["capability"],
                                      {"error": "error", "knowledge": "rag", "risk": "risk"})
        for node in ("rag", "risk"):
            builder.add_conditional_edges(node, lambda s: "error" if s.get("problem") else "format",
                                          {"error": "error", "format": "format"})
        builder.add_edge("error", "format")
        builder.add_edge("format", END)
        # No checkpointer, persistent store, tool dispatcher, or looping edges.
        self._graph = builder.compile()

    def _validate(self, state: AgentState) -> dict:
        try:
            request = AgentRequest.model_validate(state["raw_request"])
            return {"request": request, "capability": "none"}
        except (ValidationError, TypeError):
            return {"capability": "none", **problem(
                "invalid_input", "invalid_request", "Provide a nonblank message up to 2000 characters, "
                "top_k 1..20, and optional integer likelihood/impact 1..5.")}

    def _select(self, state: AgentState) -> dict:
        request = state["request"]
        capability = select_capability(request)
        if capability in ("mixed", "ambiguous"):
            return {"capability": "none", **problem(
                "needs_clarification", "ambiguous_request",
                "Ask one document-grounded cybersecurity question, or request a risk calculation "
                "with likelihood and impact. Send mixed requests separately.")}
        if capability == "knowledge":
            return {"capability": "knowledge"}
        try:
            values = risk_values(request)
        except RiskTextError as error:
            return {"capability": "risk", **problem(
                "needs_clarification" if error.conflict else "invalid_input",
                "conflicting_risk_inputs" if error.conflict else "invalid_risk_inputs",
                "Provide one consistent integer from 1 to 5 for each of likelihood and impact.")}
        missing = [label for label in ("likelihood", "impact") if label not in values]
        if missing:
            return {"capability": "risk", **problem(
                "missing_input", "missing_risk_inputs", "Provide the missing risk inputs: " + ", ".join(missing),
                missing_inputs=missing)}
        return {"capability": "risk", "risk_inputs": values}

    def _rag(self, state: AgentState) -> dict:
        try:
            request = state["request"]
            result = self._rag_factory().ask(request.message, request.top_k)
            return {"rag_result": result, "status": result.status}
        except LLMUnavailableError as error:
            code = "generation_timeout" if error.kind == "timeout" else "generation_unavailable"
            return problem("error", code, "Answer generation is temporarily unavailable.")
        except RetrievalUnavailableError:
            return problem("error", "retrieval_unavailable", "Retrieval is temporarily unavailable.")
        except Exception:
            return problem("error", "agent_unavailable", "The assistant is temporarily unavailable.")

    def _risk(self, state: AgentState) -> dict:
        try:
            return {"assessment": assess_risk(**state["risk_inputs"]), "status": "assessed"}
        except ValidationError:
            return problem("invalid_input", "invalid_risk_inputs", "Likelihood and impact must be integers 1..5.")

    def _error(self, state: AgentState) -> dict:
        # Only preconstructed public problems enter the formatter, never exceptions.
        return {"problem": state["problem"], "status": state["status"]}

    def _format(self, state: AgentState) -> dict:
        if state.get("problem"):
            response = AgentResponse(capability=state["capability"], status=state["status"],
                                     error=state["problem"])
        elif state["capability"] == "risk":
            response = AgentResponse(capability="risk", status="assessed", assessment=state["assessment"])
        else:
            result = state["rag_result"]
            response = AgentResponse(
                capability="knowledge", status=result.status, answer=result.answer,
                citations=result.citations, model=result.model,
                retrieved_evidence_count=result.retrieved_evidence_count,
                selected_evidence_count=result.selected_evidence_count,
                abstention_reason=result.abstention_reason,
            )
        return {"response": response}

    def invoke(self, request: AgentRequest | dict) -> AgentResponse:
        raw = request.model_dump() if isinstance(request, AgentRequest) else request
        try:
            result = self._graph.invoke({"raw_request": raw}, config={"recursion_limit": MAX_GRAPH_STEPS})
            return result["response"]
        except GraphRecursionError:
            return AgentResponse(capability="none", status="error", error=AgentProblem(
                code="execution_limit", message="The assistant could not complete within its execution limit."))
        except Exception:
            return AgentResponse(capability="none", status="error", error=AgentProblem(
                code="agent_unavailable", message="The assistant is temporarily unavailable."))
