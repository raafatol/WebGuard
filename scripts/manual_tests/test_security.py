
from pprint import pprint
from app.services.security_analyzer import analyze_website


domain = "www.google.com"

result = analyze_website(domain)

print("\n========== WEBGUARD ==========")
print(f"Dominio: {result['domain']}")

print("\n--- CERTIFICADO TLS ---")
pprint(result["tls"])

print("\n--- CABECERAS HTTP ---")
pprint(result["http"])

print("\n--- RECOMENDACIONES ---")
pprint(result["recommendations"])

print("\n==============================")
