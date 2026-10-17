
import pytest

from app.database import db
from app.database.client_repository import (
    add_client,
    get_clients,
    get_client_by_id,
    update_client,
    delete_client,
)

def test_agregar_cliente(database):
    cliente = add_client(
        "Agencia Málaga",
        "contacto@agencia.es"
    )

    assert cliente["id"] == 1
    assert cliente["name"] == "Agencia Málaga"
    assert cliente["email"] == "contacto@agencia.es"


def test_cliente_guardado_en_sqlite(database):
    add_client("Empresa de prueba", "empresa@example.com")

    with db.get_connection() as connection:
        resultado = connection.execute(
            "SELECT name, email FROM clients WHERE id = 1"
        ).fetchone()

    assert resultado == (
        "Empresa de prueba",
        "empresa@example.com"
    )


def test_cliente_sin_email(database):
    cliente = add_client("Cliente sin correo")

    assert cliente["name"] == "Cliente sin correo"
    assert cliente["email"] is None


def test_rechazar_nombre_vacio(database):
    with pytest.raises(ValueError):
        add_client("   ")


def test_normalizar_datos_cliente(database):
    cliente = add_client(
        "  Agencia Málaga  ",
        "  contacto@agencia.es  "
    )

    assert cliente["name"] == "Agencia Málaga"
    assert cliente["email"] == "contacto@agencia.es"


def test_obtener_clientes(database):
    add_client("Cliente A", "a@example.com")
    add_client("Cliente B", "b@example.com")

    clientes = get_clients()

    assert len(clientes) == 2
    assert clientes[0]["name"] == "Cliente A"
    assert clientes[1]["name"] == "Cliente B"


def test_obtener_clientes_vacio(database):
    clientes = get_clients()

    assert clientes == []


def test_clientes_contienen_fecha(database):
    add_client("Cliente de prueba")

    clientes = get_clients()

    assert "created_at" in clientes[0]
    assert clientes[0]["created_at"] is not None


def test_obtener_cliente_por_id(database):
    cliente = add_client("Agencia Málaga", "contacto@agencia.es")

    resultado = get_client_by_id(cliente["id"])

    assert resultado is not None
    assert resultado["id"] == cliente["id"]
    assert resultado["name"] == "Agencia Málaga"
    assert resultado["email"] == "contacto@agencia.es"
    assert "created_at" in resultado


def test_obtener_cliente_inexistente(database):
    resultado = get_client_by_id(9999)

    assert resultado is None


def test_obtener_cliente_correcto(database):
    add_client("Cliente A")
    cliente_b = add_client("Cliente B")

    resultado = get_client_by_id(cliente_b["id"])

    assert resultado["name"] == "Cliente B"


def test_actualizar_cliente(database):
    cliente = add_client("Nombre antiguo", "antiguo@example.com")

    actualizado = update_client(
        cliente["id"],
        "Nombre nuevo",
        "nuevo@example.com"
    )

    assert actualizado["id"] == cliente["id"]
    assert actualizado["name"] == "Nombre nuevo"
    assert actualizado["email"] == "nuevo@example.com"


def test_actualizacion_persistente(database):
    cliente = add_client("Cliente original")

    update_client(cliente["id"], "Cliente actualizado")

    guardado = get_client_by_id(cliente["id"])

    assert guardado["name"] == "Cliente actualizado"


def test_actualizar_cliente_inexistente(database):
    resultado = update_client(9999, "Cliente inexistente")

    assert resultado is None


def test_rechazar_actualizacion_nombre_vacio(database):
    cliente = add_client("Cliente válido")

    with pytest.raises(ValueError):
        update_client(cliente["id"], "   ")

    guardado = get_client_by_id(cliente["id"])

    assert guardado["name"] == "Cliente válido"


def test_eliminar_cliente(database):
    cliente = add_client("Cliente temporal")

    eliminado = delete_client(cliente["id"])

    assert eliminado is True
    assert get_client_by_id(cliente["id"]) is None


def test_eliminar_cliente_inexistente(database):
    eliminado = delete_client(9999)

    assert eliminado is False


def test_impedir_eliminar_cliente_con_dominios(database):
    cliente = add_client("Cliente con dominio")

    with db.get_connection() as connection:
        connection.execute(
            """
            INSERT INTO domains (domain, client_id)
            VALUES (?, ?)
            """,
            ("example.com", cliente["id"])
        )

    with pytest.raises(ValueError):
        delete_client(cliente["id"])

    # El cliente debe seguir existiendo.
    assert get_client_by_id(cliente["id"]) is not None

    # Su dominio también debe conservarse.
    with db.get_connection() as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM domains WHERE client_id = ?",
            (cliente["id"],)
        ).fetchone()[0]

    assert count == 1
