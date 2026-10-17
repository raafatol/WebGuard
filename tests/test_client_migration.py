
import sqlite3

from app.database import db


def test_crear_tabla_clientes(tmp_path, monkeypatch):
    database_path = tmp_path / "webguard_test.db"
    monkeypatch.setattr(db, "DB_PATH", database_path)

    db.init_db()

    with db.get_connection() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    assert "clients" in tables


def test_dominios_tienen_cliente(tmp_path, monkeypatch):
    database_path = tmp_path / "webguard_test.db"
    monkeypatch.setattr(db, "DB_PATH", database_path)

    db.init_db()

    with db.get_connection() as connection:
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(domains)")
        }

    assert "client_id" in columns


def test_migracion_conserva_dominios(tmp_path, monkeypatch):
    database_path = tmp_path / "webguard_test.db"
    monkeypatch.setattr(db, "DB_PATH", database_path)

    # Simulamos una base de datos antigua.
    with sqlite3.connect(database_path) as connection:
        connection.execute("""
            CREATE TABLE domains (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        connection.execute(
            "INSERT INTO domains (domain) VALUES (?)",
            ("example.com",)
        )

    # Ejecutamos la futura migración.
    db.init_db()

    with db.get_connection() as connection:
        row = connection.execute(
            "SELECT domain, client_id FROM domains WHERE domain = ?",
            ("example.com",)
        ).fetchone()

    assert row == ("example.com", None)


def test_migracion_es_repetible(tmp_path, monkeypatch):
    database_path = tmp_path / "webguard_test.db"
    monkeypatch.setattr(db, "DB_PATH", database_path)

    db.init_db()
    db.init_db()

    with db.get_connection() as connection:
        columns = [
            row[1]
            for row in connection.execute("PRAGMA table_info(domains)")
        ]

    assert columns.count("client_id") == 1
