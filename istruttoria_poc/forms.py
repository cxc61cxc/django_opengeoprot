from django import forms
from django.utils import timezone

from .models import Istruttoria, IstrComm, IstrCons


class BaseIstrForm(forms.ModelForm):
    """Form comune: testo obbligatorio e data con default a oggi."""

    campo_data = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['testo'].required = True
        self.fields['testo'].widget.attrs['autofocus'] = True

        instance = kwargs.get('instance') or getattr(self, 'instance', None)
        if instance is not None and not getattr(instance, 'data_val', None):
            self.fields[self.campo_data].initial = timezone.now().date()

    class Meta:
        widgets = {
            'testo': forms.Textarea(attrs={'class': 'form-control', 'rows': 8}),
        }
        help_texts = {
            'testo': 'Testo obbligatorio. Per annullare il contenuto usare il pulsante Elimina.',
        }

    @property
    def data_val_field(self):
        """Campo data esposto con un nome stabile nei template."""
        return self[self.campo_data]

    def clean_testo(self):
        testo = (self.cleaned_data.get('testo') or '').strip()
        if not testo:
            raise forms.ValidationError('Inserire il testo.')
        return testo


class IstruttoriaForm(BaseIstrForm):
    campo_data = 'data_istr_poc'

    class Meta(BaseIstrForm.Meta):
        model = Istruttoria
        fields = ['testo', 'data_istr_poc']
        widgets = {
            **BaseIstrForm.Meta.widgets,
            'data_istr_poc': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
        }


class IstrCommForm(BaseIstrForm):
    campo_data = 'data_commissione'

    class Meta(BaseIstrForm.Meta):
        model = IstrComm
        fields = ['testo', 'data_commissione']
        widgets = {
            **BaseIstrForm.Meta.widgets,
            'data_commissione': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
        }


class IstrConsForm(BaseIstrForm):
    campo_data = 'data_consiglio'

    class Meta(BaseIstrForm.Meta):
        model = IstrCons
        fields = ['testo', 'data_consiglio']
        widgets = {
            **BaseIstrForm.Meta.widgets,
            'data_consiglio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
        }
