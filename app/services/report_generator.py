
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    PageBreak,
)

from app.database.client_repository import get_client_by_id
from app.database.domain_repository import get_domains_by_client
from app.database.analysis_repository import get_analysis_history
from app.services.recommendations import HEADER_INFO
from datetime import datetime, timezone

def safe_text(value):
    """Escapa texto para insertarlo de forma segura en el PDF."""
    return escape(str(value)) if value is not None else "No disponible"


def generate_client_report(client_id):
    """
    Genera un informe PDF de seguridad para un cliente.

    Devuelve los bytes del PDF, sin guardarlo en disco.
    Lanza ValueError si el cliente no existe.
    """

    client = get_client_by_id(client_id)

    if client is None:
        raise ValueError("El cliente indicado no existe")

    domains = get_domains_by_client(client_id)

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=(21 * cm, 29.7 * cm),
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=f"Informe de seguridad - {client['name']}",
    )

    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="WebGuardTitle",
        parent=styles["Title"],
        fontSize=22,
        leading=28,
        textColor=colors.HexColor("#0B1120"),
        alignment=TA_CENTER,
        spaceAfter=16,
    ))

    styles.add(ParagraphStyle(
        name="WebGuardSection",
        parent=styles["Heading2"],
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#0F766E"),
        spaceBefore=16,
        spaceAfter=9,
    ))

    story = []

    story.append(Paragraph(
        "WEBGUARD",
        styles["WebGuardTitle"]
    ))

    story.append(Paragraph(
        "Informe de seguridad web",
        styles["Heading1"]
    ))

    story.append(Spacer(1, 0.5 * cm))

    generation_date = datetime.now(timezone.utc).strftime(
    "%d/%m/%Y %H:%M UTC"
)

    story.append(Paragraph(
        f"<b>Fecha de generación:</b> {generation_date}",
        styles["Normal"]
    ))

    story.append(Spacer(1, 0.3 * cm))
    
    story.append(Paragraph(
        f"<b>Cliente:</b> {safe_text(client['name'])}",
        styles["Normal"]
    ))

    story.append(Paragraph(
        f"<b>Correo:</b> {safe_text(client['email'])}",
        styles["Normal"]
    ))

    story.append(Paragraph(
        f"<b>Dominios registrados:</b> {len(domains)}",
        styles["Normal"]
    ))

    story.append(Spacer(1, 0.7 * cm))

    story.append(Spacer(1, 2 * cm))

    story.append(Paragraph(
        "DOCUMENTO CONFIDENCIAL",
        styles["WebGuardSection"]
    ))

    story.append(Paragraph(
        "Este informe contiene información sobre el estado "
        "de seguridad de los dominios monitorizados. "
        "Está destinado al cliente indicado y debe "
        "tratarse de forma confidencial.",
        styles["Normal"]
    ))

    story.append(PageBreak())

    story.append(Paragraph(
        "Resumen ejecutivo",
        styles["WebGuardSection"]
    ))

    if not domains:
        story.append(Paragraph(
            "Este cliente todavía no tiene dominios registrados.",
            styles["Normal"]
        ))

    else:
        story.append(Paragraph(
            "Este informe recoge los últimos resultados de "
            "monitorización disponibles para los dominios "
            "asociados al cliente. No constituye una auditoría "
            "de seguridad exhaustiva.",
            styles["Normal"]
        ))

    for domain_record in domains:
        domain = domain_record["domain"]
        history = get_analysis_history(domain)
        analysis = history[0] if history else None

        story.append(Paragraph(
            f"Dominio: {safe_text(domain)}",
            styles["WebGuardSection"]
        ))

        if analysis is None:
            story.append(Paragraph(
                "Todavía no hay análisis disponibles para este dominio.",
                styles["Normal"]
            ))
            continue

        tls_valid = analysis["tls_valid"]

        if tls_valid is True:
            tls_status = "Válido"
        elif tls_valid is False:
            tls_status = "No válido"
        else:
            tls_status = "No determinado"

        metrics = [
            ["Indicador", "Resultado"],
            ["Fecha del análisis", safe_text(analysis["analyzed_at"])],
            ["Certificado TLS", tls_status],
            ["Días restantes TLS", safe_text(analysis["tls_days_left"])],
            ["Estado HTTP", safe_text(analysis["http_status"])],
            [
                "Cabeceras detectadas",
                f"{analysis['headers_present'] or 0} / "
                f"{analysis['headers_total'] or 0}"
            ],
        ]

        table = Table(metrics, colWidths=[7 * cm, 9 * cm])

        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0),
             colors.HexColor("#131D2E")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#F1F5F9")]),
            ("GRID", (0, 0), (-1, -1),
             0.4, colors.HexColor("#CBD5E1")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
        ]))

        story.append(table)
        story.append(Spacer(1, 0.4 * cm))

        
        headers = analysis.get("headers", {})

        story.append(Paragraph(
            "Cabeceras de seguridad HTTP",
            styles["WebGuardSection"]
        ))

        # Si no tenemos respuesta HTTP, no podemos afirmar
        # que una cabecera esté presente o ausente.
        http_checked = analysis.get("http_status") is not None

        for header_name, header_info in HEADER_INFO.items():

            header_data = headers.get(header_name)

            if not http_checked:
                status = "No comprobada"
                recommendation = None

            elif not isinstance(header_data, dict):
                status = "No comprobada"
                recommendation = None

            elif header_data.get("present") is True:
                status = "Detectada"
                recommendation = None

            elif header_data.get("present") is False:
                status = "No detectada"
                recommendation = header_info["recommendation"]

            else:
                status = "No comprobada"
                recommendation = None

            header_content = [
                Paragraph(
                    f"<b>{safe_text(header_name)}</b> "
                    f"— {safe_text(header_info['title'])}",
                    styles["Heading3"]
                ),
                Paragraph(
                    f"<b>Estado:</b> {safe_text(status)}",
                    styles["Normal"]
                ),
                Paragraph(
                    safe_text(header_info["description"]),
                    styles["Normal"]
                ),
            ]

            if recommendation:
                header_content.append(Spacer(1, 0.12 * cm))
                header_content.append(Paragraph(
                    f"<b>Recomendación:</b> "
                    f"{safe_text(recommendation)}",
                    styles["Normal"]
                ))

            header_content.append(Spacer(1, 0.3 * cm))

            story.append(KeepTogether(header_content))

        story.append(Spacer(1, 0.4 * cm))


    document.build(story)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes
