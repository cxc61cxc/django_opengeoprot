from pathlib import Path

from django import forms
from django.conf import settings


class DocumentoForm(forms.Form):
    file = forms.FileField(
        label="Documento da elaborare",
        help_text="Formati supportati: .docx, .doc, .odt",
    )

    def clean_file(self):
        uploaded = self.cleaned_data["file"]

        allowed_extensions = set(
            getattr(
                settings,
                "OMISSIS_ALLOWED_EXTENSIONS",
                (".docx", ".doc", ".odt"),
            )
        )

        max_mb = getattr(settings, "OMISSIS_MAX_UPLOAD_MB", 20) or 20

        ext = Path(uploaded.name).suffix.lower()

        if ext not in allowed_extensions:
            raise forms.ValidationError(
                "Formato non supportato. Carica un file .docx, .doc oppure .odt."
            )

        if uploaded.size > max_mb * 1024 * 1024:
            raise forms.ValidationError(
                f"Il file è troppo grande. Dimensione massima: {max_mb} MB."
            )

        return uploaded