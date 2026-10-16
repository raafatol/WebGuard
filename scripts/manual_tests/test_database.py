
from pprint import pprint

from app.database.db import init_db
from app.database.domain_repository import (
    add_domain,
    get_domains,
    delete_domain
)

init_db()

print("\n=== AÑADIR DOMINIO ===")

try:
    result = add_domain("www.google.com")
    pprint(result)
except ValueError as error:
    print(error)

print("\n=== DOMINIOS GUARDADOS ===")
pprint(get_domains())

print("\n=== ELIMINAR DOMINIO ===")

domains = get_domains()

if domains:
    domain_id = domains[0]["id"]

    if delete_domain(domain_id):
        print(f"Dominio {domain_id} eliminado correctamente")

print("\n=== DOMINIOS RESTANTES ===")
pprint(get_domains())
