from typing import Literal, Protocol


class LLMUnavailableError(RuntimeError):
    def __init__(self, kind: Literal["configuration", "timeout", "rate_limit", "model", "provider"]):
        super().__init__("Answer generation is temporarily unavailable.")
        self.kind = kind


class InvalidModelOutputError(ValueError):
    """Incomplete or malformed output must cause abstention, not partial answers."""


class LLMProvider(Protocol):
    model: str

    def generate_json(self, system: str, payload: str) -> str:
        """Return a complete JSON object or raise a safe provider error."""
        ...
