"""
Protección CSRF para sesiones autenticadas de WebGuard.

El token CSRF se deriva mediante HMAC-SHA256 del token
de sesión y de una clave secreta independiente.
"""

import hashlib
import hmac
import os


def _get_csrf_secret() -> bytes:
    secret = os.environ.get("WEBGUARD_CSRF_SECRET", "")

    if len(secret) < 32:
        raise RuntimeError(
            "WEBGUARD_CSRF_SECRET debe contener "
            "al menos 32 caracteres."
        )

    return secret.encode("utf-8")


def generate_csrf_token(session_token: str) -> str:
    """Genera un token CSRF asociado a una sesión."""

    return hmac.new(
        _get_csrf_secret(),
        session_token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_csrf_token(
    session_token: str,
    supplied_token: str | None,
) -> bool:
    """Verifica el token mediante comparación constante."""

    if not isinstance(supplied_token, str):
        return False

    expected = generate_csrf_token(session_token)

    return hmac.compare_digest(
        expected,
        supplied_token,
    )
