
from pathlib import Path
from contextlib import asynccontextmanager
from io import BytesIO

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.services.security_analyzer import analyze_website
from app.services.domain_validator import validate_domain
from app.services.report_generator import generate_client_report

from app.database.db import init_db
from app.database.domain_repository import (
    add_domain,
    get_domains,
    get_domains_by_client,
    delete_domain
)
from app.database.analysis_repository import (
    save_analysis,
    get_analysis_history,
    get_latest_analysis
)

from app.database.alert_repository import get_alerts
from app.database.client_repository import (
    add_client,
    get_clients,
    get_client_by_id,
    update_client,
    delete_client
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Inicializa SQLite al arrancar WebGuard,
    no al importar el módulo.
    """
    init_db()
    yield

app = FastAPI(
    title="WebGuard API",
    description="Website Security Monitoring",
    version="0.4.0",
    lifespan=lifespan
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static"
)

class DomainCreate(BaseModel):
    domain: str
    client_id: int | None = None


class ClientCreate(BaseModel):
    name: str
    email: str | None = None


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
    """
    Registra un dominio y permite asociarlo
    opcionalmente a un cliente.
    """

    try:
        return add_domain(
            data.domain,
            data.client_id
        )

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
            "client_id": domain["client_id"],
            "client_name": domain["client_name"],
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


# =========================================
# GESTIÓN DE CLIENTES - WEBGUARD v0.8
# =========================================

@app.get("/clients")
def list_clients():
    """
    Devuelve todos los clientes registrados
    en WebGuard.
    """
    return get_clients()


@app.post("/clients", status_code=201)
def create_client(data: ClientCreate):
    """
    Registra un nuevo cliente en WebGuard.
    """

    try:
        return add_client(data.name, data.email)

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


@app.get("/clients/{client_id}")
def get_client(client_id: int):
    """
    Recupera un cliente mediante su identificador.
    """

    client = get_client_by_id(client_id)

    if client is None:
        raise HTTPException(
            status_code=404,
            detail="Cliente no encontrado"
        )

    return client


@app.put("/clients/{client_id}")
def edit_client(client_id: int, data: ClientCreate):
    """
    Actualiza el nombre y el correo
    electrónico de un cliente.
    """

    try:
        updated_client = update_client(
            client_id,
            data.name,
            data.email
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    if updated_client is None:
        raise HTTPException(
            status_code=404,
            detail="Cliente no encontrado"
        )

    return updated_client


@app.delete("/clients/{client_id}")
def remove_client(client_id: int):
    """
    Elimina un cliente si no tiene
    dominios asociados.
    """

    try:
        deleted = delete_client(client_id)

    except ValueError as error:
        raise HTTPException(
            status_code=409,
            detail=str(error)
        )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Cliente no encontrado"
        )

    return {
        "message": "Cliente eliminado correctamente"
    }


@app.get("/clients/{client_id}/domains")
def list_client_domains(client_id: int):
    """
    Devuelve los dominios asociados
    a un cliente concreto.
    """

    client = get_client_by_id(client_id)

    if client is None:
        raise HTTPException(
            status_code=404,
            detail="Cliente no encontrado"
        )

    return get_domains_by_client(client_id)

# =========================================
# INFORMES PDF
# =========================================

@app.get("/reports/clients/{client_id}/pdf")
def download_client_report(client_id: int):
    """
    Genera y descarga un informe PDF con los últimos
    análisis de los dominios asociados a un cliente.
    """

    try:
        pdf_bytes = generate_client_report(client_id)

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error)
        )

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition":
                f'attachment; filename="webguard-informe-cliente-{client_id}.pdf"'
        }
    )