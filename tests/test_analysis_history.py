
import pytest

from app.database import db
from app.database.analysis_repository import (
    save_analysis,
    get_analysis_history,
    get_latest_analysis,
    get_last_two_analyses,
)


@pytest.fixture
def base_de_datos_temporal(tmp_path, monkeypatch):
    ruta_temporal = tmp_path / "webguard_test.db"
    monkeypatch.setattr(db, "DB_PATH", ruta_temporal)
    db.init_db()


def crear_resultado(
    domain="example.com",
    tls_valid=True,
    days_left=30,
    http_status=200,
):
    return {
        "domain": domain,
        "tls": {
            "valid": tls_valid,
            "days_left": days_left,
            "status": "ok",
        },
        "http": {
            "http_status": http_status,
            "present_count": 1,
            "total_headers": 2,
            "headers": {
                "HSTS": {
                    "present": True,
                    "value": "max-age=31536000",
                },
                "X-Frame-Options": {
                    "present": False,
                    "value": None,
                },
            },
        },
    }


def test_guardar_analisis(base_de_datos_temporal):
    resultado = crear_resultado()

    analysis_id = save_analysis(resultado)

    assert isinstance(analysis_id, int)
    assert analysis_id > 0


def test_recuperar_historial(base_de_datos_temporal):
    save_analysis(crear_resultado())

    historial = get_analysis_history("example.com")

    assert len(historial) == 1
    assert historial[0]["domain"] == "example.com"
    assert historial[0]["tls_valid"] is True
    assert historial[0]["tls_days_left"] == 30
    assert historial[0]["http_status"] == 200


def test_recuperar_cabeceras_http(base_de_datos_temporal):
    save_analysis(crear_resultado())

    historial = get_analysis_history("example.com")

    cabeceras = historial[0]["headers"]

    assert cabeceras["HSTS"]["present"] is True
    assert cabeceras["X-Frame-Options"]["present"] is False


def test_historial_vacio(base_de_datos_temporal):
    historial = get_analysis_history("example.com")

    assert historial == []


def test_historial_separado_por_dominio(base_de_datos_temporal):
    save_analysis(crear_resultado(domain="example.com"))
    save_analysis(crear_resultado(domain="www.google.com"))

    historial = get_analysis_history("example.com")

    assert len(historial) == 1
    assert historial[0]["domain"] == "example.com"


def test_obtener_ultimo_analisis(base_de_datos_temporal):
    save_analysis(crear_resultado(days_left=30))
    segundo_id = save_analysis(crear_resultado(days_left=15))

    ultimo = get_latest_analysis("example.com")

    assert ultimo["id"] == segundo_id
    assert ultimo["tls_days_left"] == 15


def test_ultimo_analisis_inexistente(base_de_datos_temporal):
    ultimo = get_latest_analysis("example.com")

    assert ultimo is None


def test_obtener_dos_ultimos_analisis(base_de_datos_temporal):
    save_analysis(crear_resultado(days_left=30))
    segundo_id = save_analysis(crear_resultado(days_left=20))
    tercer_id = save_analysis(crear_resultado(days_left=10))

    ultimos = get_last_two_analyses("example.com")

    assert len(ultimos) == 2
    assert ultimos[0]["id"] == tercer_id
    assert ultimos[1]["id"] == segundo_id


def test_tls_invalido(base_de_datos_temporal):
    save_analysis(crear_resultado(tls_valid=False))

    ultimo = get_latest_analysis("example.com")

    assert ultimo["tls_valid"] is False


def test_limite_historial_50(base_de_datos_temporal):
    for i in range(55):
        save_analysis(crear_resultado(days_left=i))

    historial = get_analysis_history("example.com")

    assert len(historial) == 50
    assert historial[0]["tls_days_left"] == 54
    assert historial[-1]["tls_days_left"] == 5
