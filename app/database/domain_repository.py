
import sqlite3

from app.database.db import get_connection
from app.services.domain_validator import validate_domain


def add_domain(domain, client_id=None):
    """
    Registra un dominio en WebGuard.

    Opcionalmente permite asociarlo a un cliente.
    """

    # Validamos el dominio antes de guardarlo.
    domain = validate_domain(domain)

    with get_connection() as connection:

        # Comprobamos que el cliente exista, si se proporciona.
        if client_id is not None:
            client = connection.execute(
                "SELECT id FROM clients WHERE id = ?",
                (client_id,)
            ).fetchone()

            if client is None:
                raise ValueError(
                    "El cliente indicado no existe"
                )

        try:
            cursor = connection.execute(
                """
                INSERT INTO domains (domain, client_id)
                VALUES (?, ?)
                """,
                (domain, client_id)
            )

            connection.commit()

            # Conservamos la respuesta anterior cuando
            # no se indica ningún cliente.
            result = {
                "id": cursor.lastrowid,
                "domain": domain
            }

            if client_id is not None:
                result["client_id"] = client_id

            return result

        except sqlite3.IntegrityError as error:
            if error.sqlite_errorname == "SQLITE_CONSTRAINT_UNIQUE":
                raise ValueError(
                    "Este dominio ya está registrado"
                ) from error

            raise


def get_domains():
    """
    Recupera todos los dominios registrados.
    """

    with get_connection() as connection:
        connection.row_factory = sqlite3.Row

        cursor = connection.execute("""
            SELECT
                domains.id,
                domains.domain,
                domains.created_at,
                domains.client_id,
                clients.name AS client_name
            FROM domains
            LEFT JOIN clients
                ON domains.client_id = clients.id
            ORDER BY domains.id
        """)

        return [dict(row) for row in cursor.fetchall()]


def get_domains_by_client(client_id):
    """
    Recupera los dominios asociados a un cliente.
    """

    with get_connection() as connection:
        connection.row_factory = sqlite3.Row

        cursor = connection.execute(
            """
            SELECT id, domain, created_at, client_id
            FROM domains
            WHERE client_id = ?
            ORDER BY id
            """,
            (client_id,)
        )

        return [dict(row) for row in cursor.fetchall()]


def delete_domain(domain_id):
    """
    Elimina un dominio mediante su identificador.
    """

    with get_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM domains WHERE id = ?",
            (domain_id,)
        )

        connection.commit()

        return cursor.rowcount > 0
