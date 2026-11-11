from unittest.mock import Mock

import pytest

from app.embeddings import embed_texts
from app.embeddings import service


@pytest.fixture
def model(monkeypatch):
    fake = Mock()
    monkeypatch.setattr(service, "_get_model", Mock(return_value=fake))
    return fake


def test_batch_preserves_order_and_requests_normalization(model):
    model.encode.return_value.tolist.return_value = [[1.0] * 384, [2.0] * 384]
    texts = ["Detect threats.", "Respond to incidents."]
    result = embed_texts(texts, batch_size=1)
    assert result == [[1.0] * 384, [2.0] * 384]
    model.encode.assert_called_once_with(
        texts, batch_size=1, normalize_embeddings=True,
        convert_to_numpy=True, show_progress_bar=False,
    )


def test_empty_list_does_not_load_model(model):
    assert embed_texts([]) == []
    service._get_model.assert_not_called()


@pytest.mark.parametrize("texts,error", [
    ("security", TypeError), (None, TypeError), (("security",), TypeError),
    (["valid", None], TypeError), (["valid", " \n"], ValueError), ([""], ValueError),
])
def test_invalid_texts_rejected_before_loading(texts, error, model):
    with pytest.raises(error):
        embed_texts(texts)
    service._get_model.assert_not_called()


@pytest.mark.parametrize("size,error", [(0, ValueError), (-1, ValueError),
                                         (True, TypeError), (1.5, TypeError)])
def test_invalid_batch_size(size, error, model):
    with pytest.raises(error):
        embed_texts(["Security"], size)
    service._get_model.assert_not_called()


@pytest.mark.parametrize("rows", [[], [[1.0] * 768], [[float("nan")] * 384]])
def test_invalid_model_output(rows, model):
    model.encode.return_value.tolist.return_value = rows
    with pytest.raises(ValueError):
        embed_texts(["Security"])
