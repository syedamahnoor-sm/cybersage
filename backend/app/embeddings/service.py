"""Generate normalized embeddings with a lazily loaded, shared model."""

from threading import Lock
from math import isfinite
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSIONS = 384

_model: "SentenceTransformer | None" = None
_model_lock = Lock()


def _get_model() -> "SentenceTransformer":
    global _model

    with _model_lock:
        if _model is None:
            from sentence_transformers import SentenceTransformer

            _model = SentenceTransformer(MODEL_NAME)
        return _model


def embed_text(text: str) -> list[float]:
    """Embed nonblank text as 384 floats; first use may download the model.

    The model stays in memory for subsequent calls in this process. Model
    downloads use the standard Hugging Face cache (configurable with HF_HOME).
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if not text.strip():
        raise ValueError("text must not be empty or whitespace-only")

    embedding = _get_model().encode(
        text,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    ).tolist()
    if len(embedding) != EMBEDDING_DIMENSIONS:
        raise ValueError(
            f"Expected {EMBEDDING_DIMENSIONS} embedding dimensions, "
            f"got {len(embedding)}"
        )
    return [float(value) for value in embedding]


def embed_texts(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    """Embed a list in order using the shared model; an empty list returns []."""
    if not isinstance(texts, list):
        raise TypeError("texts must be a list of strings")
    if isinstance(batch_size, bool) or not isinstance(batch_size, int):
        raise TypeError("batch_size must be an integer")
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    for text in texts:
        if not isinstance(text, str):
            raise TypeError("every text must be a string")
        if not text.strip():
            raise ValueError("texts must not contain empty or whitespace-only text")
    if not texts:
        return []

    rows = _get_model().encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    ).tolist()
    if len(rows) != len(texts):
        raise ValueError("Embedding count does not match input count")
    result = []
    for row in rows:
        if len(row) != EMBEDDING_DIMENSIONS:
            raise ValueError(f"Expected {EMBEDDING_DIMENSIONS} embedding dimensions")
        vector = [float(value) for value in row]
        if not all(isfinite(value) for value in vector):
            raise ValueError("Embedding values must be finite")
        result.append(vector)
    return result
