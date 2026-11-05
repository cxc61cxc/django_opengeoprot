import logging
import tempfile
from pathlib import Path
from subprocess import CalledProcessError, TimeoutExpired

from django.http import HttpResponse
from django.shortcuts import render
from django.utils.text import slugify
from django.views.decorators.http import require_http_methods

from .forms import DocumentoForm
from .services import ensure_docx, replace_strikethrough_docx


logger = logging.getLogger(__name__)


def _output_filename(original_name: str) -> str:
    stem = Path(original_name).stem or "documento"
    safe_stem = slugify(stem) or "documento"
    return f"{safe_stem}_omissis.docx"


@require_http_methods(["GET", "POST"])
def upload_documento(request):
    if request.method == "POST":
        form = DocumentoForm(request.POST, request.FILES)

        if form.is_valid():
            uploaded = form.cleaned_data["file"]
            ext = Path(uploaded.name).suffix.lower()

            try:
                with tempfile.TemporaryDirectory() as tmpdir:
                    workdir = Path(tmpdir)

                    # Nome volutamente semplice, per evitare problemi
                    # con caratteri speciali nel nome originale.
                    input_path = workdir / f"upload{ext}"

                    with input_path.open("wb") as fh:
                        for chunk in uploaded.chunks():
                            fh.write(chunk)

                    # Se necessario converte in DOCX.
                    docx_path = ensure_docx(input_path, workdir)

                    # Genera il documento con gli omissis.
                    output_path = workdir / "output.docx"
                    replace_strikethrough_docx(docx_path, output_path)

                    data = output_path.read_bytes()

                response = HttpResponse(
                    data,
                    content_type=(
                        "application/vnd.openxmlformats-officedocument."
                        "wordprocessingml.document"
                    ),
                )

                response["Content-Disposition"] = (
                    f'attachment; filename="{_output_filename(uploaded.name)}"'
                )

                return response

            except FileNotFoundError:
                logger.exception("LibreOffice non trovato")
                form.add_error(
                    None,
                    "LibreOffice non è stato trovato. "
                    "Verifica l'installazione oppure configura "
                    "OMISSIS_LIBREOFFICE_BIN nelle settings.",
                )

            except CalledProcessError:
                logger.exception("Errore durante la conversione LibreOffice")
                form.add_error(
                    None,
                    "Conversione del documento non riuscita. "
                    "Verifica che LibreOffice sia installato correttamente.",
                )

            except TimeoutExpired:
                logger.exception("Timeout durante la conversione LibreOffice")
                form.add_error(
                    None,
                    "La conversione del documento è andata in timeout.",
                )

            except Exception:
                logger.exception("Errore durante l'elaborazione del documento")
                form.add_error(
                    None,
                    "Errore durante l'elaborazione del documento.",
                )

    else:
        form = DocumentoForm()

    return render(
        request,
        "omissis_documents/upload.html",
        {
            "form": form,
        },
    )