
from pprint import pprint

from app.database.db import init_db
from app.database.analysis_repository import (
    save_analysis,
    get_analysis_history
)

init_db()

# Resultado ficticio para probar la base de datos
test_result = {
    "domain": "www.google.com",

    "tls": {
        "valid": True,
        "days_left": 56,
        "status": "ok"
    },

    "http": {
        "http_status": 200,
        "present_count": 1,
        "total_headers": 6,

        "headers": {
            "HSTS": {
                "present": False,
                "value": None
            },
            "X-Frame-Options": {
                "present": True,
                "value": "SAMEORIGIN"
            }
        }
    }
}


print("\n=== GUARDANDO ANÁLISIS ===")

analysis_id = save_analysis(test_result)

print(f"Análisis guardado con ID: {analysis_id}")


print("\n=== CONSULTANDO HISTORIAL ===")

history = get_analysis_history("www.google.com")

pprint(history)
