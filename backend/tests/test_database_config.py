import pytest

from app.core.config import Settings
from app.db.connection import database_url


def test_url_safely_handles_password_characters(monkeypatch):
    monkeypatch.setenv("POSTGRES_USER", "test")
    monkeypatch.setenv("POSTGRES_PASSWORD", "p@ss:/?#word")
    monkeypatch.setenv("POSTGRES_DB", "cybersage")
    url = database_url(Settings(_env_file=None))
    assert url.password == "p@ss:/?#word"
    assert "p@ss" not in str(url)
    assert url.drivername == "postgresql+psycopg"


def test_missing_password_rejected(monkeypatch):
    monkeypatch.setenv("POSTGRES_PASSWORD", "")
    with pytest.raises(ValueError, match="Set POSTGRES"):
        database_url(Settings(_env_file=None))
