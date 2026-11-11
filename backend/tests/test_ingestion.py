from contextlib import contextmanager
from hashlib import sha256
from unittest.mock import MagicMock, Mock

import pytest

from app.ingestion import pipeline


class FakeEngine:
    def __init__(self):
        self.connection = MagicMock()
        self.events = []

    @contextmanager
    def begin(self):
        self.events.append("begin")
        yield self.connection
        self.events.append("commit")


@pytest.fixture
def dependencies(monkeypatch, tmp_path):
    path = tmp_path / "security.pdf"
    path.write_bytes(b"example pdf bytes")
    engine = FakeEngine()
    repo = Mock()
    repo.get_or_create.return_value = {"id": "document-id", "status": "pending"}
    monkeypatch.setattr(pipeline, "DocumentRepository", Mock(return_value=repo))
    loader = Mock(return_value=[{"page_number": 2, "content": "Cybersecurity controls."}])
    monkeypatch.setattr(pipeline, "load_pdf", loader)
    pdf = Mock()
    pdf.__enter__ = Mock(return_value=Mock(page_count=3))
    pdf.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(pipeline.pymupdf, "open", Mock(return_value=pdf))
    embedder = Mock(return_value=[[0.5] * 384])
    monkeypatch.setattr(pipeline, "embed_texts", embedder)
    return path, engine, repo, loader, embedder


def test_hash_and_case_insensitive_discovery(tmp_path):
    path = tmp_path / "test.PDF"
    path.write_bytes(b"test")
    (tmp_path / "ignore.txt").touch()
    assert pipeline.hash_pdf(path) == sha256(b"test").hexdigest()
    assert pipeline.discover_pdfs(tmp_path) == [path]


def test_pipeline_preserves_page_and_commits_indexed(dependencies):
    path, engine, repo, _, embedder = dependencies
    result = pipeline.ingest_pdf(engine, path, 16)
    assert result.status == "indexed" and result.chunks_inserted == 1
    embedder.assert_called_once_with(["Cybersecurity controls."], 16)
    assert repo.replace_chunks.call_args.args[1][0]["page_number"] == 2
    repo.set_status.assert_any_call("document-id", "processing")
    repo.set_status.assert_any_call("document-id", "indexed", 3)
    assert engine.events == ["begin", "commit"]


def test_indexed_duplicate_skips_extraction_and_embeddings(dependencies):
    path, engine, repo, loader, embedder = dependencies
    repo.get_or_create.return_value["status"] = "indexed"
    assert pipeline.ingest_pdf(engine, path).status == "skipped"
    loader.assert_not_called()
    embedder.assert_not_called()
    repo.replace_chunks.assert_not_called()


@pytest.mark.parametrize("failure_stage", ["load", "embed", "store"])
def test_failure_never_marks_indexed(dependencies, failure_stage):
    path, engine, repo, loader, embedder = dependencies
    target = {"load": loader, "embed": embedder, "store": repo.replace_chunks}[failure_stage]
    target.side_effect = RuntimeError("sensitive driver details")
    result = pipeline.ingest_pdf(engine, path)
    assert result.status == "failed" and result.error == "RuntimeError"
    repo.set_status.assert_any_call("document-id", "failed")
    assert all(call.args[1] != "indexed" for call in repo.set_status.call_args_list)


def test_textless_pdf_is_failed(dependencies):
    path, engine, repo, loader, embedder = dependencies
    loader.return_value = []
    assert pipeline.ingest_pdf(engine, path).status == "failed"
    embedder.assert_not_called()


def test_changed_file_is_failed(dependencies):
    path, engine, repo, _, embedder = dependencies
    def change_file(*args):
        path.write_bytes(b"changed")
        return [[0.5] * 384]
    embedder.side_effect = change_file
    assert pipeline.ingest_pdf(engine, path).status == "failed"
    repo.replace_chunks.assert_not_called()


def test_directory_continues_after_failure(monkeypatch, tmp_path):
    for name in ["a.pdf", "b.pdf"]:
        (tmp_path / name).touch()
    monkeypatch.setattr(pipeline, "ingest_pdf", Mock(side_effect=[
        OSError("unreadable"), pipeline.IngestionResult("b.pdf", "indexed", 2)
    ]))
    summary = pipeline.ingest_directory(Mock(), tmp_path)
    assert summary.as_dict() == {"documents_processed": 1, "documents_skipped": 0,
                                 "chunks_inserted": 2, "failures": 1}
