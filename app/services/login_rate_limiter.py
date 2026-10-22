import hashlib
import hmac
import os
import secrets
import time

from app.database.db import get_connection


WINDOW_SECONDS = 15 * 60

MAX_ACCOUNT_IP_ATTEMPTS = 5
MAX_IP_ATTEMPTS = 30

# Clave estable y privada para derivar identificadores de cuentas.
RATE_LIMIT_SECRET = os.environ.get(
    "WEBGUARD_RATE_LIMIT_SECRET", ""
)

if len(RATE_LIMIT_SECRET) < 32:
    raise RuntimeError(
        "Configura WEBGUARD_RATE_LIMIT_SECRET "
        "con una clave aleatoria de al menos 32 caracteres"
    )


def account_key(email: str) -> str:
    normalized = email.strip().lower()

    return hmac.new(
        RATE_LIMIT_SECRET.encode(),
        normalized.encode(),
        hashlib.sha256,
    ).hexdigest()


def is_login_blocked(email: str, ip_address: str) -> bool:
    now = int(time.time())
    cutoff = now - WINDOW_SECONDS
    key = account_key(email)

    with get_connection() as connection:
        account_ip_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM login_attempts
            WHERE account_key = ?
              AND ip_address = ?
              AND attempted_at > ?
            """,
            (key, ip_address, cutoff),
        ).fetchone()[0]

        ip_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM login_attempts
            WHERE ip_address = ?
              AND attempted_at > ?
            """,
            (ip_address, cutoff),
        ).fetchone()[0]

    return (
        account_ip_count >= MAX_ACCOUNT_IP_ATTEMPTS
        or ip_count >= MAX_IP_ATTEMPTS
    )


def record_failed_login(email: str, ip_address: str):
    now = int(time.time())

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO login_attempts (
                account_key,
                ip_address,
                attempted_at
            )
            VALUES (?, ?, ?)
            """,
            (account_key(email), ip_address, now),
        )

        connection.commit()


def clear_login_attempts(email: str, ip_address: str):
    with get_connection() as connection:
        connection.execute(
            """
            DELETE FROM login_attempts
            WHERE account_key = ?
              AND ip_address = ?
            """,
            (account_key(email), ip_address),
        )

        connection.commit()

def reserve_login_attempt(email: str, ip_address: str) -> bool:
    """
    Reserva un intento de login de forma atómica.

    Devuelve:
        True: se permite comprobar la contraseña.
        False: se ha alcanzado el límite.
    """
    now = int(time.time())
    cutoff = now - WINDOW_SECONDS
    key = account_key(email)

    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")

        try:
            # Eliminar registros que ya no cuentan.
            connection.execute(
                """
                DELETE FROM login_attempts
                WHERE attempted_at <= ?
                """,
                (cutoff,),
            )

            # Intentos de esta cuenta desde esta IP.
            account_ip_count = connection.execute(
                """
                SELECT COUNT(*)
                FROM login_attempts
                WHERE account_key = ?
                  AND ip_address = ?
                  AND attempted_at > ?
                """,
                (key, ip_address, cutoff),
            ).fetchone()[0]

            # Intentos totales desde esta IP.
            ip_count = connection.execute(
                """
                SELECT COUNT(*)
                FROM login_attempts
                WHERE ip_address = ?
                  AND attempted_at > ?
                """,
                (ip_address, cutoff),
            ).fetchone()[0]

            if (
                account_ip_count >= MAX_ACCOUNT_IP_ATTEMPTS
                or ip_count >= MAX_IP_ATTEMPTS
            ):
                connection.commit()
                return False

            # Reservar el intento antes de verificar la contraseña.
            connection.execute(
                """
                INSERT INTO login_attempts (
                    account_key,
                    ip_address,
                    attempted_at
                )
                VALUES (?, ?, ?)
                """,
                (key, ip_address, now),
            )

            connection.commit()
            return True

        except Exception:
            connection.rollback()
            raise