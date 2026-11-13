from types import SimpleNamespace
from uuid import uuid4

import pymupdf
from sqlalchemy import select

from app.db.repository import DocumentRepository
from app.db.tables import document_chunks
from evaluation.provenance import verify_citation


def test_real_citation_provenance_is_not_source_relevance(database, tmp_path):
    engine, connection = database
    path = tmp_path / "audit.pdf"
    text = "Security controls reduce organizational exposure."
    with pymupdf.open() as pdf:
        pdf.new_page().insert_text((72,72), text)
        pdf.save(path)
    repo = DocumentRepository(connection)
    doc = repo.get_or_create("d"*64, "audit.pdf")
    repo.replace_chunks(doc["id"], [{"chunk_index":0,"page_number":1,"content":text}], [[1.0]+[0.0]*383])
    chunk_id = connection.scalar(select(document_chunks.c.id))
    citation = {"chunk_id":str(chunk_id), "document_id":str(doc["id"]), "filename":"audit.pdf",
                "document_title":None,"page_number":1,"chunk_index":0,"quote":text,"evidence_id":"E_"+chunk_id.hex}
    question = SimpleNamespace(expected_source="audit.pdf",expected_pages=[1])
    assert verify_citation(engine,citation,question,tmp_path)["provenance_valid"]
    altered = {**citation, "quote":"Security controls never reduce organizational exposure."}
    assert not verify_citation(engine,altered,question,tmp_path)["provenance_valid"]
    wrong_page = {**citation,"page_number":2}
    assert not verify_citation(engine,wrong_page,question,tmp_path)["metadata_valid"]
    wrong_id = {**citation,"evidence_id":"E_"+uuid4().hex}
    assert not verify_citation(engine,wrong_id,question,tmp_path)["metadata_valid"]
    other_source = SimpleNamespace(expected_source="other.pdf", expected_pages=[2])
    check = verify_citation(engine,citation,other_source,tmp_path)
    assert check["provenance_valid"] and not check["source_relevant"] and not check["expected_page"]
