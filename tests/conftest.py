
import pytest

from app.database import db


@pytest.fixture
def database(tmp_path, monkeypatch):
    """
    Crea una base de datos SQLite temporal
    e independiente para cada prueba.
    """
    database_path = tmp_path / "webguard_test.db"

    monkeypatch.setattr(db, "DB_PATH", database_path)

    db.init_db()

    return database_path
