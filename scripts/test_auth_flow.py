import getpass
import requests

BASE_URL = "http://127.0.0.1:8000"

email = input("Correo de administrador: ")
password = getpass.getpass("Contraseña: ")

with requests.Session() as session:

    # 1. Iniciar sesión.
    response = session.post(
        f"{BASE_URL}/auth/login",
        json={
            "email": email,
            "password": password,
        },
        timeout=15,
    )

    print("\n1. LOGIN:", response.status_code)

    if response.status_code != 200:
        print(response.text)
        raise SystemExit(1)

    # 2. Acceder a clientes con la sesión activa.
    response = session.get(
        f"{BASE_URL}/clients",
        timeout=15,
    )

    print("2. CLIENTES CON SESIÓN:", response.status_code)

    # Obtener el token CSRF de la sesión.
    response = session.get(
        f"{BASE_URL}/auth/csrf",
        timeout=15,
    )

    response.raise_for_status()
    csrf_token = response.json()["csrf_token"]

    # 3. Cerrar sesión con token y origen legítimos.
    response = session.post(
        f"{BASE_URL}/auth/logout",
        headers={
            "Origin": BASE_URL,
            "X-CSRF-Token": csrf_token,
        },
        timeout=15,
    )

    print("3. LOGOUT:", response.status_code)

    # 4. Comprobar que la sesión ha quedado invalidada.
    response = session.get(
        f"{BASE_URL}/clients",
        timeout=15,
    )

    print("4. CLIENTES SIN SESIÓN:", response.status_code)
