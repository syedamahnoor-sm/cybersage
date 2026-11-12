import json
from unittest.mock import Mock

import pytest

from app.retrieval import __main__ as cli
from app.retrieval.schemas import SearchResponse


@pytest.mark.parametrize("args", [["--query", " "], ["--query", "x", "--top-k", "21"],
                                   ["--query", "x", "--min-similarity", "nan"]])
def test_cli_validates_before_creating_engine(args, monkeypatch, capsys):
    factory = Mock()
    monkeypatch.setattr(cli, "make_engine", factory)
    monkeypatch.setattr("sys.argv", ["retrieval", *args])
    assert cli.main() == 2
    assert "Invalid search" in capsys.readouterr().out
    factory.assert_not_called()


def test_cli_json_and_engine_cleanup(monkeypatch, capsys):
    engine = Mock()
    monkeypatch.setattr(cli, "make_engine", Mock(return_value=engine))
    retriever = Mock()
    retriever.search.return_value = SearchResponse(query="Security \u2014 evidence", results=[],
                                                 result_count=0, min_similarity=0.2)
    monkeypatch.setattr(cli, "RetrievalService", Mock(return_value=retriever))
    monkeypatch.setattr("sys.argv", ["retrieval", "--query", "Security \u2014 evidence"])
    assert cli.main() == 0
    output = capsys.readouterr().out
    assert output.isascii()
    assert json.loads(output)["query"] == "Security \u2014 evidence"
    engine.dispose.assert_called_once()


def test_cli_failure_is_safe_and_disposes_engine(monkeypatch, capsys):
    engine = Mock()
    monkeypatch.setattr(cli, "make_engine", Mock(return_value=engine))
    monkeypatch.setattr(cli, "RetrievalService", Mock(side_effect=RuntimeError("secret-password")))
    monkeypatch.setattr("sys.argv", ["retrieval", "--query", "Security"])
    assert cli.main() == 1
    assert "secret-password" not in capsys.readouterr().out
    engine.dispose.assert_called_once()
