
import sqlite3

from app.database.db import get_connection


def add_client(name, email=None):
    """
    Registra un nuevo cliente en WebGuard.

    El nombre es obligatorio y el correo electrónico
    es opcional.
    """

    if not isinstance(name, str) or not name.strip():
        raise ValueError("El nombre del cliente es obligatorio")

    name = name.strip()

    if email is not None:
        if not isinstance(email, str):
            raise ValueError("El correo electrónico debe ser texto")

        email = email.strip() or None

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO clients (name, email)
            VALUES (?, ?)
            """,
            (name, email)
        )

        connection.commit()

        return {
            "id": cursor.lastrowid,
            "name": name,
            "email": email
        }


def get_clients():
    """
    Recupera todos los clientes registrados en WebGuard.
    """

    with get_connection() as connection:
        connection.row_factory = sqlite3.Row

        cursor = connection.execute("""
            SELECT id, name, email, created_at
            FROM clients
            ORDER BY id
        """)

        return [dict(row) for row in cursor.fetchall()]


def get_client_by_id(client_id):
    """
    Recupera un cliente mediante su identificador.

    Devuelve None si el cliente no existe.
    """

    with get_connection() as connection:
        connection.row_factory = sqlite3.Row

        cursor = connection.execute(
            """
            SELECT id, name, email, created_at
            FROM clients
            WHERE id = ?
            """,
            (client_id,)
        )

        row = cursor.fetchone()

        return dict(row) if row is not None else None


def update_client(client_id, name, email=None):
    """
    Actualiza el nombre y correo de un cliente.

    Devuelve el cliente actualizado o None si no existe.
    """

    if not isinstance(name, str) or not name.strip():
        raise ValueError("El nombre del cliente es obligatorio")

    name = name.strip()

    if email is not None:
        if not isinstance(email, str):
            raise ValueError("El correo electrónico debe ser texto")

        email = email.strip() or None

    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE clients
            SET name = ?, email = ?
            WHERE id = ?
            """,
            (name, email, client_id)
        )

        if cursor.rowcount == 0:
            return None

        connection.commit()

    return get_client_by_id(client_id)


def delete_client(client_id):
    """
    Elimina un cliente únicamente si no tiene dominios.

    Devuelve:
        True: cliente eliminado.
        False: cliente inexistente.

    Lanza ValueError si tiene dominios asociados.
    """

    with get_connection() as connection:

        # Comprobamos si el cliente existe.
        client = connection.execute(
            "SELECT id FROM clients WHERE id = ?",
            (client_id,)
        ).fetchone()

        if client is None:
            return False

        # Comprobamos si tiene dominios asociados.
        domains_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM domains
            WHERE client_id = ?
            """,
            (client_id,)
        ).fetchone()[0]

        if domains_count > 0:
            raise ValueError(
                "No se puede eliminar un cliente con dominios asociados"
            )

        # Si no tiene dominios, podemos eliminarlo.
        cursor = connection.execute(
            "DELETE FROM clients WHERE id = ?",
            (client_id,)
        )

        connection.commit()

        return cursor.rowcount > 0
