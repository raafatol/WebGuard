
from io import BytesIO
from xml.sax.saxutils import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
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

# Ruta absoluta al logotipo original de WebGuard
WEBGUARD_LOGO = (
    Path(__file__).resolve().parent.parent
    / "static"
    / "assets"
    / "logos"
    / "webguard-icon-pdf.png"
)


def draw_report_cover(canvas, document, brand_name, brand_color, client_name):
    """Portada corporativa de WebGuard o de marca blanca."""

    canvas.saveState()

    width, height = A4
    white = colors.white
    muted = colors.HexColor("#A6B7D0")

    is_webguard = brand_name == "WEBGUARD"
    blue = colors.HexColor("#00BFFF" if is_webguard else brand_color)

    left = 65

    # =========================================
    # FONDO AZUL MARINO CON ILUMINACIÓN SUAVE
    # =========================================

    import math

    # Fondo base
    canvas.setFillColor(colors.HexColor("#041126"))
    canvas.rect(0, 0, width, height, fill=1, stroke=0)

    # Cuadrícula de pequeños rectángulos para simular
    # un degradado multidireccional suave.
    columns = 65
    rows = 95

    cell_w = width / columns
    cell_h = height / rows

    for row in range(rows):
        for col in range(columns):
            x = (col + 0.5) / columns
            y = (row + 0.5) / rows

            # Resplandor azul superior, amplio y suave
            top_glow = math.exp(
                -(
                    ((x - 0.62) / 0.75) ** 2
                    + ((y - 1.04) / 0.38) ** 2
                ) * 2
            )

            # Resplandor azul inferior derecho
            bottom_glow = math.exp(
                -(
                    ((x - 0.85) / 0.68) ** 2
                    + ((y + 0.12) / 0.42) ** 2
                ) * 2
            )

            # Iluminación ambiental
            ambient = 0.10

            intensity = min(
                1.0,
                ambient
                + 1.15 * top_glow
                + 0.95 * bottom_glow
            )

            red = (3 + 10 * intensity) / 255
            green = (11 + 49 * intensity) / 255
            blue_channel = (27 + 110 * intensity) / 255

            canvas.setFillColor(
                colors.Color(red, green, blue_channel)
            )

            canvas.rect(
                col * cell_w,
                row * cell_h,
                cell_w + 0.3,
                cell_h + 0.3,
                fill=1,
                stroke=0
            )

    # =========================================
    # IDENTIDAD CORPORATIVA
    # =========================================

    if is_webguard and WEBGUARD_LOGO.is_file():
        canvas.drawImage(
            ImageReader(str(WEBGUARD_LOGO)),
            left,
            height - 184,
            width=172,
            height=108,
            preserveAspectRatio=True,
            mask="auto"
        )

        brand_y = height - 205
        brand_font_size = 29

        canvas.setFont("Helvetica-Bold", brand_font_size)
        canvas.setFillColor(white)
        canvas.drawString(left, brand_y, "WEB")

        web_width = canvas.stringWidth(
            "WEB", "Helvetica-Bold", brand_font_size
        )

        canvas.setFillColor(blue)
        canvas.drawString(
            left + web_width,
            brand_y,
            "GUARD"
        )

    else:
        # Marca blanca: nombre de la empresa, sin WebGuard.
        company_display = str(brand_name)

        while (
            canvas.stringWidth(
                company_display, "Helvetica-Bold", 27
            ) > width - 2 * left
            and len(company_display) > 3
        ):
            company_display = company_display[:-4] + "..."

        canvas.setFillColor(white)
        canvas.setFont("Helvetica-Bold", 27)
        canvas.drawString(
            left,
            height - 205,
            company_display
        )

    # =========================================
    # TÍTULO PRINCIPAL
    # =========================================

    canvas.setFillColor(blue)
    canvas.rect(
        left,
        height - 267,
        65,
        5,
        fill=1,
        stroke=0
    )

    canvas.setFillColor(white)

    canvas.setFont("Helvetica", 31)
    canvas.drawString(
        left,
        height - 323,
        "INFORME DE"
    )

    canvas.setFont("Helvetica-Bold", 32)
    canvas.drawString(
        left,
        height - 358,
        "SEGURIDAD WEB"
    )

    canvas.setFillColor(muted)
    canvas.setFont("Helvetica", 12)
    canvas.drawString(
        left,
        height - 404,
        "Evaluación técnica de dominios y"
    )
    canvas.drawString(
        left,
        height - 421,
        "configuraciones de seguridad"
    )

    # =========================================
    # INFORMACIÓN DEL CLIENTE
    # =========================================

    canvas.setFillColor(blue)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(
        left,
        height - 493,
        "PREPARADO PARA"
    )

    client_display = str(client_name)

    while (
        canvas.stringWidth(
            client_display, "Helvetica-Bold", 20
        ) > width - 2 * left
        and len(client_display) > 3
    ):
        client_display = client_display[:-4] + "..."

    canvas.setFillColor(white)
    canvas.setFont("Helvetica-Bold", 20)
    canvas.drawString(
        left,
        height - 526,
        client_display
    )

    # =========================================
    # FECHA Y TIPO DE INFORME CON ICONOS
    # =========================================

    info_y = height - 600

    def draw_icon_box(x, y, icon_type):
        canvas.setFillColor(colors.HexColor("#102B4A"))
        canvas.roundRect(
            x, y - 7, 34, 34,
            7, fill=1, stroke=0
        )

        canvas.setStrokeColor(blue)
        canvas.setLineWidth(1.5)

        if icon_type == "calendar":
            canvas.roundRect(
                x + 9, y + 2, 17, 15,
                2, fill=0, stroke=1
            )
            canvas.line(x + 9, y + 12, x + 26, y + 12)
            canvas.line(x + 14, y + 15, x + 14, y + 20)
            canvas.line(x + 21, y + 15, x + 21, y + 20)

        elif icon_type == "document":
            path = canvas.beginPath()
            path.moveTo(x + 11, y + 1)
            path.lineTo(x + 23, y + 1)
            path.lineTo(x + 23, y + 19)
            path.lineTo(x + 11, y + 19)
            path.close()
            canvas.drawPath(path, fill=0, stroke=1)
            canvas.line(x + 14, y + 12, x + 20, y + 12)
            canvas.line(x + 14, y + 8, x + 20, y + 8)

    draw_icon_box(left, info_y, "calendar")
    draw_icon_box(275, info_y, "document")

    canvas.setFillColor(muted)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(
        left + 45,
        info_y + 17,
        "FECHA DE EMISIÓN"
    )
    canvas.drawString(
        320,
        info_y + 17,
        "TIPO DE INFORME"
    )

    date_text = datetime.now(timezone.utc).strftime("%d/%m/%Y")

    canvas.setFillColor(white)
    canvas.setFont("Helvetica", 11)
    canvas.drawString(
        left + 45,
        info_y - 1,
        date_text
    )

    canvas.setFont("Helvetica", 10)
    canvas.drawString(
        320,
        info_y - 1,
        "Informe técnico de seguridad"
    )

    # =========================================
    # PIE DE CONFIDENCIALIDAD
    # =========================================

    canvas.setStrokeColor(colors.HexColor("#405875"))
    canvas.setLineWidth(0.7)
    canvas.line(left, 125, width - left, 125)

    canvas.setFillColor(colors.HexColor("#CBD5E1"))
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(
        left,
        99,
        "DOCUMENTO CONFIDENCIAL"
    )

    canvas.setFillColor(muted)
    canvas.setFont("Helvetica", 9)
    canvas.drawString(
        left,
        80,
        "Este informe contiene información técnica destinada"
    )
    canvas.drawString(
        left,
        66,
        "exclusivamente al cliente indicado."
    )

    canvas.restoreState()


def create_metric_card(label, value, accent_color):
    """
    Crea una tarjeta con un indicador del resumen ejecutivo.
    """

    card = Table(
        [
            [
                Paragraph(
                    safe_text(label),
                    ParagraphStyle(
                        name="MetricLabel",
                        fontName="Helvetica",
                        fontSize=9,
                        leading=13,
                        textColor=colors.HexColor("#64748B"),
                    )
                )
            ],
            [
                Paragraph(
                    str(value),
                    ParagraphStyle(
                        name="MetricValue",
                        fontName="Helvetica-Bold",
                        fontSize=24,
                        leading=30,
                        textColor=colors.HexColor(accent_color),
                    )
                )
            ],
        ],
        colWidths=[7.4 * cm],
    )

    card.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, 0), 12),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
        ("TOPPADDING", (0, 1), (-1, 1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 12),
    ]))

    return card

def draw_report_footer(canvas, document, brand_name, brand_color):
    """Dibuja el pie corporativo en las páginas interiores."""

    canvas.saveState()

    page_width, _ = document.pagesize

    canvas.setStrokeColor(colors.HexColor("#CBD5E1"))
    canvas.setLineWidth(0.6)
    canvas.line(55, 48, page_width - 55, 48)

    canvas.setFillColor(colors.HexColor(brand_color))
    canvas.setFont("Helvetica-Bold", 8)

    footer_brand = str(brand_name).upper()
    while (
        canvas.stringWidth(
            footer_brand, "Helvetica-Bold", 8
        ) > 180
        and len(footer_brand) > 3
    ):
        footer_brand = footer_brand[:-4] + "..."

    canvas.drawString(55, 34, footer_brand)

    canvas.setFillColor(colors.HexColor("#64748B"))
    canvas.setFont("Helvetica", 8)

    page_text = f"Página {document.page}"

    canvas.drawRightString(
        page_width - 55,
        34,
        page_text
    )

    canvas.restoreState()

def generate_client_report(
    client_id,
    branding="webguard",
    company_name=None,
    primary_color=None,
    logo_path=None
):
    """
    Genera un informe PDF de seguridad para un cliente.

    Devuelve los bytes del PDF, sin guardarlo en disco.
    Lanza ValueError si el cliente no existe.
    """

    client = get_client_by_id(client_id)

    if client is None:
        raise ValueError("El cliente indicado no existe")

    # =========================================
    # CONFIGURACIÓN DE IDENTIDAD VISUAL
    # =========================================

    if branding not in ("webguard", "white_label"):
        raise ValueError("Modalidad de informe no válida")

    if branding == "webguard":
        brand_name = "WEBGUARD"
        brand_color = "#2563EB"
        brand_logo = None

    else:
        brand_name = (company_name or "").strip()

        if not brand_name:
            raise ValueError(
                "El nombre de la empresa es obligatorio "
                "para los informes de marca blanca"
            )

        brand_color = primary_color or "#2563EB"
        brand_logo = logo_path

    domains = get_domains_by_client(client_id)

    # =========================================
    # INDICADORES DEL RESUMEN EJECUTIVO
    # =========================================

    total_domains = len(domains)
    analyzed_domains = 0
    verified_tls = 0
    unchecked_domains = 0

    for domain_record in domains:
        domain_history = get_analysis_history(domain_record["domain"])

        if not domain_history:
            unchecked_domains += 1
            continue

        latest_analysis = domain_history[0]
        analyzed_domains += 1

        if latest_analysis.get("tls_valid") is True:
            verified_tls += 1

        if (
            latest_analysis.get("tls_valid") is None
            and latest_analysis.get("http_status") is None
        ):
            unchecked_domains += 1

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
        textColor=colors.HexColor(brand_color),
        spaceBefore=16,
        spaceAfter=9,
    ))

    story = []

    # Primera página reservada para la portada gráfica.
    story.append(Spacer(1, 1 * cm))
    story.append(PageBreak())

    story.append(Paragraph(
        "Resumen ejecutivo",
        styles["WebGuardSection"]
    ))

    story.append(Spacer(1, 0.3 * cm))

    metric_cards = [
        [
            create_metric_card(
                "DOMINIOS REGISTRADOS",
                total_domains,
                brand_color
            ),
            create_metric_card(
                "DOMINIOS ANALIZADOS",
                analyzed_domains,
                brand_color
            ),
        ],
        [
            create_metric_card(
                "TLS VERIFICADOS",
                verified_tls,
                brand_color
            ),
            create_metric_card(
                "DOMINIOS SIN COMPROBAR",
                unchecked_domains,
                brand_color
            ),
        ],
    ]

    metrics_table = Table(
        metric_cards,
        colWidths=[8.1 * cm, 8.1 * cm],
    )

    metrics_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    story.append(metrics_table)
    story.append(Spacer(1, 0.4 * cm))

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
            tls_status = "No comprobado"

        if analysis["headers_present"] is None:
            headers_status = "No comprobadas"
        else:
            headers_status = (
                f"{analysis['headers_present']} / "
                f"{analysis['headers_total'] or 0}"
            )

        metrics = [
            ["Indicador", "Resultado"],
            ["Fecha del análisis", safe_text(analysis["analyzed_at"])],
            ["Certificado TLS", tls_status],
            ["Días restantes TLS", safe_text(analysis["tls_days_left"])],
            ["Estado HTTP", safe_text(analysis["http_status"])],
            ["Cabeceras detectadas", headers_status],
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

        if not http_checked:
            story.append(Paragraph(
                "No se dispone de una comprobación HTTP válida "
                "para este dominio. Por tanto, no es posible "
                "determinar si sus cabeceras de seguridad "
                "están presentes o ausentes.",
                styles["Normal"]
            ))

            story.append(Spacer(1, 0.3 * cm))
            continue

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


    def draw_first_page(canvas, doc):
        draw_report_cover(
        canvas,
        doc,
        brand_name,
        brand_color,
        client["name"]
    )

    def draw_later_pages(canvas, doc):
        draw_report_footer(
            canvas,
            doc,
            brand_name,
            brand_color
        )

    document.build(
        story,
        onFirstPage=draw_first_page,
        onLaterPages=draw_later_pages
    )

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes
