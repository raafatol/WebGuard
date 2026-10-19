
import socket
import ssl
from datetime import datetime, timezone


def check_tls(domain):
    context = ssl.create_default_context()

    try:
        with socket.create_connection((domain, 443), timeout=5) as sock:
            with context.wrap_socket(
                sock,
                server_hostname=domain
            ) as secure_sock:

                certificate = secure_sock.getpeercert()

                expiry = certificate["notAfter"]

                expiry_date = datetime.fromtimestamp(
                    ssl.cert_time_to_seconds(expiry),
                    tz=timezone.utc
                )

                remaining = expiry_date - datetime.now(timezone.utc)
                days_left = remaining.days

                if days_left <= 14:
                    status = "warning"
                else:
                    status = "ok"

                return {
                    "domain": domain,
                    "valid": True,
                    "expiry_date": expiry_date.isoformat(),
                    "days_left": days_left,
                    "status": status
                }

    except ssl.SSLCertVerificationError as error:
        return {
            "domain": domain,
            "valid": False,
            "status": "error",
            "error": str(error)
        }

    except (OSError, ssl.SSLError) as error:
        return {
            "domain": domain,
            "valid": None,
            "status": "unchecked",
            "error": str(error)
        }
