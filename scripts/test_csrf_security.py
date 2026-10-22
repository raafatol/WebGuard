import getpass
import requests

BASE_URL = "http://127.0.0.1:8000"

email = input("Correo de administrador: ")
password = getpass.getpass("Contraseña: ")

with requests.Session() as session:

    # Autenticación
    response = session.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": password},
        timeout=15,
    )

    print("\nLOGIN:", response.status_code)

    if response.status_code != 200:
        print("No se pudo iniciar sesión. Prueba más tarde si hay límite de intentos.")
        raise SystemExit(1)

    # Obtener token CSRF válido
    response = session.get(
        f"{BASE_URL}/auth/csrf",
        timeout=15,
    )
    response.raise_for_status()
    csrf_token = response.json()["csrf_token"]

    # Todas las pruebas utilizan logout, pero las peticiones
    # rechazadas NO deberían cerrar la sesión.
    tests = [
        (
            "Origen malicioso + token válido",
            {
                "Origin": "https://webguard-atacante.example",
                "X-CSRF-Token": csrf_token,
            },
            403,
        ),
        (
            "Origen legítimo + token falso",
            {
                "Origin": BASE_URL,
                "X-CSRF-Token": "token-falso",
            },
            403,
        ),
        (
            "Sin Origin ni Referer + token válido",
            {
                "X-CSRF-Token": csrf_token,
            },
            403,
        ),
    ]

    for name, headers, expected in tests:
        response = session.post(
            f"{BASE_URL}/auth/logout",
            headers=headers,
            timeout=15,
        )

        status = "PASS" if response.status_code == expected else "FAIL"
        print(f"{status} | {name}: {response.status_code} (esperado {expected})")

        # Verificar que las peticiones rechazadas no invalidaron la sesión
        check = session.get(f"{BASE_URL}/auth/me", timeout=15)
        print(f"       Sesión conservada: {check.status_code == 200}")

        if response.status_code != expected or check.status_code != 200:
            print("Prueba interrumpida: resultado inesperado.")
            raise SystemExit(1)

    # Finalmente, cerrar sesión legítimamente.
    response = session.post(
        f"{BASE_URL}/auth/logout",
        headers={
            "Origin": BASE_URL,
            "X-CSRF-Token": csrf_token,
        },
        timeout=15,
    )

    print(
        f"{'PASS' if response.status_code == 200 else 'FAIL'} "
        f"| Origen legítimo + token válido: {response.status_code} "
        "(esperado 200)"
    )

    check = session.get(f"{BASE_URL}/auth/me", timeout=15)
    print(
        f"{'PASS' if check.status_code == 401 else 'FAIL'} "
        f"| Sesión invalidada tras logout: {check.status_code} "
        "(esperado 401)"
    )
