
import smtplib
from email.message import EmailMessage


def build_alert_email(alert):
    """
    Construye un correo a partir de una alerta
    de seguridad de WebGuard.
    """

    domain = alert["domain"]
    message = alert["message"]
    severity = alert["severity"]

    if severity == "warning":
        severity_text = "Advertencia"
    else:
        severity_text = "Información"

    subject = (
        f"[WebGuard] Cambio de seguridad detectado "
        f"en {domain}"
    )

    body = f"""
Hola,

WebGuard ha detectado un cambio en la configuración
de seguridad de uno de tus dominios monitorizados.

Dominio: {domain}

Nivel: {severity_text}

Detalle:
{message}

Te recomendamos revisar la configuración de
seguridad del sitio web.

---
WebGuard
Website Security Monitoring
""".strip()

    email = EmailMessage()
    email["Subject"] = subject
    email.set_content(body)

    return email


def send_alert_email(alert, recipient):
    """
    Envía una alerta al servidor SMTP local.

    Por ahora solo funciona en modo de pruebas.
    No envía correos a Internet.
    """

    email = build_alert_email(alert)

    email["From"] = "alerts@webguard.local"
    email["To"] = recipient

    with smtplib.SMTP(
        host="127.0.0.1",
        port=1025,
        timeout=10
    ) as smtp:
        smtp.send_message(email)

    return True
