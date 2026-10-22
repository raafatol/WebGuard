import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

from app.database.db import get_connection


SESSION_DURATION_HOURS = 12


def _hash_token(token: str) -> str:
    """Calcula el hash SHA-256 de un token de sesión."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(user_id: int) -> str:
    """
    Crea una sesión y devuelve el token secreto.

    En SQLite únicamente se almacena su hash.
    """

    token = secrets.token_urlsafe(32)
    token_hash = _hash_token(token)

    expires_at = (
        datetime.now(timezone.utc)
        + timedelta(hours=SESSION_DURATION_HOURS)
    ).isoformat()

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO user_sessions (user_id, token_hash, expires_at)
            SELECT id, ?, ?
            FROM users
            WHERE id = ? AND is_active = 1
            """,
            (token_hash, expires_at, user_id),
        )

        if connection.total_changes != 1:
            raise ValueError("Usuario inexistente o inactivo")

        connection.commit()

    return token


def get_session_user(token: str):
    """
    Obtiene el usuario asociado a una sesión válida.

    Devuelve None si la sesión no existe, ha caducado
    o el usuario está desactivado.
    """

    if not isinstance(token, str) or not token:
        return None

    token_hash = _hash_token(token)
    now = datetime.now(timezone.utc).isoformat()

    with get_connection() as connection:
        connection.row_factory = sqlite3.Row

        row = connection.execute(
            """
            SELECT
                users.id,
                users.email,
                users.role,
                users.is_active,
                users.organization_id
            FROM user_sessions
            JOIN users ON users.id = user_sessions.user_id
            WHERE user_sessions.token_hash = ?
              AND user_sessions.revoked_at IS NULL
              AND user_sessions.expires_at > ?
              AND users.is_active = 1
            """,
            (token_hash, now),
        ).fetchone()

        return dict(row) if row else None


def revoke_session(token: str) -> bool:
    """Revoca una sesión existente."""

    if not isinstance(token, str) or not token:
        return False

    token_hash = _hash_token(token)

    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE user_sessions
            SET revoked_at = ?
            WHERE token_hash = ?
              AND revoked_at IS NULL
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                token_hash,
            ),
        )

        connection.commit()

        return cursor.rowcount > 0