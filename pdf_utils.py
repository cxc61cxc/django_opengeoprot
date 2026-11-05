import io
import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.utils import timezone
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

User = get_user_model()


def add_watermark_to_pdf(pdf_bytes, text=None, user=None):
    """Sovrappone un watermark testuale su ogni pagina del PDF e inserisce i metadati utente."""
    # Gli utenti staff non ricevono il watermark: ritorna il PDF invariato
    if user is not None and user.is_authenticated and user.is_staff:
        return pdf_bytes

    if text is None:
        if user is not None and user.is_authenticated:
            username = user.get_username()
        else:
            username = 'anonimo'
        timestamp = timezone.now().strftime('%d/%m/%Y %H:%M:%S')
        text = f'Generato da {username} il {timestamp} (c) - Comune di Carrara'

    original = PdfReader(io.BytesIO(pdf_bytes), strict=False)
    writer = PdfWriter()
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=letter)
    width, height = letter

    # Watermark diagonale centrale grande e visibile
    c.setFont('Helvetica-Bold', 22)
    c.setFillColorRGB(0.55, 0.55, 0.55)
    c.saveState()
    c.translate(width / 2, height / 2)
    c.rotate(-45)
    c.drawCentredString(0, 0, text)
    c.restoreState()

    # Testo in basso a destra
    c.setFont('Helvetica', 10)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.drawRightString(width - 40, 30, text)

    c.save()
    packet.seek(0)
    watermark_pdf = PdfReader(packet)
    watermark_page = watermark_pdf.pages[0]

    for page in original.pages:
        page.merge_page(watermark_page)
        writer.add_page(page)

    # Metadati utente nel PDF
    if user is not None and user.is_authenticated:
        writer.add_metadata({
            '/Author': user.get_full_name() or user.get_username(),
            '/Creator': user.get_username(),
            '/Subject': 'Documento generato da utente autenticato',
            '/Keywords': f'user:{user.get_username()}',
            '/Copyright': 'Comune di Carrara',
        })

    output = io.BytesIO()
    writer.write(output)
    output.seek(0)
    return output.getvalue()


def log_pdf_access(request, filename, app_label=None, pk=None):
    ip = request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR')
    username = request.user.get_username() if request.user.is_authenticated else 'anonimo'
    timestamp = timezone.now().strftime('%d/%m/%Y %H:%M:%S')
    msg = f'[PDF] app={app_label} pk={pk} file={filename} user={username} ip={ip} time={timestamp}'
    print(msg)
    logging.getLogger('user_actions').info(msg)
