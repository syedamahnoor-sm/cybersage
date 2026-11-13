"""Mappings only; schema is installed by migration 002."""

from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID

metadata = MetaData()
conversations = Table("conversations", metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("revision", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True)), Column("updated_at", DateTime(timezone=True)))
turns = Table("conversation_turns", metadata,
    Column("request_id", UUID(as_uuid=True), primary_key=True),
    Column("conversation_id", UUID(as_uuid=True), nullable=False),
    Column("turn_number", Integer, nullable=False), Column("request_hash", String(64)),
    Column("created_at", DateTime(timezone=True)))
messages = Table("conversation_messages", metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("conversation_id", UUID(as_uuid=True), nullable=False),
    Column("request_id", UUID(as_uuid=True), nullable=False),
    Column("role", String(10)), Column("content", Text), Column("metadata", JSONB),
    Column("created_at", DateTime(timezone=True)))
