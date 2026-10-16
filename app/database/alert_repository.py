
import sqlite3

from app.database.db import get_connection


def save_alert(domain, analysis_id, change):
    """
    Guarda una alerta generada por el detector de cambios.

    Evita duplicar una misma alerta para un análisis.
    """

    with get_connection() as connection:

        cursor = connection.execute("""
            INSERT OR IGNORE INTO alerts (
                domain,
                analysis_id,
                alert_type,
                header,
                severity,
                message
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            domain,
            analysis_id,
            change["type"],
            change.get("header"),
            change["severity"],
            change["message"]
        ))

        connection.commit()

        return cursor.lastrowid if cursor.rowcount > 0 else None


def get_alerts(domain=None):
    """
    Recupera las últimas 100 alertas.

    Si se indica un dominio, devuelve únicamente
    las alertas de ese dominio.
    """

    with get_connection() as connection:
        connection.row_factory = sqlite3.Row

        if domain is None:
            cursor = connection.execute("""
                SELECT
                    id,
                    domain,
                    analysis_id,
                    alert_type,
                    header,
                    severity,
                    message,
                    created_at
                FROM alerts
                ORDER BY created_at DESC, id DESC
                LIMIT 100
            """)

        else:
            cursor = connection.execute("""
                SELECT
                    id,
                    domain,
                    analysis_id,
                    alert_type,
                    header,
                    severity,
                    message,
                    created_at
                FROM alerts
                WHERE domain = ?
                ORDER BY created_at DESC, id DESC
                LIMIT 100
            """, (domain,))

        return [
            dict(row)
            for row in cursor.fetchall()
        ]
