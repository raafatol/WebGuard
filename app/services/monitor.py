
import os

from app.database.domain_repository import get_domains
from app.database.analysis_repository import (
    save_analysis,
    get_last_two_analyses
)
from app.database.alert_repository import save_alert

from app.database.email_repository import (
    create_notification,
    claim_notification,
    mark_notification_sent,
    mark_notification_failed
)

from app.services.domain_validator import validate_domain
from app.services.security_analyzer import analyze_website
from app.services.change_detector import detect_changes
from app.services.email_notifier import send_alert_email


def notifications_enabled():
    """
    Comprueba si las notificaciones SMTP
    están activadas.
    """
    return os.getenv(
        "WEBGUARD_EMAIL_ENABLED", "false"
    ).lower() == "true"



def notify_new_alert(alert_id, domain, change):
    """
    Registra una notificación y, si el correo
    está activado, la reserva antes de enviarla.

    Solo el proceso que consigue la reserva
    puede intentar el envío SMTP.
    """

    recipient = os.getenv(
        "WEBGUARD_ALERT_RECIPIENT",
        "pruebas@example.com"
    )

    # 1. Registrar la notificación.
    notification_id = create_notification(
        alert_id,
        recipient
    )

    if notification_id is None:
        print(
            "La notificación ya existe. "
            "No se crea un duplicado."
        )
        return False

    print(
        f"Notificación pendiente creada "
        f"(ID: {notification_id})"
    )

    # 2. Comprobar si el correo está activado.
    if not notifications_enabled():
        print(
            "Correo desactivado. "
            "Notificación guardada como pendiente."
        )
        return False

    # 3. Reservar la notificación.
    claimed = claim_notification(notification_id)

    if not claimed:
        print(
            "No se pudo reservar la notificación. "
            "No se enviará el correo."
        )
        return False

    print(
        f"Notificación reservada "
        f"(ID: {notification_id})"
    )

    alert = {
        "domain": domain,
        "severity": change["severity"],
        "message": change["message"]
    }

    # 4. Intentar el envío SMTP.
    try:
        send_alert_email(alert, recipient)

    except Exception as error:

        # 5. Registrar el fallo.
        mark_notification_failed(
            notification_id,
            error
        )

        print(
            f"Error enviando correo "
            f"para {domain}: {error}"
        )

        return False

    # 6. Registrar que SMTP aceptó el correo.
    mark_notification_sent(notification_id)

    print(
        f"Correo aceptado por SMTP "
        f"para {recipient}"
    )

    return True

def monitor_domains():
    """
    Analiza los dominios registrados,
    detecta cambios, guarda alertas
    y registra notificaciones.
    """

    print("\n=== WEBGUARD: INICIANDO MONITORIZACIÓN ===")

    domains = get_domains()

    if not domains:
        print("No hay dominios registrados.")
        return []

    results = []

    for item in domains:
        domain = item["domain"]

        print(f"\nAnalizando: {domain}")

        try:
            validated_domain = validate_domain(domain)

            # 1. Realizar el análisis.
            analysis = analyze_website(validated_domain)

            # 2. Guardarlo en SQLite.
            analysis_id = save_analysis(analysis)

            print(
                f"Análisis guardado correctamente "
                f"(ID: {analysis_id})"
            )

            # 3. Recuperar los últimos análisis.
            analyses = get_last_two_analyses(
                validated_domain
            )

            alerts_created = 0
            emails_sent = 0

            if len(analyses) >= 2:

                current = analyses[0]
                previous = analyses[1]

                # 4. Detectar cambios.
                changes = detect_changes(
                    previous,
                    current
                )

                # 5. Guardar alertas.
                for change in changes:

                    alert_id = save_alert(
                        validated_domain,
                        analysis_id,
                        change
                    )

                    if alert_id is not None:

                        alerts_created += 1

                        print(
                            f"Alerta guardada: "
                            f"{change['message']}"
                        )

                        # 6. Registrar y enviar notificación.
                        sent = notify_new_alert(
                            alert_id,
                            validated_domain,
                            change
                        )

                        if sent:
                            emails_sent += 1

            print(f"Alertas nuevas: {alerts_created}")
            print(
                f"Correos aceptados por SMTP: "
                f"{emails_sent}"
            )

            results.append({
                "domain": validated_domain,
                "success": True,
                "analysis_id": analysis_id,
                "alerts_created": alerts_created,
                "emails_sent": emails_sent
            })

        except Exception as error:
            print(
                f"Error analizando {domain}: {error}"
            )

            results.append({
                "domain": domain,
                "success": False,
                "error": str(error)
            })

    successful = sum(
        1 for result in results
        if result["success"]
    )

    total_alerts = sum(
        result.get("alerts_created", 0)
        for result in results
    )

    total_emails = sum(
        result.get("emails_sent", 0)
        for result in results
    )

    print("\n=== MONITORIZACIÓN FINALIZADA ===")
    print(f"Dominios procesados: {len(results)}")
    print(f"Análisis guardados: {successful}")
    print(f"Errores: {len(results) - successful}")
    print(f"Alertas nuevas: {total_alerts}")
    print(
        f"Correos aceptados por SMTP: {total_emails}"
    )

    return results


if __name__ == "__main__":
    monitor_domains()
