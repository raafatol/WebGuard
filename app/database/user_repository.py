import sqlite3

from argon2 import PasswordHasher
from argon2.exceptions import (
    VerifyMismatchError,
    VerificationError,
    InvalidHashError,
)

from app.database.db import get_connection


# Argon2id es el algoritmo predeterminado de PasswordHasher.
password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Genera un hash seguro de la contraseña."""
    if not isinstance(password, str) or not password:
        raise ValueError("La contraseña no puede estar vacía")

    return password_hasher.hash(password)


def verify_password(password: str, stored_hash: str) -> bool:
    """Comprueba una contraseña sin almacenar el texto original."""
    try:
        return password_hasher.verify(stored_hash, password)

    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def get_user_by_email(email: str):
    """Busca un usuario por su correo electrónico."""

    with get_connection() as connection:
        connection.row_factory = sqlite3.Row

        row = connection.execute(
            """
            SELECT id, email, password_hash, role,
                   is_active, created_at
            FROM users
            WHERE email = ?
            """,
            (email.strip(),),
        ).fetchone()

        return dict(row) if row else None


def get_user_by_id(user_id: int):
    """Busca un usuario por su identificador."""

    with get_connection() as connection:
        connection.row_factory = sqlite3.Row

        row = connection.execute(
            """
            SELECT id, email, role, is_active, created_at
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()

        return dict(row) if row else None


def create_agency_user(email: str, password: str):
    """
    Crea una cuenta de agencia.

    El rol se establece exclusivamente en el servidor.
    """

    normalized_email = email.strip().lower()
    password_hash = hash_password(password)

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO users (email, password_hash, role)
            VALUES (?, ?, 'agency')
            """,
            (normalized_email, password_hash),
        )

        connection.commit()

        return cursor.lastrowid