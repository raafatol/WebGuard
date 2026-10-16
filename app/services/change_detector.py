
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
