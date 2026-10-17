
import pytest

from fastapi.testclient import TestClient

from app.main import app
from app.database.client_repository import add_client
from app.database.domain_repository import add_domain

@pytest.fixture
def api_client(database):
    """
    Cliente HTTP de pruebas conectado
    a la base de datos temporal.
    """
    return TestClient(app)


def test_listar_clientes_vacio(api_client):
    response = api_client.get("/clients")

    assert response.status_code == 200
    assert response.json() == []


def test_crear_cliente_desde_api(api_client):
    response = api_client.post(
        "/clients",
        json={
            "name": "Agencia Málaga",
            "email": "contacto@agencia.es"
        }
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "Agencia Málaga"
    assert data["email"] == "contacto@agencia.es"
    assert isinstance(data["id"], int)


def test_consultar_cliente_existente(api_client):
    cliente = add_client("Empresa de prueba")

    response = api_client.get(
        f"/clients/{cliente['id']}"
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Empresa de prueba"


def test_consultar_cliente_inexistente(api_client):
    response = api_client.get("/clients/9999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Cliente no encontrado"


def test_crear_cliente_sin_nombre(api_client):
    response = api_client.post(
        "/clients",
        json={
            "name": "   ",
            "email": "contacto@agencia.es"
        }
    )

    assert response.status_code == 400


def test_actualizar_cliente_desde_api(api_client):
    cliente = add_client("Nombre antiguo", "antiguo@example.com")

    response = api_client.put(
        f"/clients/{cliente['id']}",
        json={
            "name": "Nombre actualizado",
            "email": "nuevo@example.com"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == cliente["id"]
    assert data["name"] == "Nombre actualizado"
    assert data["email"] == "nuevo@example.com"

    # Comprobar que los cambios persisten en SQLite.
    consulta = api_client.get(f"/clients/{cliente['id']}")

    assert consulta.status_code == 200
    assert consulta.json()["name"] == "Nombre actualizado"


def test_actualizar_cliente_inexistente_desde_api(api_client):
    response = api_client.put(
        "/clients/9999",
        json={
            "name": "Cliente inexistente",
            "email": None
        }
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Cliente no encontrado"


def test_actualizar_cliente_con_nombre_vacio(api_client):
    cliente = add_client("Cliente válido")

    response = api_client.put(
        f"/clients/{cliente['id']}",
        json={
            "name": "   ",
            "email": None
        }
    )

    assert response.status_code == 400

    # La actualización fallida no debe modificar el cliente.
    consulta = api_client.get(f"/clients/{cliente['id']}")

    assert consulta.json()["name"] == "Cliente válido"


def test_actualizar_cliente_sin_email(api_client):
    cliente = add_client("Cliente original", "original@example.com")

    response = api_client.put(
        f"/clients/{cliente['id']}",
        json={
            "name": "Cliente sin correo"
        }
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Cliente sin correo"
    assert response.json()["email"] is None


def test_eliminar_cliente_desde_api(api_client):
    cliente = add_client("Cliente temporal")

    response = api_client.delete(
        f"/clients/{cliente['id']}"
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Cliente eliminado correctamente"

    # El cliente ya no debe existir.
    consulta = api_client.get(
        f"/clients/{cliente['id']}"
    )

    assert consulta.status_code == 404


def test_eliminar_cliente_inexistente_desde_api(api_client):
    response = api_client.delete("/clients/9999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Cliente no encontrado"


def test_impedir_eliminar_cliente_con_dominios_desde_api(api_client):
    cliente = add_client("Cliente protegido")

    # Asociar un dominio al cliente mediante la API.
    response_domain = api_client.post(
        "/domains",
        json={"domain": "example.com"}
    )

    assert response_domain.status_code == 201

    # Asociar el dominio al cliente en SQLite.
    from app.database.db import get_connection

    with get_connection() as connection:
        connection.execute(
            "UPDATE domains SET client_id = ? WHERE id = ?",
            (cliente["id"], response_domain.json()["id"])
        )
        connection.commit()

    # Intentar eliminar el cliente.
    response = api_client.delete(
        f"/clients/{cliente['id']}"
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "No se puede eliminar un cliente con dominios asociados"
    )

    # Comprobar que el cliente sigue existiendo.
    consulta = api_client.get(
        f"/clients/{cliente['id']}"
    )

    assert consulta.status_code == 200

    # Comprobar que el dominio también sigue existiendo.
    dominios = api_client.get("/domains")

    assert dominios.status_code == 200
    assert len(dominios.json()) == 1
    assert dominios.json()[0]["client_id"] == cliente["id"]


def test_dominios_cliente_vacio(api_client):
    cliente = add_client("Cliente sin dominios")

    response = api_client.get(
        f"/clients/{cliente['id']}/domains"
    )

    assert response.status_code == 200
    assert response.json() == []


def test_dominios_cliente_inexistente(api_client):
    response = api_client.get("/clients/9999/domains")

    assert response.status_code == 404
    assert response.json()["detail"] == "Cliente no encontrado"


def test_consultar_dominios_de_un_cliente(api_client):
    cliente = add_client("Agencia Málaga")

    add_domain("example.com", cliente["id"])

    response = api_client.get(
        f"/clients/{cliente['id']}/domains"
    )

    assert response.status_code == 200

    dominios = response.json()

    assert len(dominios) == 1
    assert dominios[0]["domain"] == "example.com"
    assert dominios[0]["client_id"] == cliente["id"]


def test_aislamiento_dominios_entre_clientes(api_client):
    cliente_a = add_client("Cliente A")
    cliente_b = add_client("Cliente B")

    add_domain("example.com", cliente_a["id"])
    add_domain("www.google.com", cliente_b["id"])

    response_a = api_client.get(
        f"/clients/{cliente_a['id']}/domains"
    )

    response_b = api_client.get(
        f"/clients/{cliente_b['id']}/domains"
    )

    assert response_a.status_code == 200
    assert response_b.status_code == 200

    assert len(response_a.json()) == 1
    assert len(response_b.json()) == 1

    assert response_a.json()[0]["domain"] == "example.com"
    assert response_b.json()[0]["domain"] == "www.google.com"


def test_crear_dominio_asociado_a_cliente_desde_api(api_client):
    cliente = add_client("Agencia Málaga")

    response = api_client.post(
        "/domains",
        json={
            "domain": "example.com",
            "client_id": cliente["id"]
        }
    )

    assert response.status_code == 201
    assert response.json()["domain"] == "example.com"
    assert response.json()["client_id"] == cliente["id"]

    # Comprobar que aparece en los dominios del cliente.
    consulta = api_client.get(
        f"/clients/{cliente['id']}/domains"
    )

    assert consulta.status_code == 200
    assert len(consulta.json()) == 1
    assert consulta.json()[0]["domain"] == "example.com"


def test_crear_dominio_sin_cliente_desde_api(api_client):
    response = api_client.post(
        "/domains",
        json={
            "domain": "example.com"
        }
    )

    assert response.status_code == 201
    assert response.json()["domain"] == "example.com"

    # Un dominio sin cliente no debe aparecer
    # asociado a ninguna empresa.
    dominios = api_client.get("/domains")

    assert dominios.status_code == 200
    assert dominios.json()[0]["client_id"] is None


def test_crear_dominio_con_cliente_inexistente_desde_api(api_client):
    response = api_client.post(
        "/domains",
        json={
            "domain": "example.com",
            "client_id": 9999
        }
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "El cliente indicado no existe"

    # No debe haberse registrado ningún dominio.
    dominios = api_client.get("/domains")

    assert dominios.json() == []


def test_impedir_dominio_duplicado_entre_clientes_desde_api(api_client):
    cliente_a = add_client("Cliente A")
    cliente_b = add_client("Cliente B")

    primera_respuesta = api_client.post(
        "/domains",
        json={
            "domain": "example.com",
            "client_id": cliente_a["id"]
        }
    )

    segunda_respuesta = api_client.post(
        "/domains",
        json={
            "domain": "example.com",
            "client_id": cliente_b["id"]
        }
    )

    assert primera_respuesta.status_code == 201
    assert segunda_respuesta.status_code == 400
    assert segunda_respuesta.json()["detail"] == (
        "Este dominio ya está registrado"
    )

    # El dominio debe seguir perteneciendo al primer cliente.
    dominios = api_client.get("/domains")

    assert len(dominios.json()) == 1
    assert dominios.json()[0]["client_id"] == cliente_a["id"]
