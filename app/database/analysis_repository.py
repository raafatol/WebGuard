import json
import sqlite3

from app.database.db import get_connection


def save_analysis(result):
    """
    Guarda los resultados de un análisis
    de seguridad en SQLite.
    """

    domain = result["domain"]
    tls = result["tls"]
    http = result["http"]
    redirect_json = json.dumps(result.get("redirect"), ensure_ascii=False) if result.get("redirect") is not None else None

    tls_valid = (
        int(tls["valid"])
        if isinstance(tls.get("valid"), bool)
        else None
    )

    tls_days_left = tls.get("days_left")
    tls_expiry_date = tls.get("expiry_date")
    tls_issuer = tls.get("issuer")
    tls_version = tls.get("tls_version")
    tls_cipher = tls.get("cipher")
    tls_signature_algorithm = tls.get("signature_algorithm")
    http_status = http.get("http_status")
    headers_present = http.get("present_count")
    headers_total = http.get("total_headers")

    headers_json = json.dumps(
        http.get("headers", {}),
        ensure_ascii=False
    )

    with get_connection() as connection:

        cursor = connection.execute("""
            INSERT INTO analyses (
                domain,
                tls_valid,
                tls_days_left,
                tls_expiry_date,
                tls_issuer,
                tls_version,
                tls_cipher,
                tls_signature_algorithm,
                http_status,
                headers_present,
                headers_total,
                headers_json,
                redirect_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            domain,
            tls_valid,
            tls_days_left,
            tls_expiry_date,
            tls_issuer,
            tls_version,
            tls_cipher,
            tls_signature_algorithm,
            http_status,
            headers_present,
            headers_total,
            headers_json,
            redirect_json
        ))

        connection.commit()

        return cursor.lastrowid


def get_analysis_history(domain):
    """
    Recupera el historial de análisis
    de un dominio, del más reciente
    al más antiguo.
    """

    with get_connection() as connection:

        connection.row_factory = __import__("sqlite3").Row

        cursor = connection.execute("""
            SELECT
                id,
                domain,
                analyzed_at,
                tls_valid,
                tls_days_left,
                tls_expiry_date,
                tls_issuer,
                tls_version,
                tls_cipher,
                tls_signature_algorithm,
                http_status,
                headers_present,
                headers_total,
                headers_json,
                redirect_json
            FROM analyses
            WHERE domain = ?
            ORDER BY analyzed_at DESC, id DESC
            LIMIT 50
        """, (domain,))

        analyses = []

        for row in cursor.fetchall():

            analysis = dict(row)

            if analysis["tls_valid"] is not None:
                analysis["tls_valid"] = bool(
                    analysis["tls_valid"]
                )

            analysis["headers"] = json.loads(
                analysis.pop("headers_json") or "{}"
            )

            analysis["redirect"] = json.loads(analysis.pop("redirect_json") or "null")
            analyses.append(analysis)

        return analyses


def get_latest_analysis(domain):
    """
    Recupera el análisis más reciente
    de un dominio.
    """

    with get_connection() as connection:
        connection.row_factory = sqlite3.Row

        cursor = connection.execute("""
            SELECT
                id,
                domain,
                analyzed_at,
                tls_valid,
                tls_days_left,
                tls_expiry_date,
                tls_issuer,
                tls_version,
                tls_cipher,
                tls_signature_algorithm,
                http_status,
                headers_present,
                headers_total,
                redirect_json
            FROM analyses
            WHERE domain = ?
            ORDER BY analyzed_at DESC, id DESC
            LIMIT 1
        """, (domain,))

        row = cursor.fetchone()

        if row is None:
            return None

        analysis = dict(row)

        if analysis["tls_valid"] is not None:
            analysis["tls_valid"] = bool(
                analysis["tls_valid"]
            )

        analysis["redirect"] = json.loads(analysis.pop("redirect_json") or "null")
        return analysis

def get_last_two_analyses(domain):
    """
    Recupera los dos últimos análisis de un dominio,
    incluyendo sus cabeceras HTTP.

    Devuelve una lista ordenada del más reciente
    al más antiguo.
    """

    with get_connection() as connection:
        connection.row_factory = sqlite3.Row

        cursor = connection.execute("""
            SELECT
                id,
                domain,
                analyzed_at,
                tls_valid,
                tls_days_left,
                tls_expiry_date,
                tls_issuer,
                tls_version,
                tls_cipher,
                tls_signature_algorithm,
                http_status,
                headers_present,
                headers_total,
                headers_json,
                redirect_json
            FROM analyses
            WHERE domain = ?
            ORDER BY analyzed_at DESC, id DESC
            LIMIT 2
        """, (domain,))

        analyses = []

        for row in cursor.fetchall():
            analysis = dict(row)

            if analysis["tls_valid"] is not None:
                analysis["tls_valid"] = bool(
                    analysis["tls_valid"]
                )

            analysis["headers"] = json.loads(
                analysis.pop("headers_json") or "{}"
            )

            analysis["redirect"] = json.loads(analysis.pop("redirect_json") or "null")
            analyses.append(analysis)

        return analyses