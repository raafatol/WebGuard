
import sqlite3

from app.database.db import get_connection
from app.services.domain_validator import validate_domain


def add_domain(domain):
    # Validamos el dominio antes de guardarlo
    domain = validate_domain(domain)

    with get_connection() as connection:
        try:
            cursor = connection.execute(
                "INSERT INTO domains (domain) VALUES (?)",
                (domain,)
            )

            connection.commit()

            return {
                "id": cursor.lastrowid,
                "domain": domain
            }

        except sqlite3.IntegrityError:
            raise ValueError(
                "Este dominio ya está registrado"
            )


def get_domains():
    with get_connection() as connection:
        connection.row_factory = sqlite3.Row

        cursor = connection.execute(
            "SELECT id, domain, created_at "
            "FROM domains ORDER BY id"
        )

        return [dict(row) for row in cursor.fetchall()]


def delete_domain(domain_id):
    with get_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM domains WHERE id = ?",
            (domain_id,)
        )

        connection.commit()

        return cursor.rowcount > 0
