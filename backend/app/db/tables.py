"""SQLAlchemy Core mappings for existing tables. No schema is created here."""

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import Column, DateTime, ForeignKey, Integer, MetaData, String, Table, Text, text
from sqlalchemy.dialects.postgresql import UUID

metadata = MetaData()

documents = Table(
    "documents", metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("filename", String(255), nullable=False),
    Column("title", String(500)),
    Column("source", String(255)),
    Column("jurisdiction", String(100)),
    Column("file_hash", String(64), nullable=False, unique=True),
    Column("page_count", Integer),
    Column("status", String(30), nullable=False),
    Column("created_at", DateTime(timezone=True)),
    Column("updated_at", DateTime(timezone=True)),
)

document_chunks = Table(
    "document_chunks", metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("document_id", UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False),
    Column("chunk_index", Integer, nullable=False),
    Column("page_number", Integer, nullable=False),
    Column("content", Text, nullable=False),
    Column("embedding", VECTOR(384), nullable=False),
    Column("created_at", DateTime(timezone=True)),
)
