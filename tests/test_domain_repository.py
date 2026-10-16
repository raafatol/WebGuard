
import pytest

from app.database import db
from app.database.domain_repository import (
    add_domain,
    get_domains,
    delete_domain,
)


@pytest.fixture
def base_de_datos_temporal(tmp_path, monkeypatch):
    # Cada prueba utilizará su propia base de datos
    ruta_temporal = tmp_path / "webguard_test.db"

    # Cambiamos temporalmente la ruta de SQLite
    monkeypatch.setattr(db, "DB_PATH", ruta_temporal)

    # Creamos las tablas
    db.init_db()

    return ruta_temporal


def test_agregar_dominio(base_de_datos_temporal):
    resultado = add_domain("example.com")

    assert resultado["domain"] == "example.com"
    assert isinstance(resultado["id"], int)


def test_obtener_dominios(base_de_datos_temporal):
    add_domain("example.com")
    add_domain("www.google.com")

    dominios = get_domains()

    assert len(dominios) == 2
    assert dominios[0]["domain"] == "example.com"
    assert dominios[1]["domain"] == "www.google.com"


def test_rechazar_dominio_duplicado(base_de_datos_temporal):
    add_domain("example.com")

    with pytest.raises(ValueError, match="ya está registrado"):
        add_domain("example.com")


def test_rechazar_dominio_no_autorizado(base_de_datos_temporal):
    with pytest.raises(ValueError, match="Dominio no autorizado"):
        add_domain("openai.com")

    assert get_domains() == []


def test_eliminar_dominio(base_de_datos_temporal):
    resultado = add_domain("example.com")

    eliminado = delete_domain(resultado["id"])

    assert eliminado is True
    assert get_domains() == []


def test_eliminar_dominio_inexistente(base_de_datos_temporal):
    eliminado = delete_domain(9999)

    assert eliminado is False


def test_normalizar_dominio_antes_de_guardar(base_de_datos_temporal):
    resultado = add_domain("  EXAMPLE.COM  ")

    assert resultado["domain"] == "example.com"

    dominios = get_domains()
    assert dominios[0]["domain"] == "example.com"
