import socket
import ssl
from datetime import datetime, timezone


def _distinguished_name(parts):
    return ", ".join(f"{key}={value}" for rdn in parts for key, value in rdn)


def check_tls(domain):
    """Comprueba TLS con verificación de certificado y SNI.

    version/cipher describen esta conexión, no todas las capacidades del servidor.
    """
    context = ssl.create_default_context()
    try:
        with socket.create_connection((domain, 443), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as secure_sock:
                certificate = secure_sock.getpeercert()
                expiry = certificate["notAfter"]
                expiry_date = datetime.fromtimestamp(
                    ssl.cert_time_to_seconds(expiry), tz=timezone.utc
                )
                days_left = (expiry_date - datetime.now(timezone.utc)).days
                cipher_info = secure_sock.cipher()
                result = {
                    "domain": domain,
                    "valid": True,
                    "expiry_date": expiry_date.isoformat(),
                    "days_left": days_left,
                    "status": "warning" if days_left <= 14 else "ok",
                    "issuer": _distinguished_name(certificate.get("issuer", ())) or None,
                    "tls_version": secure_sock.version(),
                    "cipher": cipher_info[0] if cipher_info else None,
                    "signature_algorithm": None,
                }
                # Opcional: extraer el algoritmo de firma si cryptography está instalada.
                try:
                    from cryptography import x509
                    parsed = x509.load_der_x509_certificate(secure_sock.getpeercert(binary_form=True))
                    oid = parsed.signature_algorithm_oid
                    result["signature_algorithm"] = getattr(oid, "_name", None) or oid.dotted_string
                except (ImportError, ValueError, TypeError, AttributeError):
                    pass
                return result
    except ssl.SSLCertVerificationError as error:
        return {"domain": domain, "valid": False, "status": "error", "error": str(error)}
    except (OSError, ssl.SSLError, KeyError, ValueError) as error:
        return {"domain": domain, "valid": None, "status": "unchecked", "error": str(error)}
