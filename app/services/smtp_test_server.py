
import asyncio

from aiosmtpd.controller import Controller


class TestEmailHandler:

    async def handle_DATA(self, server, session, envelope):
        print("\n" + "=" * 60)
        print("WEBGUARD - CORREO RECIBIDO")
        print("=" * 60)

        print(f"Remitente: {envelope.mail_from}")
        print(f"Destinatarios: {envelope.rcpt_tos}")

        print("\nCONTENIDO DEL CORREO:\n")

        content = envelope.content.decode(
            "utf-8",
            errors="replace"
        )

        print(content)
        print("=" * 60 + "\n")

        return "250 Message accepted for testing"


async def main():
    controller = Controller(
        TestEmailHandler(),
        hostname="127.0.0.1",
        port=1025
    )

    controller.start()

    print("Servidor SMTP de pruebas iniciado.")
    print("Dirección: 127.0.0.1")
    print("Puerto: 1025")
    print("Esperando correos de WebGuard...")
    print("Pulsa Ctrl+C para detenerlo.\n")

    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        controller.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServidor SMTP detenido.")
