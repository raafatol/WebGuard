
import re


ALLOWED_DOMAINS = {
    "www.google.com",
    "example.com"
}


def validate_domain(domain):
    domain = domain.strip().lower()

    pattern = (
        r"^(?!-)[a-z0-9-]{1,63}(?<!-)"
        r"(\.(?!-)[a-z0-9-]{1,63}(?<!-))+$"
    )

    if not re.fullmatch(pattern, domain):
        raise ValueError("Formato de dominio no válido")

    if domain not in ALLOWED_DOMAINS:
        raise ValueError("Dominio no autorizado para la demo")

    return domain
