"""Shared opt-in PostgreSQL fixtures; test tables never touch indexed PDFs."""

from contextlib import contextmanager
import os
from pathlib import Path

import pytest

from app.db.connection import check_database, make_engine


class BoundEngine:
    def __init__(self, connection):
        self.connection = connection

    @contextmanager
    def begin(self):
        with self.connection.begin_nested():
            yield self.connection

    @contextmanager
    def connect(self):
        yield self.connection


@pytest.fixture
def database():
    if os.getenv("CYBERSAGE_TEST_POSTGRES") != "1":
        pytest.skip("Set CYBERSAGE_TEST_POSTGRES=1 for real PostgreSQL tests")
    engine = make_engine()
    try:
        check_database(engine)
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                schema = (Path(__file__).resolve().parents[1] / "migrations" /
                          "001_initial_schema.sql").read_text()
                schema = schema.replace("CREATE EXTENSION IF NOT EXISTS vector;", "")
                schema = schema.replace("CREATE TABLE IF NOT EXISTS", "CREATE TEMP TABLE")
                connection.exec_driver_sql(schema)
                yield BoundEngine(connection), connection
            finally:
                transaction.rollback()
    finally:
        engine.dispose()


@pytest.fixture
def memory_database(database):
    engine, connection = database
    schema = (Path(__file__).resolve().parents[1] / "migrations" /
              "002_conversational_memory.sql").read_text()
    schema = schema.replace("BEGIN;", "").replace("COMMIT;", "")
    schema = schema.replace("CREATE TABLE ", "CREATE TEMP TABLE ")
    connection.exec_driver_sql(schema)
    return engine, connection
