
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.services.security_analyzer import analyze_website
from app.services.domain_validator import validate_domain

from app.database.db import init_db
from app.database.domain_repository import (
    add_domain,
    get_domains,
    delete_domain
)
from app.database.analysis_repository import (
    save_analysis,
    get_analysis_history,
    get_latest_analysis
)

from app.database.alert_repository import get_alerts


app = FastAPI(
    title="WebGuard API",
    description="Website Security Monitoring",
    version="0.4.0"
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static"
)

# Inicializar las tablas de SQLite
init_db()


class DomainCreate(BaseModel):
    domain: str


# =========================================
# PÁGINA PRINCIPAL
# =========================================

@app.get("/")
def home():
    return FileResponse(STATIC_DIR / "index.html")


# =========================================
# ANALIZADOR DE SEGURIDAD
# =========================================

@app.get("/analyze")
def analyze(domain: str):

    try:
        validated_domain = validate_domain(domain)

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    # Realizar el análisis
    result = analyze_website(validated_domain)

    # Guardar el resultado en SQLite
    analysis_id = save_analysis(result)

    # Incluir el ID del análisis en la respuesta
    result["analysis_id"] = analysis_id

    return result


# =========================================
# GESTIÓN DE DOMINIOS
# =========================================

@app.get("/domains")
def list_domains():
    return get_domains()


@app.post("/domains", status_code=201)
def create_domain(data: DomainCreate):

    try:
        return add_domain(data.domain)

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


@app.delete("/domains/{domain_id}")
def remove_domain(domain_id: int):

    deleted = delete_domain(domain_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Dominio no encontrado"
        )

    return {
        "message": "Dominio eliminado correctamente"
    }


# =========================================
# HISTORIAL DE ANÁLISIS
# =========================================

@app.get("/history")
def history(domain: str):

    try:
        validated_domain = validate_domain(domain)

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    return get_analysis_history(validated_domain)


# =========================================
# ESTADO ACTUAL DE LOS DOMINIOS
# =========================================

@app.get("/domains/status")
def get_domains_status():
    """
    Devuelve los dominios registrados
    junto con su análisis más reciente.
    """

    domains = get_domains()

    results = []

    for domain in domains:

        latest_analysis = get_latest_analysis(
            domain["domain"]
        )

        results.append({
            "id": domain["id"],
            "domain": domain["domain"],
            "created_at": domain["created_at"],
            "latest_analysis": latest_analysis
        })

    return results


@app.get("/alerts")
def list_alerts(domain: str | None = None):
    """
    Recupera las últimas alertas de seguridad.

    Si se proporciona un dominio, devuelve
    únicamente las alertas de ese dominio.
    """
    return get_alerts(domain)
