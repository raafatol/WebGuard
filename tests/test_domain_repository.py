
import pytest

from app.database import db
from app.database.domain_repository import (
    add_domain,
    get_domains,
    delete_domain,
)

from app.database.client_repository import add_client
from app.database.domain_repository import get_domains_by_client


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


def test_agregar_dominio_a_cliente(base_de_datos_temporal):
    cliente = add_client("Agencia Málaga")

    dominio = add_domain("example.com", cliente["id"])

    assert dominio["domain"] == "example.com"
    assert dominio["client_id"] == cliente["id"]


def test_obtener_dominios_de_cliente(base_de_datos_temporal):
    cliente = add_client("Agencia Málaga")

    add_domain("example.com", cliente["id"])
    add_domain("www.google.com", cliente["id"])

    dominios = get_domains_by_client(cliente["id"])

    assert len(dominios) == 2
    assert dominios[0]["domain"] == "example.com"
    assert dominios[1]["domain"] == "www.google.com"


def test_separar_dominios_por_cliente(base_de_datos_temporal):
    cliente_a = add_client("Cliente A")
    cliente_b = add_client("Cliente B")

    add_domain("example.com", cliente_a["id"])
    add_domain("www.google.com", cliente_b["id"])

    dominios_a = get_domains_by_client(cliente_a["id"])
    dominios_b = get_domains_by_client(cliente_b["id"])

    assert len(dominios_a) == 1
    assert len(dominios_b) == 1

    assert dominios_a[0]["domain"] == "example.com"
    assert dominios_b[0]["domain"] == "www.google.com"


def test_rechazar_cliente_inexistente(base_de_datos_temporal):
    with pytest.raises(ValueError, match="cliente indicado no existe"):
        add_domain("example.com", 9999)


def test_listado_incluye_nombre_cliente(base_de_datos_temporal):
    cliente = add_client("Agencia Málaga")

    add_domain("example.com", cliente["id"])

    dominios = get_domains()

    assert len(dominios) == 1
    assert dominios[0]["client_id"] == cliente["id"]
    assert dominios[0]["client_name"] == "Agencia Málaga"


def test_dominio_sin_cliente(base_de_datos_temporal):
    add_domain("example.com")

    dominios = get_domains()

    assert len(dominios) == 1
    assert dominios[0]["domain"] == "example.com"
    assert dominios[0]["client_id"] is None
    assert dominios[0]["client_name"] is None


def test_dominio_duplicado_entre_clientes(base_de_datos_temporal):
    cliente_a = add_client("Cliente A")
    cliente_b = add_client("Cliente B")

    add_domain("example.com", cliente_a["id"])

    with pytest.raises(
        ValueError,
        match="Este dominio ya está registrado"
    ):
        add_domain("example.com", cliente_b["id"])

    # El dominio original debe seguir perteneciendo al cliente A.
    dominios = get_domains()

    assert len(dominios) == 1
    assert dominios[0]["client_id"] == cliente_a["id"]
