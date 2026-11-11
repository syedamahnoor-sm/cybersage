"""Offline unit tests: never load or download the real model."""

import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.embeddings import embed_text, embed_texts
from app.embeddings import service


@pytest.fixture
def fake_model(monkeypatch):
    model = Mock()
    model.encode.return_value.tolist.return_value = [0.5] * 384
    constructor = Mock(return_value=model)
    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        SimpleNamespace(SentenceTransformer=constructor),
    )
    monkeypatch.setattr(service, "_model", None)
    return constructor, model


@pytest.mark.parametrize("text", ["", " ", "\t\n\r"])
def test_blank_input_rejected_before_loading(text, fake_model):
    constructor, _ = fake_model
    with pytest.raises(ValueError, match="empty or whitespace-only"):
        embed_text(text)
    constructor.assert_not_called()


@pytest.mark.parametrize("text", [None, 42, ["security"]])
def test_non_string_input_rejected(text, fake_model):
    constructor, _ = fake_model
    with pytest.raises(TypeError, match="must be a string"):
        embed_text(text)
    constructor.assert_not_called()


def test_embedding_dimensions_and_normalization_requested(fake_model):
    _, model = fake_model
    result = embed_text("Network segmentation limits lateral movement.")
    assert isinstance(result, list)
    assert len(result) == 384
    assert all(isinstance(value, float) for value in result)
    model.encode.assert_called_once_with(
        "Network segmentation limits lateral movement.",
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )


def test_model_loaded_lazily_and_reused(fake_model):
    constructor, _ = fake_model
    constructor.assert_not_called()
    embed_text("Detect malicious network traffic.")
    embed_text("Investigate suspicious login attempts.")
    constructor.assert_called_once_with(service.MODEL_NAME)


def test_unexpected_dimensions_rejected(fake_model):
    _, model = fake_model
    model.encode.return_value.tolist.return_value = [0.5] * 768
    with pytest.raises(ValueError, match="Expected 384 embedding dimensions"):
        embed_text("Security controls reduce risk.")


def test_single_and_batch_calls_share_one_cached_model(fake_model):
    constructor, model = fake_model
    embed_text("Detect threats.")
    model.encode.return_value.tolist.return_value = [[1.0] * 384]
    embed_texts(["Respond to incidents."], batch_size=1)
    embed_texts(["Recover systems."], batch_size=1)
    constructor.assert_called_once_with(service.MODEL_NAME)
