
import os

from app.database.email_repository import (
    get_pending_notifications,
    claim_notification,
    mark_notification_sent,
    mark_notification_failed
)

from app.services.email_notifier import send_alert_email


MAX_ATTEMPTS = 3


def notifications_enabled():
    """
    Comprueba si el envío de correos está activado.
    """
    return os.getenv(
        "WEBGUARD_EMAIL_ENABLED", "false"
    ).lower() == "true"


def retry_notifications():
    """
    Recupera notificaciones pendientes o fallidas
    e intenta enviarlas mediante SMTP.

    Cada notificación debe reservarse antes
    de intentar su envío.
    """

    print("\n=== WEBGUARD: REINTENTO DE NOTIFICACIONES ===")

    if not notifications_enabled():
        print("Notificaciones por correo desactivadas.")
        return []

    notifications = get_pending_notifications(
        max_attempts=MAX_ATTEMPTS
    )

    if not notifications:
        print("No hay notificaciones disponibles para enviar.")
        return []

    results = []

    for notification in notifications:

        notification_id = notification["id"]
        recipient = notification["recipient"]

        # 1. Intentar reservar la notificación.
        claimed = claim_notification(
            notification_id,
            max_attempts=MAX_ATTEMPTS
        )

        if not claimed:
            print(
                f"Notificación {notification_id}: "
                "no disponible para reservar."
            )
            continue

        print(
            f"\nNotificación {notification_id} reservada."
        )

        # 2. Reconstruir el correo desde SQLite.
        alert = {
            "domain": notification["domain"],
            "severity": notification["severity"],
            "message": notification["message"]
        }

        # 3. Intentar el envío.
        try:
            send_alert_email(alert, recipient)

        except Exception as error:
            mark_notification_failed(
                notification_id,
                error
            )

            print(
                f"Error enviando notificación "
                f"{notification_id}: {error}"
            )

            results.append({
                "notification_id": notification_id,
                "success": False,
                "error": str(error)
            })

            continue

        # 4. Registrar el envío aceptado por SMTP.
        mark_notification_sent(notification_id)

        print(
            f"Notificación {notification_id}: "
            "correo aceptado por SMTP."
        )

        results.append({
            "notification_id": notification_id,
            "success": True
        })

    successful = sum(
        1 for result in results
        if result["success"]
    )

    print("\n=== REINTENTOS FINALIZADOS ===")
    print(f"Notificaciones procesadas: {len(results)}")
    print(f"Correos aceptados por SMTP: {successful}")
    print(f"Fallos: {len(results) - successful}")

    return results


if __name__ == "__main__":
    retry_notifications()
