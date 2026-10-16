
import sqlite3
from pathlib import Path


# Ruta principal del proyecto WebGuard
BASE_DIR = Path(__file__).resolve().parents[2]

# Archivo de base de datos SQLite
DB_PATH = BASE_DIR / "webguard.db"


def get_connection():
    """
    Establece una conexión con la base de datos.
    """
    return sqlite3.connect(DB_PATH)


def init_db():
    """
    Inicializa las tablas necesarias para WebGuard.

    Las tablas existentes se conservan.
    """

    with get_connection() as connection:

        # ==========================================
        # TABLA DE DOMINIOS
        # ==========================================

        connection.execute("""
            CREATE TABLE IF NOT EXISTS domains (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ==========================================
        # TABLA DE ANÁLISIS
        # ==========================================

        connection.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL,
                analyzed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                tls_valid INTEGER,
                tls_days_left INTEGER,
                http_status INTEGER,
                headers_present INTEGER,
                headers_total INTEGER,
                headers_json TEXT
            )
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_analyses_domain
            ON analyses (domain, analyzed_at)
        """)

        # ==========================================
        # TABLA DE ALERTAS - WEBGUARD v0.6
        # ==========================================

        connection.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL,
                analysis_id INTEGER NOT NULL,
                alert_type TEXT NOT NULL,
                header TEXT,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (analysis_id)
                    REFERENCES analyses(id),

                UNIQUE (analysis_id, alert_type, header)
            )
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_alerts_domain
            ON alerts (domain, created_at)
        """)

        # ==========================================
        # TABLA DE NOTIFICACIONES - WEBGUARD v0.7
        # ==========================================

        connection.execute("""
            CREATE TABLE IF NOT EXISTS email_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                alert_id INTEGER NOT NULL,
                recipient TEXT NOT NULL,

                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK (
                        status IN (
                            'pending',
                            'sending',
                            'sent',
                            'failed'
                        )
                    ),

                attempts INTEGER NOT NULL DEFAULT 0
                    CHECK (attempts >= 0),

                last_error TEXT,

                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                sent_at TEXT,

                next_attempt_at TEXT,

                claimed_at TEXT,

                FOREIGN KEY (alert_id)
                    REFERENCES alerts(id),

                UNIQUE (alert_id, recipient)
            )
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_email_notifications_status
            ON email_notifications (status, created_at)
        """)

        connection.commit()
