
import pytest

from app.database import db


@pytest.fixture(autouse=True)
def protect_real_database(tmp_path, monkeypatch):
    """
    Aísla cada test de la base de datos real.

    No inicializa las tablas automáticamente porque
    algunos tests necesitan simular bases antiguas.
    """
    database_path = tmp_path / "webguard_test.db"

    monkeypatch.setattr(db, "DB_PATH", database_path)


@pytest.fixture
def database():
    """
    Inicializa una base de datos temporal para
    los tests que solicitan esta fixture.
    """
    db.init_db()

    return db.DB_PATH
