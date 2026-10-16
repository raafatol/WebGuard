
import logging

from apscheduler.schedulers.blocking import BlockingScheduler

from app.services.monitor import monitor_domains
from app.services.notification_retry import retry_notifications
from app.database.email_repository import (
    recover_stale_notifications
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger("webguard")


def run_monitoring():
    """
    Ejecuta una ronda completa de WebGuard:

    1. Analiza los dominios.
    2. Detecta reservas de correo abandonadas.
    3. Procesa notificaciones pendientes.
    """

    logger.info("Iniciando ciclo de WebGuard.")

    # 1. Monitorizar los dominios.
    try:
        monitor_domains()

    except Exception:
        logger.exception(
            "Error inesperado en la monitorización."
        )

    # 2. Detectar notificaciones abandonadas.
    try:
        recovered = recover_stale_notifications(
            timeout_minutes=10
        )

        if recovered > 0:
            logger.warning(
                "%s notificaciones requieren revisión manual.",
                recovered
            )

    except Exception:
        logger.exception(
            "Error recuperando reservas abandonadas."
        )

    # 3. Reintentar notificaciones.
    try:
        retry_notifications()

    except Exception:
        logger.exception(
            "Error procesando notificaciones pendientes."
        )

    logger.info("Ciclo de WebGuard finalizado.")


def start_scheduler():
    """
    Programa la ejecución periódica de WebGuard.
    """

    scheduler = BlockingScheduler(
        timezone="UTC"
    )

    scheduler.add_job(
        run_monitoring,
        trigger="interval",
        minutes=5,
        id="webguard_monitor",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=60
    )

    logger.info(
        "WebGuard Scheduler iniciado. "
        "Monitorización y notificaciones cada 5 minutos."
    )

    try:
        scheduler.start()

    except (KeyboardInterrupt, SystemExit):
        logger.info("WebGuard Scheduler detenido.")


if __name__ == "__main__":
    start_scheduler()
