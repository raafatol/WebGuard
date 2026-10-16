
from app.services.headers_checker import check_headers

domain = "www.google.com"

result = check_headers(domain)

print(f"Dominio: {result['domain']}")

if result.get("status") == "error":
    print(f"Error: {result['error']}")
else:
    print(f"Estado HTTP: {result['http_status']}")
    print(
        f"Cabeceras detectadas: "
        f"{result['present_count']}/{result['total_headers']}"
    )

    for name, info in result["headers"].items():
        if info["present"]:
            print(f"[OK] {name}")
        else:
            print(f"[--] {name}")
