
def detect_changes(previous, current):
    """
    Compara dos análisis de seguridad.

    Detecta:
    - Cabeceras que han desaparecido.
    - Cabeceras que han aparecido.

    No compara cabeceras cuyo estado sea desconocido.
    """

    changes = []

    previous_headers = previous.get("headers", {})
    current_headers = current.get("headers", {})

    # Si no tenemos una respuesta HTTP válida en ambos
    # análisis, no podemos comparar las cabeceras.
    if (
        previous.get("http_status") is None
        or current.get("http_status") is None
    ):
        return changes

    for header, current_info in current_headers.items():

        previous_info = previous_headers.get(header)

        if previous_info is None:
            continue

        previous_present = previous_info.get("present")
        current_present = current_info.get("present")

        # Solo comparamos estados booleanos conocidos.
        if (
            not isinstance(previous_present, bool)
            or not isinstance(current_present, bool)
        ):
            continue

        if previous_present and not current_present:
            changes.append({
                "type": "header_removed",
                "header": header,
                "severity": "warning",
                "message": (
                    f"La cabecera {header} estaba presente "
                    f"y ha dejado de detectarse."
                )
            })

        elif not previous_present and current_present:
            changes.append({
                "type": "header_added",
                "header": header,
                "severity": "info",
                "message": (
                    f"La cabecera {header} no estaba presente "
                    f"y ahora se ha detectado."
                )
            })

    return changes

# Solo estos estados permiten concluir si el servidor terminó en HTTPS.
_REDIRECT_SECURE = 'redirects_to_https'
_REDIRECT_INSECURE = {'no_redirect', 'ends_on_http'}


def detect_redirect_changes(previous, current):
    """Detecta pérdidas y recuperaciones confirmadas de redirección HTTPS.

    Los resultados no concluyentes (errores, bucles, destinos externos,
    registros antiguos sin medición) no se consideran fallos confirmados.
    """
    old = previous.get('redirect')
    new = current.get('redirect')
    if not isinstance(old, dict) or not isinstance(new, dict):
        return []
    before, after = old.get('status'), new.get('status')
    if before == _REDIRECT_SECURE and after in _REDIRECT_INSECURE:
        return [{
            'type': 'redirect_https_lost',
            'severity': 'warning',
            'message': ('La redirección HTTP → HTTPS antes verificada ha dejado '
                        'de funcionar. Estado actual: ' + after + '.'),
        }]
    if before in _REDIRECT_INSECURE and after == _REDIRECT_SECURE:
        return [{
            'type': 'redirect_https_restored',
            'severity': 'info',
            'message': 'Se ha recuperado la redirección HTTP → HTTPS verificada.',
        }]
    return []
