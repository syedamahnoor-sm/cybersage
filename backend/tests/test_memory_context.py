import pytest

from app.agent.schemas import AgentRequest
from app.memory.context import ContextTurn, resolve


def turn(message, capability="knowledge", status="answered"):
    return ContextTurn(message, message, capability, status)


def test_nist_recovery_uses_user_source_reference():
    result = resolve(AgentRequest(message="What about recovery?"), [
        turn("What does NIST CSF 2.0 say about incident response?")])
    assert result == ("What does NIST CSF 2.0 say about recovery?", True, False)


def test_pakistan_pronoun_is_resolved_without_assistant_facts():
    result = resolve(AgentRequest(message="What response measures does it describe?"), [
        turn("What does Pakistan's National Cyber Security Policy say about critical infrastructure?")])
    assert result == ("What response measures does Pakistan's National Cyber Security Policy describe?", True, False)


@pytest.mark.parametrize("history", [[], [turn("What does NIST and Pakistan's policy say?")],
    [turn("Calculate risk", "risk", "assessed")], [turn("What about that?", "none", "needs_clarification")]])
def test_ambiguous_reference_never_guesses(history):
    assert resolve(AgentRequest(message="What about recovery?"), history)[2] is True


def test_explicit_standalone_source_never_uses_old_conversation():
    question = "What does Pakistan's policy say about critical infrastructure?"
    assert resolve(AgentRequest(message=question), [turn("What does NIST CSF 2.0 say?")]) == (question, False, False)


def test_risk_never_inherits_prior_numerical_values():
    request = AgentRequest(message="Calculate risk", likelihood=4)
    assert resolve(request, [turn("likelihood 3 impact 5", "risk", "assessed")]) == (request.message, False, False)


def test_latest_user_source_controls_context_not_older_turns():
    history = [turn("What does NIST CSF 2.0 say?"), turn("What does Pakistan's National Cyber Security Policy say?")]
    assert "Pakistan" in resolve(AgentRequest(message="What about recovery?"), history)[0]


def test_unknown_explicit_source_is_not_rewritten_as_known_source():
    message = "What is the cybersecurity policy of Mars in 2050?"
    assert resolve(AgentRequest(message=message), [turn("What does NIST say?")]) == (message, False, False)


def test_generic_source_reference_requires_explicit_name():
    assert resolve(AgentRequest(message="What about that policy?"), [turn("What does NIST say?")])[2]


def test_unrelated_pakistan_policy_is_not_renamed_as_cybersecurity():
    assert resolve(AgentRequest(message="What response measures does it describe?"),
                   [turn("What does Pakistan's fiscal policy say?")])[2]
