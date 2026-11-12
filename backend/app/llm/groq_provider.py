"""Official Groq SDK adapter. RAG logic does not import or depend on this class."""

from threading import Lock

from groq import APITimeoutError, Groq, NotFoundError, RateLimitError

from app.core.config import Settings
from app.llm.base import InvalidModelOutputError, LLMUnavailableError


class GroqProvider:
    def __init__(self, settings: Settings):
        self.model = settings.GROQ_MODEL.strip()
        self._key = settings.GROQ_API_KEY
        self._temperature = settings.GROQ_TEMPERATURE
        self._timeout = settings.GROQ_TIMEOUT_SECONDS
        self._max_tokens = settings.GROQ_MAX_OUTPUT_TOKENS
        self._client = None
        self._validated = False
        self._lock = Lock()

    def _ready_client(self):
        with self._lock:
            if not self._key or not self._key.get_secret_value().strip():
                raise LLMUnavailableError("configuration")
            if not self.model:
                raise LLMUnavailableError("model")
            if self._client is None:
                self._client = Groq(
                    api_key=self._key.get_secret_value(), timeout=self._timeout,
                    max_retries=0,  # Bound latency; callers may retry explicitly.
                )
            if not self._validated:
                # Namespaced IDs may return 404 on the single-model route even
                # when active. The account's model list is authoritative.
                models = self._client.models.list().data
                if not any(model.id == self.model and getattr(model, "active", True) is not False
                           for model in models):
                    raise LLMUnavailableError("model")
                self._validated = True
            return self._client

    def generate_json(self, system: str, payload: str) -> str:
        try:
            client = self._ready_client()
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": payload}],
                response_format={"type": "json_object"},
                temperature=self._temperature,
                max_completion_tokens=self._max_tokens,
            )
            choice = response.choices[0]
            if choice.finish_reason != "stop" or not choice.message.content:
                raise InvalidModelOutputError("Incomplete model response")
            return choice.message.content
        except (LLMUnavailableError, InvalidModelOutputError):
            raise
        except APITimeoutError:
            raise LLMUnavailableError("timeout") from None
        except RateLimitError:
            raise LLMUnavailableError("rate_limit") from None
        except NotFoundError:
            raise LLMUnavailableError("model") from None
        except Exception:
            raise LLMUnavailableError("provider") from None

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
