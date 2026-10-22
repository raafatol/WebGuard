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
    CondPageBreak,
    HRFlowable,
)
from app.database.client_repository import get_client_by_id
from app.database.domain_repository import get_domains_by_client
from app.database.analysis_repository import get_analysis_history
from app.services.recommendations import HEADER_INFO
from datetime import datetime, timezone
from uuid import uuid4
from reportlab.pdfgen import canvas as pdfcanvas
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
# Interior editorial del informe. La portada anterior permanece intacta.
from collections import Counter
from datetime import datetime
from reportlab.graphics.shapes import Drawing, Rect, Line, String, Circle, PolyLine
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import HRFlowable
import json, os, urllib.request
NAVY=colors.HexColor('#0A1831')
INK=colors.HexColor('#15233B')
MUTED=colors.HexColor('#63748B')
CYAN=colors.HexColor('#00A9D6')
PALE=colors.HexColor('#F2F7FC')
BORDER=colors.HexColor('#DCE6F0')
RED=colors.HexColor('#B9344C')
AMBER=colors.HexColor('#B66B12')
GREEN=colors.HexColor('#158064')
W=17*cm
def styles_for(accent):
    s=getSampleStyleSheet()
    for name, font, size, leading, color, before, after in [
        ('WGKicker','Helvetica-Bold',8,11,CYAN,5,9),
        ('WGTitle','Helvetica-Bold',27,33,NAVY,0,12),
        ('WGSection','Helvetica-Bold',15,20,NAVY,16,8),
        ('WGSub','Helvetica-Bold',10.5,15,INK,10,6),
        ('WGBody','Helvetica',9.5,15.5,INK,0,9),
        ('WGSmall','Helvetica',8,12,MUTED,0,7),
        ('WGLabel','Helvetica-Bold',7.4,10,MUTED,0,3),
        ('WGNumber','Helvetica-Bold',22,27,NAVY,0,1),
        ('WGCell','Helvetica',8.2,12,INK,0,0),
        ('WGCellHead','Helvetica-Bold',7.8,11,colors.white,0,0),
        ('WGWhite','Helvetica-Bold',11,15,colors.white,0,3),
        ('WGWhiteSmall','Helvetica',8,12,colors.HexColor('#B7D0E9'),0,0),
        ('WGInsight','Helvetica',10.5,17,INK,0,6),
    ]:
        s.add(ParagraphStyle(name=name,fontName=font,fontSize=size,leading=leading,
             textColor=color,spaceBefore=before,spaceAfter=after,keepWithNext=(name in ('WGSection','WGSub','WGKicker'))))
    return s
def format_date(value, date_only=False):
    if not value:
        return 'No disponible'
    if isinstance(value, datetime):
        d = value
    else:
        raw = str(value).strip().replace('Z', '+00:00')
        try:
            d = datetime.fromisoformat(raw)
        except ValueError:
            return str(value)
    if date_only:
        return d.strftime('%d/%m/%Y')
    # SQLite CURRENT_TIMESTAMP stores UTC without an offset. Other naive
    # timestamps must be treated consistently with that repository contract.
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    else:
        d = d.astimezone(timezone.utc)
    return d.strftime('%d/%m/%Y %H:%M UTC')
def friendly_tls_issuer(value):
    """Presentation-only; the original issuer remains unchanged in SQLite."""
    if not value:
        return None
    raw = str(value).strip()
    parts = {}
    for item in raw.split(','):
        if '=' in item:
            key, val = item.strip().split('=', 1)
            parts[key.strip().lower()] = val.strip()
    org = parts.get('organizationname') or parts.get('o')
    cn = parts.get('commonname') or parts.get('cn')
    if org and cn:
        return f'{org} ({cn})'
    return org or cn or raw


def friendly_tls_expiry(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).strip().replace('Z', '+00:00'))
        if dt.tzinfo is not None:
            from datetime import timezone
            dt = dt.astimezone(timezone.utc)
            return dt.strftime('%d/%m/%Y %H:%M UTC')
        # Never claim UTC for a timestamp without timezone information.
        return dt.strftime('%d/%m/%Y %H:%M')
    except (ValueError, TypeError, OverflowError):
        return str(value)


def friendly_tls_version(value):
    if not value:
        return None
    return {'TLSv1.3': 'TLS 1.3', 'TLSv1.2': 'TLS 1.2'}.get(str(value), str(value))


def tls_cipher_assessment(version, cipher):
    """A narrow classification, not a complete TLS configuration audit."""
    if not cipher:
        return None
    if str(version) in ('TLSv1.3', 'TLS 1.3') and str(cipher) in {
        'TLS_AES_256_GCM_SHA384', 'TLS_AES_128_GCM_SHA256', 'TLS_CHACHA20_POLY1305_SHA256'
    }:
        return 'Cifrado moderno (TLS 1.3); sin observaciones en la negociación analizada'
    return 'Sin clasificación automática; requiere revisión técnica'


# El informe utiliza únicamente observaciones guardadas; no realiza sondas de red.
_REDIRECT_LABELS = {
    'redirects_to_https': 'Redirección a HTTPS verificada',
    'no_redirect': 'Sin redirección HTTP → HTTPS observada',
    'ends_on_http': 'La cadena termina en HTTP',
    'redirect_loop': 'Bucle de redirecciones',
    'too_many_redirects': 'Límite de redirecciones alcanzado',
    'external_redirect_unverified': 'Destino externo no verificado',
    'unsupported_redirect': 'Destino no admitido / no verificado',
    'connection_error': 'No se pudo comprobar',
    'http_error_status': 'Respuesta HTTP de error',
    'invalid_domain': 'Dominio no válido para la comprobación',
    'unknown': 'Resultado no concluyente',
}


def redirect_result(analysis):
    value = (analysis or {}).get('redirect')
    return value if isinstance(value, dict) else None


def redirect_label(redirect):
    if redirect is None:
        return 'No comprobada'
    return _REDIRECT_LABELS.get(redirect.get('status'), 'Estado no reconocido / no verificado')


def redirect_details(redirect):
    if redirect is None:
        return []
    details = [('Estado', redirect_label(redirect))]
    code = redirect.get('http_status')
    if isinstance(code, int) and not isinstance(code, bool):
        details.append(('Última respuesta HTTP', str(code)))
    hops = redirect.get('hop_count')
    if isinstance(hops, int) and not isinstance(hops, bool) and hops >= 0:
        details.append(('Saltos observados', str(hops)))
    if redirect.get('final_url'):
        details.append(('Última URL comprobada', str(redirect['final_url'])[:240]))
    if redirect.get('location'):
        details.append(('Cabecera Location observada', str(redirect['location'])[:240]))
    if redirect.get('error'):
        details.append(('Error de comprobación', str(redirect['error'])[:120]))
    for index, hop in enumerate((redirect.get('hops') or [])[:5], 1):
        if isinstance(hop, dict):
            details.append((f'Salto {index}', f"{str(hop.get('status', '?'))}: {str(hop.get('from', '—'))[:120]} → {str(hop.get('to', '—'))[:160]}"))
    return details


def positive_controls(items):
    controls=[]
    for item in items:
        a=item['latest'] or {}
        domain=item['domain']
        if a.get('tls_valid') is True:
            days=a.get('tls_days_left')
            suffix=f' · {days} días hasta caducidad' if isinstance(days,(int,float)) else ''
            controls.append(f'{domain}: certificado TLS válido{suffix}')
            if a.get('tls_version') in ('TLSv1.3', 'TLS 1.3'):
                controls.append(f'{domain}: TLS 1.3 negociado en la conexión analizada')
        if (redirect_result(a) or {}).get('status') == 'redirects_to_https':
            controls.append(f'{domain}: redirección HTTP a HTTPS verificada en la cadena observada')
        if a.get('http_status') is not None:
            for name, hd in (a.get('headers') or {}).items():
                if isinstance(hd,dict) and hd.get('present') is True:
                    controls.append(f'{domain}: {name} detectada en la respuesta analizada')
    return controls
def txt(value, style):
    return Paragraph(safe_text(value),style)
def panel(content, bg=PALE, border=BORDER, pad=13, width=W):
    t=Table([[content]],colWidths=[width])
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),bg),('LINEBEFORE',(0,0),(0,-1),3,CYAN),('LINEBELOW',(0,-1),(-1,-1),.5,border),
        ('LEFTPADDING',(0,0),(-1,-1),pad),('RIGHTPADDING',(0,0),(-1,-1),pad),
        ('TOPPADDING',(0,0),(-1,-1),pad),('BOTTOMPADDING',(0,0),(-1,-1),pad),
    ]))
    return t
def section_eyebrow(story, label, st):
    story.append(Spacer(1, 5))
    story.append(txt(label.upper(), st['WGKicker']))
def insight_card(label, body, st, tone='info'):
    tones = {
        'info': (colors.HexColor('#EDF8FC'), CYAN),
        'warning': (colors.HexColor('#FFF6E8'), colors.HexColor('#D38B25')),
        'neutral': (colors.HexColor('#F1F5F9'), colors.HexColor('#7890A8')),
    }
    bg, stripe = tones.get(tone, tones['info'])
    content = [txt(label.upper(), st['WGLabel']), txt(body, st['WGInsight'])]
    t = Table([[content]], colWidths=[W])
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),bg),
        ('LINEBEFORE',(0,0),(0,-1),4,stripe),
        ('LEFTPADDING',(0,0),(-1,-1),16),
        ('RIGHTPADDING',(0,0),(-1,-1),16),
        ('TOPPADDING',(0,0),(-1,-1),15),
        ('BOTTOMPADDING',(0,0),(-1,-1),12),
    ]))
    return t
def headline(story, number, title, desc, st):
    story.append(txt('WEBGUARD  /  INFORME DE SEGURIDAD',st['WGKicker']))
    story.append(txt(f'{number}  {title}',st['WGTitle']))
    if desc: story.append(txt(desc,st['WGSmall']))
    story.append(HRFlowable(width='100%',thickness=1.2,color=CYAN,spaceAfter=14))
def sub(story, title, st):
    story.append(txt(title,st['WGSection']))
def metric(label,value,caption,st,width):
    content=[txt(label.upper(),st['WGLabel']),txt(value,st['WGNumber']),txt(caption,st['WGSmall'])]
    return panel(content,width=width,pad=12)
def metrics_row(values,st):
    width=(W-12)/4
    cells=[metric(label,value,caption,st,width) for label,value,caption in values]
    t=Table([cells],colWidths=[width+3]*4)
    t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),
       ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),3),
       ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0)]))
    return t
def table(rows,widths,st):
    data=[[txt(c,st['WGCellHead'] if i==0 else st['WGCell']) for c in row]
          for i,row in enumerate(rows)]
    t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),NAVY),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F7FAFD')]),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('LINEBELOW',(0,1),(-1,-1),.35,BORDER),
        ('LEFTPADDING',(0,0),(-1,-1),11),('RIGHTPADDING',(0,0),(-1,-1),10),
        ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
    ]))
    return t
def get_data(client_id):
    result=[]
    for d in get_domains_by_client(client_id):
        h=get_analysis_history(d['domain'])
        result.append({'domain':d['domain'],'history':h,'latest':h[0] if h else None})
    return result
def has_data(a):
    return a is not None and (a.get('tls_valid') is not None or a.get('http_status') is not None)
# Descripciones de riesgos potenciales, nunca afirmaciones de explotación.
HEADER_RISKS = {
    'HSTS': 'En determinados escenarios, una primera conexión HTTP sin protección HSTS podría permitir degradación a HTTP e interceptación por un atacante en la red. No se ha probado su explotabilidad.',
    'CSP': 'Sin una política CSP restrictiva se pierde una capa de defensa que puede limitar el impacto de ciertas inyecciones de contenido. No demuestra que exista una vulnerabilidad XSS.',
    'X-Frame-Options': 'La falta de restricciones de enmarcado puede aumentar la exposición a clickjacking si otras políticas, como frame-ancestors en CSP, tampoco lo impiden.',
    'X-Content-Type-Options': 'Sin nosniff, algunos navegadores podrían interpretar recursos con un tipo distinto del declarado en determinadas condiciones.',
    'Referrer-Policy': 'Una política de referencia insuficiente puede revelar información de navegación a otros orígenes, según la URL y las políticas predeterminadas del navegador.',
    'Permissions-Policy': 'Sin una política explícita puede haber menos restricciones sobre ciertas funciones del navegador; el impacto depende de las funciones utilizadas y los permisos existentes.',
}
EFFORT = {'HSTS':'Medio', 'CSP':'Alto', 'X-Frame-Options':'Bajo',
          'X-Content-Type-Options':'Bajo', 'Referrer-Policy':'Bajo', 'Permissions-Policy':'Bajo'}
ACTIONABLE_FIXES = {
    'HSTS': 'Tras confirmar HTTPS en todo el sitio, activar Strict-Transport-Security: max-age=300; aumentar progresivamente hasta 6-12 meses y valorar includeSubDomains solo tras verificar los subdominios.',
    'CSP': "Probar Content-Security-Policy-Report-Only: default-src 'self'; como punto de partida, ajustando las fuentes necesarias para cada sitio antes de aplicar una política obligatoria.",
    'X-Content-Type-Options': 'Configurar X-Content-Type-Options: nosniff.',
    'Referrer-Policy': 'Configurar Referrer-Policy: strict-origin-when-cross-origin, tras revisar los requisitos de la aplicación.',
    'Permissions-Policy': 'Restringir funciones innecesarias, por ejemplo Permissions-Policy: camera=(), microphone=(), geolocation=(); adaptar a las funciones realmente utilizadas.',
}
def findings(items):
    out=[]
    for item in items:
        a=item['latest']; domain=item['domain']
        if not a: continue
        if a.get('tls_valid') is False:
            out.append(dict(domain=domain,severity='Alta',title='Certificado TLS no válido',
              evidence='La última comprobación devolvió tls_valid=False.',
              impact='Los navegadores podrían rechazar la conexión o advertir de un problema de autenticación TLS.',
              fix='Revisar vigencia, cadena de confianza y coincidencia del nombre del certificado.',effort='Medio'))
        days=a.get('tls_days_left')
        if a.get('tls_valid') is True and isinstance(days,(int,float)) and days<=30:
            out.append(dict(domain=domain,severity='Alta' if days<=7 else 'Media',
              title='Certificado TLS próximo a caducar',evidence=f'Quedan {days} días de validez.',
              impact='Si el certificado expira sin renovación, los clientes pueden recibir errores de conexión.',
              fix='Renovar el certificado y comprobar la renovación automática.',effort='Bajo'))
        redirect = redirect_result(a)
        redirect_status = (redirect or {}).get('status')
        if redirect_status in ('no_redirect', 'ends_on_http'):
            code = redirect.get('http_status')
            evidence = (f'Comprobación HTTP → HTTPS: {redirect_label(redirect)}; '
                        f'respuesta HTTP {code if isinstance(code, int) else "no disponible"}; '
                        f'última URL {str(redirect.get("final_url") or "no disponible")[:180]}.')
            out.append(dict(domain=domain, severity='Media',
                title='Sin redirección HTTP → HTTPS observada' if redirect_status == 'no_redirect' else 'Cadena de redirección finalizada en HTTP',
                evidence=evidence,
                impact='La conexión HTTP puede permanecer sin cifrar; el riesgo depende también de HSTS, precarga y del comportamiento del cliente. No se ha demostrado explotación.',
                fix='Configurar una redirección desde HTTP hacia HTTPS y verificar la cadena completa; revisar HSTS cuando el sitio funcione íntegramente por HTTPS.',
                effort='Bajo'))
        # Los estados indeterminados (errores, bucles, externos) no se convierten
        # automáticamente en vulnerabilidades confirmadas.
        if a.get('http_status') is not None:
            for name,info in HEADER_INFO.items():
                hd=(a.get('headers') or {}).get(name)
                if isinstance(hd,dict) and hd.get('present') is False:
                    out.append(dict(domain=domain,severity='Media' if name in ('HSTS','CSP','X-Frame-Options') else 'Baja',
                       title=f'Cabecera no detectada: {name}',
                       evidence=f'La cabecera {name} no se detectó en la respuesta HTTP analizada.',
                       impact=HEADER_RISKS.get(name,'La ausencia de este control puede reducir la defensa en profundidad según el contexto.'),
                       fix=ACTIONABLE_FIXES.get(name, info['recommendation']),effort=EFFORT.get(name,'Medio')))
    return sorted(out,key=lambda x:({'Alta':0,'Media':1,'Baja':2}[x['severity']],x.get('effort')!='Bajo',x['domain']))
def stats(items):
    return (len(items),sum(has_data(i['latest']) for i in items),
            sum(i['latest'] is not None and i['latest'].get('tls_valid') is True for i in items),
            sum(i['latest'] is not None and i['latest'].get('http_status') is not None for i in items))
def diagnosis(items,issues):
    total,covered,tls,http=stats(items)
    if not total: return 'El cliente no tiene dominios registrados. Añada un dominio y ejecute las comprobaciones para iniciar la evaluación.'
    if not covered: return ('No hay mediciones TLS o HTTP concluyentes. La seguridad no puede evaluarse con estos datos. '
       'La prioridad es restaurar la cobertura de monitorización y repetir los análisis.')
    counts=Counter(i['severity'] for i in issues)
    tls_text=f'{tls} {"tiene" if tls==1 else "tienen"} TLS válido'
    http_text=f'{http} {"tiene" if http==1 else "tienen"} respuesta HTTP registrada'
    return (f'Se han obtenido datos del {100*covered/total:.0f}% de los dominios en alcance ({covered} de {total}); {tls_text} y '
       f'{http_text}. Se observan {len(issues)} hallazgos de configuración '
       f'({counts["Alta"]} altos, {counts["Media"]} medios y {counts["Baja"]} bajos). '
       'Los resultados son parciales y no equivalen a una auditoría de seguridad exhaustiva.')
def ai_text(items, issues, summary):
    """Optional external analysis; no API key or provider error breaks report creation.
    Only aggregate monitoring evidence is transmitted. Never include API secrets,
    raw headers, cookies or client contact information in the request.
    """
    if os.getenv('WEBGUARD_REPORT_AI_ENABLED') != '1':
        return None
    key = os.getenv('OPENAI_API_KEY', '').strip()
    if not key:
        import logging
        logging.getLogger(__name__).warning('WebGuard AI enabled but OPENAI_API_KEY is missing')
        return None
    from urllib.error import HTTPError, URLError
    import logging
    log = logging.getLogger(__name__)
    evidence = {
        'scope': 'TLS certificate, six HTTP response security headers and observed HTTP-to-HTTPS redirects',
        'metrics': {'domains': stats(items)[0], 'covered': stats(items)[1],
                    'tls_valid': stats(items)[2], 'http_observed': stats(items)[3]},
        'findings': [dict(domain=x['domain'], severity=x['severity'],
                          title=x['title'], evidence=x['evidence'], impact=x['impact'], fix=x['fix'])
                     for x in issues[:25]],
        'diagnosis': summary,
        'latest': [dict(domain=i['domain'],
                        observed_at=(i['latest'] or {}).get('analyzed_at'),
                        tls_valid=(i['latest'] or {}).get('tls_valid'),
                        http_status=(i['latest'] or {}).get('http_status'))
                   for i in items[:30]],
    }
    payload = {
        'model': os.getenv('WEBGUARD_REPORT_AI_MODEL', 'gpt-4.1-mini'),
        'messages': [
            {'role': 'system', 'content': (
                'Eres un analista de seguridad redactando un informe para un cliente. '
                'Responde en español, en texto plano, con máximo 180 palabras y tres párrafos: '
                'SITUACIÓN ACTUAL, RIESGOS POTENCIALES y PRÓXIMOS PASOS. '
                'Usa solo los datos JSON. Nunca inventes resultados, exploits, gravedad CVSS '
                'ni vulnerabilidades. Si no hay mediciones concluyentes, dilo expresamente. '
                'Habla de RIESGOS POTENCIALES, nunca RIESGOS CONFIRMADOS salvo evidencia directa. '
                'No contradigas ni amplifiques los impactos incluidos en el JSON. '
                'No uses el adjetivo importantes para cabeceras; distingue la gravedad por hallazgo. '
                'Describe la evidencia como una respuesta HTTP observada, no como todo el sitio. '
                'No afirmes cuántas rutas se analizaron: una respuesta HTTP no equivale a una ruta. '
                'Si mencionas el alcance, di: La evaluación se basa en una única respuesta HTTP analizada; no se comprobaron otras rutas o respuestas. ')},
            {'role': 'user', 'content': json.dumps(evidence, ensure_ascii=False)}
        ],
        'temperature': 0.2, 'max_tokens': 420,
    }
    try:
        req = urllib.request.Request(
            'https://api.openai.com/v1/chat/completions',
            data=json.dumps(payload).encode('utf-8'),
            headers={'Authorization': 'Bearer ' + key,
                     'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(req, timeout=15) as resp:
            answer = json.load(resp)
        result = answer['choices'][0]['message']['content'].strip()
        return result[:3000] if result else None
    except HTTPError as exc:
        log.warning('WebGuard AI HTTP %s: %s', exc.code, exc.reason)
    except (URLError, OSError, ValueError, KeyError, IndexError, TypeError) as exc:
        log.warning('WebGuard AI unavailable: %s', type(exc).__name__)
    return None
def issue_card(issue, st, number):
    """One actionable finding combines risk, evidence, fix and effort."""
    severity=issue['severity']
    tone={'Alta':RED,'Media':AMBER,'Baja':GREEN}[severity]
    quick=issue.get('effort')=='Bajo'
    heading=Table([[txt(f'{number:02d}  {issue["title"]}', st['WGWhite']),
                    txt(severity.upper()+('  ·  RÁPIDA' if quick else ''),st['WGWhiteSmall'])]],
                  colWidths=[W-132,132])
    heading.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),NAVY),
        ('LINEBELOW',(0,0),(-1,-1),3,tone),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('LEFTPADDING',(0,0),(-1,-1),12),('RIGHTPADDING',(0,0),(-1,-1),8),
        ('TOPPADDING',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),9)]))
    body=[txt('DOMINIO / '+issue['domain'],st['WGLabel']),
          txt('EVIDENCIA · '+issue['evidence'],st['WGSmall']),
          txt('RIESGO · '+issue['impact'],st['WGBody']),
          txt('ACCIÓN RECOMENDADA · '+issue['fix'],st['WGBody']),
          txt('ESFUERZO / '+issue.get('effort','Por determinar')+' · Estimación orientativa',st['WGLabel'])]
    return KeepTogether([heading,panel(body,pad=11),Spacer(1,9)])
def timeline(item):
    h=list(reversed(item['history']))
    valid=[]
    for a in h:
        if a.get('http_status') is not None and type(a.get('headers_present')) is int and type(a.get('headers_total')) is int and 0 <= a['headers_present'] <= a['headers_total'] and a['headers_total']>0:
            valid.append((a.get('analyzed_at'),max(0,min(100,100*a['headers_present']/a['headers_total']))))
    if len(valid)<5 or max(v for _,v in valid)-min(v for _,v in valid)<0.01: return None
    d=Drawing(470,174)
    d.add(Rect(0,0,470,174,fillColor=PALE,strokeColor=BORDER,strokeWidth=.5))
    for val in (0,50,100):
        y=29+val*.95
        d.add(Line(47,y,451,y,strokeColor=BORDER,strokeWidth=.7))
        d.add(String(10,y-3,str(val)+'%',fontSize=8,fillColor=MUTED))
    coords=[]
    for idx,(_,value) in enumerate(valid):
        x=49+idx*398/max(1,len(valid)-1); y=29+value*.95
        coords.extend([x,y]);d.add(Circle(x,y,3,fillColor=CYAN,strokeColor=CYAN))
    d.add(PolyLine(coords,strokeColor=CYAN,strokeWidth=2.3,fillColor=None))
    d.add(String(49,10,format_date(valid[0][0]),fontSize=7,fillColor=MUTED))
    d.add(String(346,10,format_date(valid[-1][0]),fontSize=7,fillColor=MUTED))
    d.add(String(49,157,f'Inicio: {valid[0][1]:.0f}%   |   Último: {valid[-1][1]:.0f}%   |   {len(valid)} mediciones',fontName='Helvetica-Bold',fontSize=9,fillColor=NAVY))
    return d
def footer(canvas,doc,name,color):
    canvas.saveState();w,_=A4
    canvas.setStrokeColor(BORDER);canvas.line(2*cm,1.6*cm,w-2*cm,1.6*cm)
    canvas.setFillColor(colors.HexColor(color));canvas.setFont('Helvetica-Bold',8)
    canvas.drawString(2*cm,1.23*cm,str(name)[:40]);canvas.setFillColor(MUTED)
    canvas.setFont('Helvetica',8)
    canvas.drawRightString(w-2*cm,1.23*cm,f'PÁGINA {doc.page:02d}  /  CONFIDENCIAL')
    canvas.restoreState()
# V6: editorial report composition. Cover routine above is unchanged.
def _progress_visual(items, st):
    """A compact evidence-based coverage dashboard; unknown is not zero risk."""
    total = len(items)
    measured = sum(has_data(i['latest']) for i in items)
    tls_tested = sum(i['latest'] is not None and i['latest'].get('tls_valid') is not None for i in items)
    http_tested = sum(i['latest'] is not None and i['latest'].get('http_status') is not None for i in items)
    measures = [('COBERTURA ACTUAL', measured, total),
                ('CERTIFICADOS EVALUADOS', tls_tested, total),
                ('RESPUESTAS HTTP OBSERVADAS', http_tested, total)]
    d = Drawing(W, 122)
    d.add(Rect(0, 0, W, 122, fillColor=colors.HexColor('#F1F6FA'), strokeColor=None))
    for idx, (label, value, denominator) in enumerate(measures):
        y = 97 - idx * 37
        d.add(String(16, y, label, fontName='Helvetica-Bold', fontSize=8, fillColor=NAVY))
        d.add(String(W-16, y, f'{value} / {denominator}', textAnchor='end', fontName='Helvetica-Bold', fontSize=9, fillColor=NAVY))
        d.add(Rect(16, y-14, W-32, 6, fillColor=colors.HexColor('#DAE5EC'), strokeColor=None))
        if denominator and value:
            d.add(Rect(16, y-14, (W-32)*value/denominator, 6, fillColor=CYAN, strokeColor=None))
    return d
def _severity_visual(issues, st):
    """Risk distribution is a count of observed findings, not a risk score."""
    counts = Counter(i['severity'] for i in issues)
    tones = [('ALTA', 'Alta', colors.HexColor('#C74B50')),
             ('MEDIA', 'Media', colors.HexColor('#D5902D')),
             ('BAJA', 'Baja', colors.HexColor('#1E9C9A'))]
    d = Drawing(W, 75)
    d.add(Rect(0, 0, W, 75, fillColor=colors.HexColor('#F1F6FA'), strokeColor=None))
    slot=(W-32)/3
    for idx, (label, key, color) in enumerate(tones):
        x=16+idx*slot
        d.add(Circle(x+7, 49, 4, fillColor=color, strokeColor=None))
        d.add(String(x+19, 46, label, fontName='Helvetica-Bold', fontSize=8, fillColor=MUTED))
        d.add(String(x+1, 12, str(counts[key]), fontName='Helvetica-Bold', fontSize=23, fillColor=NAVY))
    return d
def _priority_name(issue):
    """Nombre de control legible, nunca el título literal de un hallazgo."""
    title = str(issue.get('title', ''))
    if 'redirecci' in title.lower():
        return 'la redirección HTTP → HTTPS'
    if title.startswith('Cabecera no detectada: '):
        return title.split(': ', 1)[1]
    return 'el control de seguridad señalado'


def _join_spanish(values):
    values = list(dict.fromkeys(values))
    if not values:
        return ''
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f'{values[0]} y {values[1]}'
    return ', '.join(values[:-1]) + ' y ' + values[-1]


def _ai_narrative_visual(narrative, st, issues=None):
    """Texto breve, sin concatenar títulos de hallazgos como sustantivos."""
    import re
    clean = re.sub(r'(?im)^\s*\*{0,2}(SITUACI[ÓO]N ACTUAL|RIESGOS POTENCIALES|PR[ÓO]XIMOS PASOS)\*{0,2}\s*[:\-]?\s*', '', narrative or '')
    clean = re.sub(r'\s+', ' ', clean).strip()
    # La plantilla determinista ya contiene sus prioridades y no se trunca.
    if issues is not None:
        return panel([txt('INTERPRETACIÓN AUTOMATIZADA', st['WGLabel']),
                      txt(clean, st['WGBody'])], pad=12)
    return panel([txt('INTERPRETACIÓN AUTOMATIZADA', st['WGLabel']),
                  txt(clean[:900], st['WGBody'])], pad=12)


def _fallback_narrative(items, issues):
    """Resumen breve basado solo en mediciones observadas, sin duplicar métricas."""
    total, covered, _, _ = stats(items)
    if not total:
        return ('No hay dominios en alcance. Prioridad: registrar los activos y '
                'obtener una primera medición. Alcance limitado a los datos registrados.')
    if not covered:
        return ('No hay mediciones concluyentes para los dominios en alcance. '
                'Prioridad: restablecer la monitorización y repetir las comprobaciones.')
    lead = (f'Se ha evaluado {covered} dominio.' if covered == 1 else
            f'Se han evaluado {covered} dominios.')
    if covered < total:
        lead += (f' Quedan {total-covered} '
                 f'{"dominio" if total-covered == 1 else "dominios"} sin mediciones concluyentes.')
    missing = list(dict.fromkeys(
        i['title'].split(': ', 1)[1] for i in issues
        if i['title'].startswith('Cabecera no detectada: ')))
    if missing:
        lead += (' Las cabeceras ' + _join_spanish(missing) +
                 ' no se detectaron en las respuestas analizadas.')
    redirect_missing = any(i['title'] == 'Sin redirección HTTP → HTTPS observada'
                           for i in issues)
    redirect_http = any(i['title'] == 'Cadena de redirección finalizada en HTTP'
                        for i in issues)
    if redirect_missing:
        lead += ' No se observó redirección de HTTP a HTTPS.'
    elif redirect_http:
        lead += ' Se observó una cadena de redirección que termina en HTTP.'
    priority = [i for i in issues if i['severity'] in ('Alta', 'Media')]
    if priority:
        names = [_priority_name(i) for i in priority]
        lead += (' Prioridad: revisar ' + _join_spanish(names) +
                 ', y verificar los cambios tras aplicarlos.')
    elif issues:
        lead += ' Prioridad: revisar las recomendaciones y verificar los cambios tras aplicarlos.'
    else:
        lead += ' No se identificaron hallazgos en los controles comprobados.'
    return lead + ' Alcance limitado a las respuestas registradas.'

class _ChapterMarker:
    def __init__(self, elements):
        self.elements=elements
def _chapter(story, number, title, subtitle, st):
    block=[Spacer(1,11),txt(f'SECCIÓN {number}  /  INFORME DE SEGURIDAD WEB',st['WGKicker']),
           txt(title,st['WGSection'])]
    if subtitle: block.append(txt(subtitle,st['WGSmall']))
    block.append(HRFlowable(width='100%',thickness=.8,color=BORDER,spaceAfter=10))
    story.append(_ChapterMarker(block))
def _mini_status(domain, a, st):
    """Inventario compacto: reserva espacio para las cabeceras en la misma página."""
    tls='Válido' if a.get('tls_valid') is True else 'No válido' if a.get('tls_valid') is False else 'No comprobado'
    http=str(a['http_status']) if a.get('http_status') is not None else 'No comprobado'
    hp=a.get('headers_present'); ht=a.get('headers_total')
    heads=f'{hp}/{ht}' if a.get('http_status') is not None and hp is not None and ht else 'No comprobadas'
    rows=[['CONTROL','RESULTADO'],['Certificado TLS',tls],['Respuesta HTTP',http],
          ['Cabeceras detectadas',heads],['Días hasta caducidad TLS',str(a.get('tls_days_left')) if a.get('tls_days_left') is not None else 'No comprobado']]
    return panel([txt(domain,st['WGSub']),
                  txt('Última ejecución: '+format_date(a.get('analyzed_at')),st['WGSmall']),
                  table(rows,[7.4*cm,9*cm],st)],bg=colors.white,pad=10)


def _technical_status(a, st):
    """Detalle breve, después de la tabla HTTP; sin duplicar la fila del inventario."""
    parts=[]
    tls=[('Emisor',friendly_tls_issuer(a.get('tls_issuer'))),
         ('Caducidad',friendly_tls_expiry(a.get('tls_expiry_date'))),
         ('Protocolo',friendly_tls_version(a.get('tls_version'))),
         ('Cifrado',a.get('tls_cipher')),
         ('Valoración',tls_cipher_assessment(a.get('tls_version'),a.get('tls_cipher'))),
         ('Firma',a.get('tls_signature_algorithm'))]
    tls=[f'{label}: {value}' for label,value in tls if value is not None and str(value).strip()]
    if tls:
        parts.append(txt('DETALLES TÉCNICOS TLS',st['WGLabel']))
        for line in tls:
            parts.append(txt(line,st['WGSmall']))
    redirect=redirect_result(a)
    if redirect is not None:
        parts.append(txt('REDIRECCIÓN HTTP → HTTPS',st['WGLabel']))
        for label,value in redirect_details(redirect):
            parts.append(txt(f'{label}: {value}',st['WGSmall']))
    return KeepTogether(parts) if parts else Spacer(1,0)

def _narrative_sections(narrative, st):
    # The provider may return text with section labels but no line breaks.
    # Keep it together with the title, so no orphan heading remains on a page.
    return KeepTogether([txt('INTERPRETACIÓN AUTOMATIZADA',st['WGLabel']),
        Spacer(1,6),txt(narrative,st['WGBody']),
        txt('Interpretación automatizada basada en las evidencias disponibles; no equivale a una auditoría.',st['WGSmall'])])
def generate_client_report(client_id,branding='webguard',company_name=None,primary_color=None,
                           logo_path=None,report_type='complete',include_ai=True,
                           include_history=True,include_appendix=True):
    client=get_client_by_id(client_id)
    if client is None: raise ValueError('El cliente indicado no existe')
    if branding not in ('webguard','white_label'): raise ValueError('Modalidad de informe no válida')
    if report_type not in ('complete','executive','technical'): raise ValueError('Tipo de informe no válido')
    name='WEBGUARD' if branding=='webguard' else (company_name or '').strip()
    if not name: raise ValueError('El nombre de empresa es obligatorio en marca blanca')
    accent='#00A9D6' if branding=='webguard' else (primary_color or '#2563EB')
    try: colors.HexColor(accent)
    except (ValueError,TypeError) as e: raise ValueError('Color de marca no válido') from e
    st=styles_for(accent)
    # Random suffix avoids falsely suggesting a persistent sequential counter.
    # Each newly generated PDF receives its own traceable reference.
    generated_at=datetime.now(timezone.utc)
    report_id=f'WG-{generated_at:%Y-%m%d}-{uuid4().hex[:8].upper()}'
    items=get_data(client_id); issues=findings(items)
    total,covered,tls,http=stats(items); counts=Counter(i['severity'] for i in issues)
    summary=diagnosis(items,issues)
    # La interpretación comercial es determinista: no requiere llamadas de IA.
    narrative=None
    buf=BytesIO()
    doc=SimpleDocTemplate(buf,pagesize=A4,leftMargin=2*cm,rightMargin=2*cm,
        topMargin=1.65*cm,bottomMargin=1.9*cm,title='WebGuard | '+client['name'],
        pageCompression=1)
    class ReportStory(list):
        def append(self, element):
            if self and isinstance(self[-1], _ChapterMarker):
                chapter=self.pop()
                super().append(KeepTogether([*chapter.elements, element]))
            else:
                super().append(element)
    story=ReportStory([Spacer(1,1*cm),PageBreak()])
    headline(story,'SECCIÓN 01 /','Estado de seguridad',f'{client["name"]}  /  {format_date(datetime.now(), date_only=True)}',st)
    story.append(metrics_row([('DOMINIOS',str(total),'en alcance'),
        ('COBERTURA',f'{covered}/{total}','con datos recientes'),
        ('TLS VÁLIDO',str(tls),'última ejecución'),
        ('HTTP',str(http),'última ejecución')],st))
    story.append(Spacer(1,12))
    # Avoid duplicating the four dashboard counters with three identical progress bars.
    story.append(Spacer(1,8))
    state='COBERTURA INSUFICIENTE' if covered<total else 'REQUIERE ATENCIÓN' if counts['Alta'] or counts['Media'] else 'OBSERVACIONES MENORES' if issues else 'SIN HALLAZGOS OBSERVADOS'
    story.append(insight_card(state,summary,st,'warning' if covered<total or counts['Alta'] or counts['Media'] else 'info'))
    story.append(txt('Criterio: «Requiere atención» si existe al menos un hallazgo alto o medio; «Cobertura insuficiente» si falta una última medición concluyente en algún dominio. No es una puntuación global.',st['WGSmall']))
    story.append(Spacer(1,10))
    section_eyebrow(story, 'DISTRIBUCIÓN DE HALLAZGOS OBSERVADOS', st)
    story.append(_severity_visual(issues, st))
    story.append(txt('Recuento de observaciones; no representa una puntuación global de riesgo. Orden de hallazgos: severidad y, dentro de cada nivel, menor esfuerzo primero.', st['WGSmall']))
    # El detalle de hallazgos ya incorpora severidad, riesgo y corrección.
    # Evitamos repetirlo en el resumen ejecutivo.
    section_number=1
    def executive_context():
        blocks=[]
        # La interpretación comercial mantiene una redacción consistente y
        # verificable incluso si la IA está desactivada o falla.
        blocks.append(_ai_narrative_visual(_fallback_narrative(items, issues), st, issues))
        blocks.append(txt('Interpretación basada en evidencias de las mediciones registradas; no sustituye una auditoría de seguridad.', st['WGSmall']))
        positives=positive_controls(items)[:5]
        if positives:
            blocks.append(txt('Controles correctos observados',st['WGSub']))
            for control in positives:
                blocks.append(txt('OK  ·  '+control,st['WGBody']))
        return blocks
    # La interpretación pertenece al resumen ejecutivo, nunca al inventario.
    context=executive_context()
    if context:
        for block in context:
            story.append(block)
    if report_type!='executive':
        section_number+=1
        _chapter(story,f'{section_number:02d}','Inventario de activos','Estado de la última observación por dominio',st)
        if not items: story.append(txt('No hay dominios registrados.',st['WGBody']))
        for item in items:
            a=item['latest'] or {}
            story.append(KeepTogether([_mini_status(item['domain'],a,st),Spacer(1,9)]))
            if a.get('http_status') is not None:
                rows=[['CONTROL HTTP','ESTADO','EVIDENCIA']]
                for hn in HEADER_INFO:
                    hd=(a.get('headers') or {}).get(hn)
                    state='Presente' if isinstance(hd,dict) and hd.get('present') is True else 'Ausente' if isinstance(hd,dict) and hd.get('present') is False else 'Sin dato'
                    val=str(hd.get('value') or '—')[:100] if isinstance(hd,dict) else '—'
                    rows.append([hn,state,val])
                # Una tabla corta de seis controles nunca debe fragmentarse entre páginas.
                story.append(KeepTogether([table(rows,[4.7*cm,2.4*cm,9.9*cm],st)]))
            else:
                story.append(txt('HTTP no comprobado: no se deduce ausencia de cabeceras.',st['WGSmall']))
            story.append(_technical_status(a,st))
        if issues:
            section_number+=1
            _chapter(story,f'{section_number:02d}','Hallazgos y correcciones','Riesgo, evidencia, acción concreta y esfuerzo estimado',st)
            for n,i in enumerate(issues,1):story.append(issue_card(i,st,n))
        if include_history:
            charts=[(i,timeline(i)) for i in items]
            charts=[(i,c) for i,c in charts if c is not None]
            if charts:
                section_number+=1
                _chapter(story,f'{section_number:02d}','Evolución de controles',
              'Porcentaje de las seis cabeceras HTTP detectadas; no es una puntuación de seguridad',st)
                for i,c in charts:
                    story.append(KeepTogether([txt(i['domain'],st['WGSub']),panel(c),Spacer(1,9)]))
            elif items:
                story.append(txt('EVOLUCIÓN HISTÓRICA',st['WGSub']))
            story.append(txt('Sin cambios relevantes o sin suficientes mediciones comparables.',st['WGSmall']))
        # Remediation is included in each finding: do not repeat the plan.
        if covered < total:
            story.append(insight_card('Cobertura incompleta',
              f'{total-covered} de {total} dominios carecen de una última comprobación TLS/HTTP concluyente. Revisar conectividad y repetir el análisis.',st,'warning'))
        elif not issues:
            story.append(txt('Mantener la monitorización periódica y revisar cambios de configuración.',st['WGBody']))
        if include_appendix or report_type=='technical':
            story.append(PageBreak())
            section_number+=1
            _chapter(story,f'{section_number:02d}','Método y limitaciones','Trazabilidad del alcance de esta evaluación',st)
            story.append(txt('ORIGEN  /  Registros históricos de monitorización de WebGuard. Se utiliza la última ejecución por dominio y las últimas 50 mediciones como máximo.',st['WGBody']))
            story.append(txt('ALCANCE  /  Certificado TLS, respuesta HTTP, presencia de seis cabeceras y cadena de redirección HTTP a HTTPS observada. No se han comprobado exhaustivamente otras rutas, páginas o respuestas.',st['WGBody']))
            story.append(KeepTogether([txt('LIMITACIONES  /  No se ha realizado pentesting, auditoría de código ni comprobación exhaustiva de vulnerabilidades. Las redirecciones solo se siguen hasta cinco saltos y dentro del mismo host; los destinos externos y los errores se consideran no verificados. La ausencia de redirección no demuestra por sí sola explotación ni descarta protección HSTS en clientes.',st['WGBody']),txt('PERIODICIDAD  /  El informe refleja las comprobaciones registradas hasta la fecha de emisión; los intervalos entre registros pueden variar.',st['WGSmall'])]))
    else:
        section_number+=1
        _chapter(story,f'{section_number:02d}','Acciones recomendadas','Decisiones sugeridas para el siguiente ciclo de monitorización',st)
        if issues:
            for i in issues[:5]: story.append(txt(f'{i["severity"]} / {i["domain"]}: {i["fix"]}',st['WGBody']))
        else: story.append(txt('Completar las comprobaciones pendientes y mantener monitorización periódica.',st['WGBody']))
    if report_type != 'executive' and include_appendix:
        glossary = [
            ('TLS', 'Protocolo que protege la comunicación entre navegador y servidor.'),
            ('HSTS', 'Indicación para que el navegador utilice HTTPS en conexiones futuras.'),
            ('Redirección HTTP → HTTPS', 'Envía automáticamente al visitante a la versión cifrada del sitio.'),
            ('CSP', 'Política que restringe los orígenes de contenido que puede cargar una página.'),
            ('Cabecera HTTP', 'Información enviada por el servidor junto a una respuesta web.'),
            ('X-Content-Type-Options', 'Evita que ciertos navegadores interpreten tipos MIME distintos del declarado.'),
            ('Referrer-Policy', 'Controla la información de referencia compartida al navegar.'),
            ('Permissions-Policy', 'Restringe el uso de determinadas funciones del navegador.'),
            ('Report-Only', 'Permite probar una CSP sin bloquear recursos.'),
            ('nosniff', 'Valor que impide determinados intentos de adivinar tipos MIME.'),
            ('XSS', 'Inyección de scripts en el contexto de una página web.'),
            ('MIME', 'Identificador del tipo de contenido de un recurso.'),
        ]
        glossary_rows = [[txt(term,st['WGCell']), txt(definition,st['WGCell'])] for term,definition in glossary]
        glossary_table=Table(glossary_rows,colWidths=[4.5*cm,12.5*cm],hAlign='LEFT')
        glossary_table.setStyle(TableStyle([
            ('ROWBACKGROUNDS',(0,0),(-1,-1),[colors.white,PALE]),
            ('VALIGN',(0,0),(-1,-1),'TOP'),
            ('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),8),
            ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
        ]))
        story.append(KeepTogether([txt('GLOSARIO',st['WGSection']),glossary_table]))
    story.append(Spacer(1,10))
    contact_email=os.getenv('WEBGUARD_REPORT_CONTACT_EMAIL','').strip()
    contact_web=os.getenv('WEBGUARD_REPORT_CONTACT_WEB','').strip()
    contact_phone=os.getenv('WEBGUARD_REPORT_CONTACT_PHONE','').strip()
    contacts=[f'Email: {contact_email}' if contact_email else '',
              f'Web: {contact_web}' if contact_web else '',
              f'Teléfono: {contact_phone}' if contact_phone else '']
    contacts=[c for c in contacts if c]
    if contacts:
        cta=('Solicita una revisión técnica de los hallazgos, apoyo para aplicar las '
             'correcciones y una nueva verificación de los controles. '
             'Contacto: ' + ' · '.join(contacts) + '.')
    else:
        cta=('Solicita una revisión técnica de los hallazgos y apoyo para aplicar '
             'las correcciones y verificar los resultados. '
             'Consulta con el proveedor del informe los canales de contacto disponibles.')
    story.append(KeepTogether([Spacer(1,10),insight_card('SOLICITA UNA REVISIÓN TÉCNICA',cta,st)]))
    story.append(txt('Alcance limitado a los controles registrados. Documento confidencial; no sustituye una auditoría de seguridad.',st['WGSmall']))
    class NumberedCanvas(pdfcanvas.Canvas):
        # Dos pasadas internas: numeración de páginas sin alterar la portada.
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._saved_pages=[]
        def showPage(self):
            self._saved_pages.append(dict(self.__dict__))
            self._startPage()
        def save(self):
            total=len(self._saved_pages)
            for state in self._saved_pages:
                self.__dict__.update(state)
                if self._pageNumber > 1:
                    self.saveState()
                    width,_=A4
                    self.setStrokeColor(BORDER)
                    self.line(2*cm,1.6*cm,width-2*cm,1.6*cm)
                    self.setFillColor(colors.HexColor(accent))
                    self.setFont('Helvetica-Bold',8)
                    self.drawString(2*cm,1.23*cm,str(name)[:24])
                    self.setFillColor(MUTED)
                    self.setFont('Helvetica',7)
                    self.drawCentredString(width/2,1.23*cm,report_id)
                    self.setFont('Helvetica',8)
                    self.drawRightString(width-2*cm,1.23*cm,
                        f'PÁGINA {self._pageNumber:02d} DE {total:02d}  /  CONFIDENCIAL')
                    self.restoreState()
                super().showPage()
            super().save()
    doc.build(story,onFirstPage=lambda c,d:draw_report_cover(c,d,name,accent,client['name']),
        onLaterPages=lambda c,d:None,canvasmaker=NumberedCanvas)
    result=buf.getvalue();buf.close();return result
