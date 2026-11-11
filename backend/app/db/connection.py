"""Create SQLAlchemy engines without exposing credentials or bound values."""

from sqlalchemy import URL, create_engine, text
from sqlalchemy.engine import Engine

from app.core.config import Settings, get_settings


def database_url(settings: Settings) -> URL:
    if not (settings.POSTGRES_USER and settings.POSTGRES_PASSWORD
            and settings.POSTGRES_PASSWORD.get_secret_value() and settings.POSTGRES_DB):
        raise ValueError("Set POSTGRES_USER, POSTGRES_PASSWORD, and POSTGRES_DB")
    return URL.create(
        "postgresql+psycopg",
        username=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD.get_secret_value(),
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        database=settings.POSTGRES_DB,
    )


def make_engine(settings: Settings | None = None) -> Engine:
    return create_engine(
        database_url(settings or get_settings()),
        pool_pre_ping=True,
        hide_parameters=True,
        connect_args={"connect_timeout": 5},
    )


def check_database(engine: Engine) -> dict:
    """Read-only connectivity and compatibility check; never creates tables."""
    with engine.connect() as connection:
        version = connection.scalar(text("SHOW server_version"))
        vector_version = connection.scalar(text(
            "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
        ))
        embedding_type = connection.scalar(text(
            "SELECT format_type(a.atttypid, a.atttypmod) "
            "FROM pg_attribute a WHERE a.attrelid = to_regclass('document_chunks') "
            "AND a.attname = 'embedding' AND NOT a.attisdropped"
        ))
        if not vector_version or embedding_type != "vector(384)":
            raise RuntimeError("Existing database must have pgvector and VECTOR(384)")
        connection.execute(text("SELECT id, file_hash, status FROM documents LIMIT 0"))
    return {"postgresql": version, "pgvector": vector_version,
            "embedding_type": embedding_type}
