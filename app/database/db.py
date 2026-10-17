
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
    connection = sqlite3.connect(DB_PATH)

    # Activa la comprobación de claves foráneas en SQLite.
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def init_db():
    """
    Inicializa las tablas necesarias para WebGuard.

    Las tablas existentes se conservan y se aplican
    las migraciones necesarias para nuevas versiones.
    """

    with get_connection() as connection:

        # ==========================================
        # TABLA DE CLIENTES - WEBGUARD v0.8
        # ==========================================

        connection.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ==========================================
        # TABLA DE DOMINIOS
        # ==========================================

        connection.execute("""
            CREATE TABLE IF NOT EXISTS domains (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                client_id INTEGER,

                FOREIGN KEY (client_id)
                    REFERENCES clients(id)
            )
        """)

        # ==========================================
        # MIGRACIÓN DE DOMINIOS - WEBGUARD v0.8
        # ==========================================

        # Las bases de datos antiguas no tienen client_id.
        # Comprobamos las columnas antes de modificar la tabla.

        existing_columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(domains)"
            )
        }

        if "client_id" not in existing_columns:
            connection.execute("""
                ALTER TABLE domains
                ADD COLUMN client_id INTEGER
                REFERENCES clients(id)
            """)

        # Índice para consultar los dominios de un cliente.

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_domains_client
            ON domains (client_id)
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
