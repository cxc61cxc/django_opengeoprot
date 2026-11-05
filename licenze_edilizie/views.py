import os
from django.conf import settings
from django.shortcuts import render, get_object_or_404
from django.http import Http404, HttpResponse
from django.contrib.auth.decorators import login_required
from pdf_utils import add_watermark_to_pdf, log_pdf_access
from .models import RegistroLicenzeEdilizie

PDF_BASE_DIR = os.path.join(settings.BASE_DIR, 'licenze_edilizie', 'pdf')

@login_required
def lista_registri(request):
    registri = RegistroLicenzeEdilizie.objects.all().order_by('periodo')
    return render(request, 'licenze_edilizie/lista.html', {'registri': registri})

@login_required
def download_pdf(request, pk):
    registro = get_object_or_404(RegistroLicenzeEdilizie, pk=pk)
    filename = os.path.basename(registro.filename)
    filepath = os.path.join(PDF_BASE_DIR, filename)
    if os.path.exists(filepath):
        log_pdf_access(request, filename, app_label='licenze_edilizie', pk=registro.pk)
        with open(filepath, 'rb') as fh:
            pdf_bytes = fh.read()
        pdf_bytes = add_watermark_to_pdf(pdf_bytes, user=request.user)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename=%s' % filename
        return response
    raise Http404("File non trovato")
