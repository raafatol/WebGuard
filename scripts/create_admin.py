import getpass
import sqlite3
import sys
from pathlib import Path

# Permite ejecutar el script desde la raíz del proyecto.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database.db import get_connection, init_db
from app.database.user_repository import hash_password


def main():
    init_db()

    print("\n=== WEBGUARD: ADMINISTRADOR INICIAL ===\n")

    with get_connection() as connection:
        existing_admin = connection.execute(
            "SELECT id FROM users WHERE role = 'admin' LIMIT 1"
        ).fetchone()

    if existing_admin:
        print("Ya existe un administrador.")
        print("Este script no permite crear otro.")
        return

    email = input("Correo del administrador: ").strip().lower()

    if not email or "@" not in email:
        print("Error: introduce un correo válido.")
        return

    password = getpass.getpass("Contraseña: ")
    confirmation = getpass.getpass("Repite la contraseña: ")

    if password != confirmation:
        print("Error: las contraseñas no coinciden.")
        return

    if len(password) < 12 or len(password.encode("utf-8")) > 1024:
        print("Error: utiliza una contraseña de entre 12 caracteres y 1024 bytes.")
        return

    password_hash = hash_password(password)

    try:
        with get_connection() as connection:
            # La comprobación se repite dentro de una transacción
            # para impedir creaciones simultáneas.
            connection.execute("BEGIN IMMEDIATE")

            existing_admin = connection.execute(
                "SELECT id FROM users WHERE role = 'admin' LIMIT 1"
            ).fetchone()

            if existing_admin:
                print("Ya existe un administrador.")
                return

            connection.execute(
                """
                INSERT INTO users (email, password_hash, role)
                VALUES (?, ?, 'admin')
                """,
                (email, password_hash),
            )

            connection.commit()

    except sqlite3.IntegrityError:
        print("Error: el correo ya está registrado.")
        return

    print("\nAdministrador creado correctamente.")
    print("Rol asignado: admin")


if __name__ == "__main__":
    main()