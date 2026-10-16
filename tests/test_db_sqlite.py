
import sqlite3

from app.database import db


def test_creacion_base_de_datos(tmp_path, monkeypatch):
    # Creamos una ruta temporal para SQLite
    ruta_temporal = tmp_path / "webguard_test.db"

    # Sustituimos la ruta real solo durante esta prueba
    monkeypatch.setattr(db, "DB_PATH", ruta_temporal)

    # Inicializamos la base de datos de prueba
    db.init_db()

    # Comprobamos que el archivo se ha creado
    assert ruta_temporal.exists()


def test_creacion_tablas(tmp_path, monkeypatch):
    ruta_temporal = tmp_path / "webguard_test.db"
    monkeypatch.setattr(db, "DB_PATH", ruta_temporal)

    db.init_db()

    with db.get_connection() as connection:
        cursor = connection.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
        """)

        tablas = {fila[0] for fila in cursor.fetchall()}

    assert "domains" in tablas
    assert "analyses" in tablas
    assert "alerts" in tablas
    assert "email_notifications" in tablas


def test_insertar_y_consultar_dominio(tmp_path, monkeypatch):
    ruta_temporal = tmp_path / "webguard_test.db"
    monkeypatch.setattr(db, "DB_PATH", ruta_temporal)

    db.init_db()

    with db.get_connection() as connection:
        connection.execute(
            "INSERT INTO domains (domain) VALUES (?)",
            ("example.com",)
        )
        connection.commit()

        cursor = connection.execute(
            "SELECT domain FROM domains WHERE domain = ?",
            ("example.com",)
        )

        resultado = cursor.fetchone()

    assert resultado is not None
    assert resultado[0] == "example.com"


def test_dominio_duplicado(tmp_path, monkeypatch):
    ruta_temporal = tmp_path / "webguard_test.db"
    monkeypatch.setattr(db, "DB_PATH", ruta_temporal)

    db.init_db()

    with db.get_connection() as connection:
        connection.execute(
            "INSERT INTO domains (domain) VALUES (?)",
            ("example.com",)
        )
        connection.commit()

        try:
            connection.execute(
                "INSERT INTO domains (domain) VALUES (?)",
                ("example.com",)
            )
        except sqlite3.IntegrityError:
            duplicado_rechazado = True
        else:
            duplicado_rechazado = False

    assert duplicado_rechazado is True


def test_inicializacion_repetida(tmp_path, monkeypatch):
    ruta_temporal = tmp_path / "webguard_test.db"
    monkeypatch.setattr(db, "DB_PATH", ruta_temporal)

    # Inicializar dos veces no debería producir errores
    db.init_db()
    db.init_db()

    with db.get_connection() as connection:
        cursor = connection.execute(
            "SELECT COUNT(*) FROM sqlite_master "
            "WHERE type = 'table' AND name = 'domains'"
        )

        cantidad = cursor.fetchone()[0]

    assert cantidad == 1
