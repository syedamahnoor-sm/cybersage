from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from groq import APIConnectionError, APIStatusError, APITimeoutError, NotFoundError, RateLimitError
from pydantic import SecretStr

from app.core.config import Settings
from app.llm.base import InvalidModelOutputError, LLMUnavailableError
from app.llm import groq_provider


@pytest.fixture
def provider(monkeypatch):
    settings = Settings(_env_file=None, GROQ_API_KEY=SecretStr("test-only-placeholder"))
    client = Mock()
    client.models.list.return_value = SimpleNamespace(data=[
        SimpleNamespace(id=settings.GROQ_MODEL, active=True)
    ])
    client.chat.completions.create.return_value = SimpleNamespace(choices=[
        SimpleNamespace(finish_reason="stop", message=SimpleNamespace(content='{"ok":true}'))
    ])
    factory = Mock(return_value=client)
    monkeypatch.setattr(groq_provider, "Groq", factory)
    return groq_provider.GroqProvider(settings), client, factory


def test_groq_parameters_lazy_validation_and_client_reuse(provider):
    adapter, client, factory = provider
    factory.assert_not_called()
    assert adapter.generate_json("JSON rules", "{}") == '{"ok":true}'
    adapter.generate_json("JSON rules", "{}")
    factory.assert_called_once()
    assert factory.call_args.kwargs["max_retries"] == 0
    assert factory.call_args.kwargs["timeout"] == 30
    client.models.list.assert_called_once_with()
    client.models.retrieve.assert_not_called()
    parameters = client.chat.completions.create.call_args.kwargs
    assert parameters["temperature"] == 0
    assert parameters["max_completion_tokens"] == 2048
    assert parameters["response_format"] == {"type": "json_object"}
    assert parameters["messages"][0]["role"] == "system"
    assert "tools" not in parameters
    adapter.close()
    client.close.assert_called_once()


def test_missing_credentials_fail_without_sdk_call(monkeypatch):
    factory = Mock()
    monkeypatch.setattr(groq_provider, "Groq", factory)
    settings = Settings(_env_file=None, GROQ_API_KEY=None)
    with pytest.raises(LLMUnavailableError) as captured:
        groq_provider.GroqProvider(settings).generate_json("rules", "{}")
    assert captured.value.kind == "configuration"
    factory.assert_not_called()


@pytest.mark.parametrize("active,model_id", [(False, "openai/gpt-oss-120b"), (True, "wrong-model")])
def test_unavailable_model_is_rejected(active, model_id, provider):
    adapter, client, _ = provider
    client.models.list.return_value = SimpleNamespace(data=[SimpleNamespace(id=model_id, active=active)])
    with pytest.raises(LLMUnavailableError) as captured:
        adapter.generate_json("rules", "{}")
    assert captured.value.kind == "model"
    client.chat.completions.create.assert_not_called()


def test_model_missing_from_account_list_is_rejected(provider):
    adapter, client, _ = provider
    client.models.list.return_value = SimpleNamespace(data=[])
    with pytest.raises(LLMUnavailableError) as captured:
        adapter.generate_json("rules", "{}")
    assert captured.value.kind == "model"
    client.chat.completions.create.assert_not_called()


@pytest.mark.parametrize("kind", ["timeout", "rate_limit", "model", "provider", "connection"])
@pytest.mark.parametrize("phase", ["validation", "completion"])
def test_errors_are_sanitized(kind, phase, provider):
    adapter, client, _ = provider
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    response = httpx.Response(429 if kind == "rate_limit" else 404, request=request)
    errors = {
        "timeout": APITimeoutError(request=request),
        "rate_limit": RateLimitError("sensitive provider details", response=response, body={}),
        "model": NotFoundError("sensitive provider details", response=response, body={}),
        "provider": APIStatusError("sensitive provider details", response=response, body={}),
        "connection": APIConnectionError(request=request),
    }
    target = client.models.list if phase == "validation" else client.chat.completions.create
    target.side_effect = errors[kind]
    with pytest.raises(LLMUnavailableError) as captured:
        adapter.generate_json("rules", "{}")
    assert captured.value.kind == ("provider" if kind == "connection" else kind)
    assert "sensitive" not in str(captured.value)


@pytest.mark.parametrize("reason,content", [("length", '{"partial":'), ("stop", None),
                                             ("tool_calls", "{}")])
def test_partial_responses_are_rejected(reason, content, provider):
    adapter, client, _ = provider
    client.chat.completions.create.return_value.choices[0] = SimpleNamespace(
        finish_reason=reason, message=SimpleNamespace(content=content),
    )
    with pytest.raises(InvalidModelOutputError):
        adapter.generate_json("rules", "{}")
