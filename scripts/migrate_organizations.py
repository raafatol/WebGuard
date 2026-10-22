import sqlite3
from app.database.db import DB_PATH

with sqlite3.connect(DB_PATH) as db:
    db.execute("PRAGMA foreign_keys = ON")

    # Evitar una segunda migración accidental.
    existing = db.execute("""
        SELECT name FROM sqlite_master
        WHERE type = 'table' AND name = 'organizations'
    """).fetchone()

    if existing:
        raise SystemExit("La migración ya existe. No se han realizado cambios.")

    users = db.execute("SELECT id FROM users").fetchall()

    if len(users) != 1:
        raise SystemExit(
            "Se esperaba exactamente un usuario. "
            "Migración cancelada."
        )

    original_counts = {
        table: db.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]
        for table in ("users", "clients", "domains", "analyses", "alerts")
    }

    try:
        db.execute("BEGIN IMMEDIATE")

        db.execute("""
            CREATE TABLE organizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor = db.execute(
            "INSERT INTO organizations (name) VALUES (?)",
            ("Organización principal",)
        )
        organization_id = cursor.lastrowid

        for table in ("users", "clients", "analyses"):
            db.execute(
                f"ALTER TABLE {table} "
                "ADD COLUMN organization_id INTEGER "
                "REFERENCES organizations(id)"
            )
            db.execute(
                f"UPDATE {table} SET organization_id = ?",
                (organization_id,)
            )

        # Los dominios pertenecen a la organización de su cliente.
        # La columna permitirá proteger también las consultas directas.
        db.execute("""
            ALTER TABLE domains
            ADD COLUMN organization_id INTEGER
            REFERENCES organizations(id)
        """)

        db.execute("""
            UPDATE domains
            SET organization_id = (
                SELECT organization_id
                FROM clients
                WHERE clients.id = domains.client_id
            )
        """)

        db.execute("""
            ALTER TABLE alerts
            ADD COLUMN organization_id INTEGER
            REFERENCES organizations(id)
        """)

        db.execute("""
            UPDATE alerts
            SET organization_id = (
                SELECT organization_id
                FROM analyses
                WHERE analyses.id = alerts.analysis_id
            )
        """)

        for table in ("users", "clients", "domains", "analyses", "alerts"):
            db.execute(
                f"CREATE INDEX idx_{table}_organization "
                f"ON {table}(organization_id)"
            )

        new_counts = {
            table: db.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]
            for table in original_counts
        }

        if new_counts != original_counts:
            raise RuntimeError("El número de registros ha cambiado")

        for table in original_counts:
            missing = db.execute(
                f"SELECT COUNT(*) FROM {table} "
                "WHERE organization_id IS NULL"
            ).fetchone()[0]
            if missing:
                raise RuntimeError(
                    f"{table}: {missing} registros sin organización"
                )

        invalid = db.execute("PRAGMA foreign_key_check").fetchall()
        if invalid:
            raise RuntimeError(f"Claves foráneas inválidas: {invalid}")

        db.commit()

    except Exception:
        db.rollback()
        raise

    print("MIGRACIÓN COMPLETADA")
    print("Organización inicial:", organization_id)
    for table, count in new_counts.items():
        print(f"{table}: {count} registros conservados")
    print("Claves foráneas: OK")
