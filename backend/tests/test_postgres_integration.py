"""Opt in with CYBERSAGE_TEST_POSTGRES=1; all test tables are temporary."""

import pymupdf
import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError, StatementError

from app.db.repository import DocumentRepository
from app.db.tables import document_chunks, documents
from app.ingestion import pipeline


@pytest.fixture
def pdf(tmp_path):
    path = tmp_path / "security.pdf"
    with pymupdf.open() as document:
        document.new_page()  # Blank page must not renumber the next page.
        page = document.new_page()
        page.insert_text((72, 72), "Network segmentation limits lateral movement.")
        document.save(path)
    return path


def fake_embeddings(texts, batch_size=32):
    return [[1.0] + [0.0] * 383 for _ in texts]


def test_real_pipeline_duplicate_and_page_references(database, pdf, monkeypatch):
    engine, connection = database
    monkeypatch.setattr(pipeline, "embed_texts", fake_embeddings)
    assert pipeline.ingest_pdf(engine, pdf).status == "indexed"
    assert pipeline.ingest_pdf(engine, pdf).status == "skipped"
    assert connection.scalar(select(func.count()).select_from(documents)) == 1
    assert connection.scalar(select(func.count()).select_from(document_chunks)) == 1
    doc = connection.execute(select(documents)).mappings().one()
    chunk = connection.execute(select(document_chunks)).mappings().one()
    assert doc["status"] == "indexed" and doc["page_count"] == 2
    assert chunk["page_number"] == 2 and chunk["document_id"] == doc["id"]
    assert len(chunk["embedding"]) == 384
    assert connection.scalar(text("SELECT vector_dims(embedding) FROM document_chunks")) == 384


def test_failed_partial_write_rollback_and_retry(database, pdf, monkeypatch):
    engine, connection = database
    monkeypatch.setattr(pipeline, "embed_texts", fake_embeddings)
    original = DocumentRepository.replace_chunks
    def write_then_fail(self, *args):
        original(self, *args)
        raise RuntimeError("simulate failure after insertion")
    monkeypatch.setattr(DocumentRepository, "replace_chunks", write_then_fail)
    assert pipeline.ingest_pdf(engine, pdf).status == "failed"
    assert connection.scalar(select(documents.c.status)) == "failed"
    assert connection.scalar(select(func.count()).select_from(document_chunks)) == 0
    monkeypatch.setattr(DocumentRepository, "replace_chunks", original)
    assert pipeline.ingest_pdf(engine, pdf).status == "indexed"
    assert connection.scalar(select(func.count()).select_from(documents)) == 1
    assert connection.scalar(select(func.count()).select_from(document_chunks)) == 1


def test_repository_hash_uniqueness_and_vector_constraint(database):
    _, connection = database
    repository = DocumentRepository(connection)
    first = repository.get_or_create("a" * 64, "first.pdf")
    second = repository.get_or_create("a" * 64, "renamed.pdf")
    assert first["id"] == second["id"]
    chunk = {"chunk_index": 0, "page_number": 1, "content": "Security"}
    with pytest.raises(StatementError) as captured:
        with connection.begin_nested():
            repository.replace_chunks(first["id"], [chunk], [[1.0] * 768])
    assert "384" in str(captured.value)
    assert connection.scalar(select(func.count()).select_from(document_chunks)) == 0


def test_database_error_marks_failed_and_can_retry(database, pdf, monkeypatch):
    engine, connection = database
    monkeypatch.setattr(pipeline, "embed_texts", fake_embeddings)
    original = DocumentRepository.replace_chunks
    def invalid_page(self, document_id, chunks, embeddings):
        original(self, document_id, [{**chunk, "page_number": 0} for chunk in chunks], embeddings)
    monkeypatch.setattr(DocumentRepository, "replace_chunks", invalid_page)
    result = pipeline.ingest_pdf(engine, pdf)
    assert result.status == "failed" and result.error == "IntegrityError"
    assert connection.scalar(select(documents.c.status)) == "failed"
    assert connection.scalar(select(func.count()).select_from(document_chunks)) == 0
    monkeypatch.setattr(DocumentRepository, "replace_chunks", original)
    assert pipeline.ingest_pdf(engine, pdf).status == "indexed"


def test_missing_parent_rejected(database):
    _, connection = database
    with pytest.raises(IntegrityError):
        with connection.begin_nested():
            connection.execute(text(
                "INSERT INTO document_chunks (document_id, chunk_index, page_number, content, embedding) "
                "VALUES (gen_random_uuid(), 0, 1, 'Security', CAST(:embedding AS vector))"
            ), {"embedding": "[" + ",".join(["1"] + ["0"] * 383) + "]"})
