
HEADER_INFO = {
    "HSTS": {
        "title": "HTTP Strict Transport Security",
        "description": (
            "Indica al navegador que debe utilizar HTTPS "
            "en futuras conexiones con el sitio."
        ),
        "recommendation": (
            "Revisar si HSTS está configurado. "
            "Valorar su activación después de comprobar "
            "que HTTPS funciona correctamente."
        )
    },

    "CSP": {
        "title": "Content Security Policy",
        "description": (
            "Permite restringir los recursos que una "
            "página web puede cargar y ejecutar."
        ),
        "recommendation": (
            "Definir una política CSP adaptada a la web. "
            "Probarla inicialmente en modo Report-Only."
        )
    },

    "X-Frame-Options": {
        "title": "Protección contra clickjacking",
        "description": (
            "Controla si la página puede mostrarse "
            "dentro de un iframe."
        ),
        "recommendation": (
            "Utilizar DENY o SAMEORIGIN cuando corresponda. "
            "También puede utilizarse CSP frame-ancestors."
        )
    },

    "X-Content-Type-Options": {
        "title": "Protección de tipos MIME",
        "description": (
            "Evita determinadas interpretaciones "
            "incorrectas de los tipos de contenido."
        ),
        "recommendation": (
            "Configurar X-Content-Type-Options: nosniff."
        )
    },

    "Referrer-Policy": {
        "title": "Política de información de origen",
        "description": (
            "Controla qué información sobre la página "
            "de origen se envía al navegar."
        ),
        "recommendation": (
            "Revisar la política actual. "
            "strict-origin-when-cross-origin puede "
            "ser una opción adecuada."
        )
    },

    "Permissions-Policy": {
        "title": "Política de permisos del navegador",
        "description": (
            "Permite restringir determinadas funciones "
            "del navegador, como cámara o micrófono."
        ),
        "recommendation": (
            "Deshabilitar las funciones que la "
            "aplicación no necesite."
        )
    }
}



def generate_recommendations(headers_result):
    recommendations = []

    # Comprobamos si el análisis HTTP se ha completado.
    analysis_successful = (
        headers_result.get("status") == "success"
    )

    for name, info in headers_result.get("headers", {}).items():

        if name not in HEADER_INFO:
            continue

        details = HEADER_INFO[name]

        # Si no hubo respuesta HTTP, no podemos afirmar
        # que una cabecera esté presente o ausente.
        if not analysis_successful:
            detected = None
            status = "unknown"

        elif info.get("present") is True:
            detected = True
            status = "present"

        elif info.get("present") is False:
            detected = False
            status = "missing"

        else:
            detected = None
            status = "unknown"

        recommendations.append({
            "header": name,
            "title": details["title"],
            "description": details["description"],
            "detected": detected,
            "status": status,
            "recommendation": (
                details["recommendation"]
                if status == "missing"
                else None
            )
        })

    return recommendations
