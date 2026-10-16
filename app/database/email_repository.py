
import sqlite3

from app.database.db import get_connection


def create_notification(alert_id, recipient):
    """
    Registra una notificación pendiente.

    Si ya existe una notificación para la misma
    alerta y destinatario, no crea un duplicado.
    """

    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT OR IGNORE INTO email_notifications (
                alert_id,
                recipient
            )
            VALUES (?, ?)
        """, (alert_id, recipient))

        connection.commit()

        if cursor.rowcount > 0:
            return cursor.lastrowid

        return None

def mark_notification_sent(notification_id):
    """
    Marca una notificación como enviada
    después de que SMTP acepte el correo.
    """

    with get_connection() as connection:

        cursor = connection.execute("""
            UPDATE email_notifications

            SET status = 'sent',
                attempts = attempts + 1,
                last_error = NULL,
                sent_at = CURRENT_TIMESTAMP,
                claimed_at = NULL,
                next_attempt_at = NULL

            WHERE id = ?
              AND status = 'sending'
        """, (notification_id,))

        connection.commit()

        return cursor.rowcount == 1

def mark_notification_failed(
    notification_id,
    error,
    retry_delay_minutes=5
):
    """
    Registra un envío fallido.

    Incrementa los intentos y programa
    el siguiente reintento para dentro
    de unos minutos.
    """

    with get_connection() as connection:

        cursor = connection.execute("""
            UPDATE email_notifications

            SET status = 'failed',
                attempts = attempts + 1,
                last_error = ?,
                claimed_at = NULL,
                next_attempt_at = datetime(
                    'now',
                    '+' || ? || ' minutes'
                )

            WHERE id = ?
              AND status = 'sending'
        """, (
            str(error),
            retry_delay_minutes,
            notification_id
        ))

        connection.commit()

        return cursor.rowcount == 1



def get_pending_notifications(max_attempts=3):
    """
    Recupera notificaciones pendientes o fallidas
    que están listas para enviarse.

    Respeta el máximo de intentos y el tiempo
    de espera entre reintentos.
    """

    with get_connection() as connection:
        connection.row_factory = sqlite3.Row

        cursor = connection.execute("""
            SELECT
                n.id,
                n.alert_id,
                n.recipient,
                n.status,
                n.attempts,
                n.last_error,
                n.created_at,
                a.domain,
                a.severity,
                a.message

            FROM email_notifications AS n

            JOIN alerts AS a
                ON n.alert_id = a.id

            WHERE n.status IN ('pending', 'failed')
              AND n.attempts < ?
              AND (
                  n.next_attempt_at IS NULL
                  OR n.next_attempt_at <= CURRENT_TIMESTAMP
              )

            ORDER BY n.created_at ASC, n.id ASC
            LIMIT 100
        """, (max_attempts,))

        return [
            dict(row)
            for row in cursor.fetchall()
        ]


def get_notifications():
    """
    Recupera las últimas 100 notificaciones,
    independientemente de su estado.
    """

    with get_connection() as connection:
        connection.row_factory = sqlite3.Row

        cursor = connection.execute("""
            SELECT
                id,
                alert_id,
                recipient,
                status,
                attempts,
                last_error,
                created_at,
                sent_at

            FROM email_notifications

            ORDER BY created_at DESC, id DESC
            LIMIT 100
        """)

        return [
            dict(row)
            for row in cursor.fetchall()
        ]


def claim_notification(notification_id, max_attempts=3):
    """
    Reserva una notificación para su envío.

    Solo permite reservar notificaciones pendientes
    o fallidas que no hayan agotado sus intentos.

    Devuelve True si consigue la reserva.
    Devuelve False si otro proceso ya la reservó,
    si está enviada o si agotó sus intentos.
    """

    with get_connection() as connection:

        cursor = connection.execute("""
            UPDATE email_notifications

            SET status = 'sending',
                claimed_at = CURRENT_TIMESTAMP

            WHERE id = ?
              AND status IN ('pending', 'failed')
              AND attempts < ?
              AND (
                  next_attempt_at IS NULL
                  OR next_attempt_at <= CURRENT_TIMESTAMP
              )
        """, (notification_id, max_attempts))

        connection.commit()

        return cursor.rowcount == 1


def recover_stale_notifications(timeout_minutes=10):
    """
    Detecta notificaciones que llevan demasiado
    tiempo en estado 'sending'.

    Las marca como 'failed' y agota sus intentos
    automáticos para evitar reenvíos inciertos.

    Devuelve el número de reservas recuperadas.
    """

    with get_connection() as connection:

        cursor = connection.execute("""
            UPDATE email_notifications

            SET status = 'failed',
                attempts = MAX(attempts, 3),
                last_error =
                    'Reserva abandonada: el resultado '
                    || 'del envío SMTP es desconocido. '
                    || 'Requiere revisión manual.',
                claimed_at = NULL,
                next_attempt_at = NULL

            WHERE status = 'sending'
              AND claimed_at IS NOT NULL
              AND claimed_at <= datetime(
                  'now',
                  '-' || ? || ' minutes'
              )
        """, (timeout_minutes,))

        connection.commit()

        return cursor.rowcount
