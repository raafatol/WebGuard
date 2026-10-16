
import httpx


SECURITY_HEADERS = {
    "strict-transport-security": "HSTS",
    "content-security-policy": "CSP",
    "x-frame-options": "X-Frame-Options",
    "x-content-type-options": "X-Content-Type-Options",
    "referrer-policy": "Referrer-Policy",
    "permissions-policy": "Permissions-Policy"
}


def check_headers(domain):
    """
    Comprueba las cabeceras de seguridad HTTP.

    Distingue entre:
    - Comprobación completada.
    - Error de conexión o respuesta.
    """

    url = f"https://{domain}"

    try:
        with httpx.Client(
            timeout=5,
            follow_redirects=False,
            trust_env=False
        ) as client:

            response = client.get(url)

            results = {}

            for header, name in SECURITY_HEADERS.items():
                value = response.headers.get(header)

                results[name] = {
                    "present": value is not None,
                    "value": value
                }

            present = sum(
                item["present"]
                for item in results.values()
            )

            return {
                "domain": domain,
                "status": "success",
                "http_status": response.status_code,
                "headers": results,
                "present_count": present,
                "total_headers": len(SECURITY_HEADERS),
                "error": None
            }

    except httpx.HTTPError as error:

        # No se ha podido obtener una respuesta HTTP.
        # No debemos interpretar las cabeceras como ausentes.

        results = {}

        for name in SECURITY_HEADERS.values():
            results[name] = {
                "present": None,
                "value": None
            }

        return {
            "domain": domain,
            "status": "error",
            "http_status": None,
            "headers": results,
            "present_count": None,
            "total_headers": len(SECURITY_HEADERS),
            "error": str(error)
        }
