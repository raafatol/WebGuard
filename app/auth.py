import os
import secrets

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, EmailStr

from app.database.user_repository import (
    get_user_by_email,
    verify_password,
)
from app.database.session_repository import (
    create_session,
    get_session_user,
    revoke_session,
    SESSION_DURATION_HOURS,
)

from app.services.login_rate_limiter import (
    reserve_login_attempt,
)


router = APIRouter(prefix="/auth", tags=["Autenticación"])

from argon2 import PasswordHasher

_dummy_hasher = PasswordHasher()

DUMMY_PASSWORD_HASH = _dummy_hasher.hash(
    "WebGuard-Dummy-Password-Not-A-Real-Account"
)

COOKIE_NAME = "webguard_session"
CSRF_COOKIE_NAME = "webguard_csrf"

# Solo se permite desactivar Secure en desarrollo local.
LOCAL_DEV = os.getenv("WEBGUARD_LOCAL_DEV") == "1"


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    password: str


def get_current_user(
    session_token: str | None = Cookie(
        default=None,
        alias=COOKIE_NAME,
    ),
):
    if not session_token:
        raise HTTPException(
            status_code=401,
            detail="Autenticación requerida",
        )

    user = get_session_user(session_token)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Sesión inválida o caducada",
        )

    return user


@router.post("/login")
def login(
    data: LoginRequest,
    request: Request,
    response: Response,
):
    ip_address = (
        request.client.host
        if request.client
        else "unknown"
    )

    if not reserve_login_attempt(data.email, ip_address):
        raise HTTPException(
            status_code=429,
            detail="Demasiados intentos. Inténtalo más tarde.",
            headers={"Retry-After": "900"},
        )

    user = get_user_by_email(data.email)

    stored_hash = (
        user["password_hash"]
        if user is not None
        else DUMMY_PASSWORD_HASH
    )

    password_valid = verify_password(
        data.password,
        stored_hash,
    )

    if (
        user is None
        or not user["is_active"]
        or not password_valid
    ):
        raise HTTPException(
            status_code=401,
            detail="Credenciales incorrectas",
        )

    token = create_session(user["id"])

    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=SESSION_DURATION_HOURS * 3600,
        httponly=True,
        secure=not LOCAL_DEV,
        samesite="strict",
        path="/",
    )

    return {
        "message": "Sesión iniciada correctamente",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "role": user["role"],
        },
    }

@router.get("/me")
def me(user=Depends(get_current_user)):
    return {
        "id": user["id"],
        "email": user["email"],
        "role": user["role"],
    }


@router.post("/logout")
def logout(
    response: Response,
    session_token: str | None = Cookie(
        default=None,
        alias=COOKIE_NAME,
    ),
):
    if session_token:
        revoke_session(session_token)

    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        samesite="strict",
        secure=not LOCAL_DEV,
        httponly=True,
    )

    return {"message": "Sesión cerrada correctamente"}