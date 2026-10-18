from io import BytesIO

from pypdf import PdfReader

from app.services import report_generator


def test_generar_informe_cliente_sin_dominios(monkeypatch):

    monkeypatch.setattr(
        report_generator,
        "get_client_by_id",
        lambda client_id: {
            "id": client_id,
            "name": "Cliente de prueba",
            "email": "prueba@example.com",
        },
    )

    monkeypatch.setattr(
        report_generator,
        "get_domains_by_client",
        lambda client_id: [],
    )

    pdf = report_generator.generate_client_report(1)

    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF-")

    reader = PdfReader(BytesIO(pdf))
    text = "\n".join(page.extract_text() for page in reader.pages)

    assert "WEBGUARD" in text
    assert "Cliente de prueba" in text
    assert "no tiene dominios registrados" in text


def test_generar_informe_cliente_inexistente(monkeypatch):

    monkeypatch.setattr(
        report_generator,
        "get_client_by_id",
        lambda client_id: None,
    )

    try:
        report_generator.generate_client_report(999)
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Debe producirse ValueError si el cliente no existe"
        )
