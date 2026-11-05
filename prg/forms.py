from django import forms
from prg.widgets import DatePicker
from .models import *

class DateInput(forms.DateInput):
    input_type = 'date'


class PianoForm(forms.ModelForm):
    piano = forms.TextInput()
    data_atto = forms.DateField(widget=DatePicker(),required=False)
    data_in = forms.DateField(widget=DatePicker(),required=False)
    data_out = forms.DateField(widget=DatePicker(),required=False)
   
    class Meta:
        model   = Piano
        fields  = ('name','description','tipo_provvedimento','atto','data_atto','data_in','data_out', 'ordine')
        labels = {
            'name': ('Nome del Piano'),
            'description':('Descrizione'),
            'tipo_provvedimento':('Provvedimento'),
            'data_atto':('Data Atto'),
            'data_in' : ('Data Efficacia'),
            'data_out':('Data Cessazione')
        }



        widgets = {

            'name'              : forms.TextInput(attrs={'required': 'true','class':'form-control', 'autofocus': True}),
            'description'       : forms.Textarea(attrs={'required': 'true','class':'form-control'}),
            'tipo_provvedimento': forms.TextInput(attrs={'required': 'false','class':'form-control'}),
            'data_atto'         : forms.DateInput(attrs={'required': 'false'}),
            'data_in'           : forms.DateInput(attrs={'required': 'false'}),
            'data_out'          : forms.DateInput(attrs={'required': 'false'}),
            'ordine'            : forms.TextInput(attrs={'required':'false','class':'form-control'}),   
        }


class DestinazioneForm(forms.ModelForm):

    class Meta:
        model = Destinazione
        fields =['name','description','norma']
        labels = {
            'name': ('Nome'),
            'description':('Descrizione')
        }

        widgets = {

            'name'              : forms.TextInput(attrs={'required': 'true','class':'form-control', 'autofocus': True}),
            'description'       : forms.Textarea(attrs={'required': 'true','class':'form-control'}),
            'norma': forms.TextInput(attrs={'required': 'false','class':'form-control'}),
              
        }


# motivo della richiesta del cdu


class CduForm(forms.ModelForm):
    cdu_date = forms.DateField(widget=DatePicker(), required=True)
    data_riferimento = forms.DateField(widget=DatePicker(), required=True)

    class Meta:
        model = Cerdesurb
        fields = ('cdu_number', 'cdu_date', 'uso','data_riferimento')
        

        widgets = {
            # 'cdu_number'        : forms.TextInput(attrs={'required': 'true','class':'form-control', 'autofocus': True}),
            # 'cdu_date'          : forms.DateInput(attrs={'required': 'true'}),
            'uso'               : forms.Select(attrs={'class':'form-control'}),
            'data_riferimento'  : forms.DateInput(attrs={'required': 'true'}), 

        }


class IstruttoriaForm(forms.ModelForm):
   
    class Meta:
        model = Istruttoria
        fields = ('destinazione', 'parte')




class MarcaForm(forms.ModelForm):
    data_iuv = forms.DateField(widget=DatePicker(), required=False)
    data_marca = forms.DateField(widget=DatePicker(), required=False)
    class Meta:
        model = Marca
        fields = ['iuv', 'data_iuv', 'marca', 'data_marca']
        widgets = {
            # 'data_iuv': forms.DateInput(attrs={'type': 'date'}),
            # 'data_marca': forms.DateInput(attrs={'type': 'date'}),
            'data_iuv' : forms.DateInput(attrs={'required': 'false'}),
            'data_marca' : forms.DateInput(attrs={'required': 'false'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Rendi tutti i campi non obbligatori
        self.fields['iuv'].required = False
        self.fields['data_iuv'].required = False
        self.fields['marca'].required = False
        self.fields['data_marca'].required = False

    def clean_data_marca(self):
        data_marca = self.cleaned_data.get('data_marca')
        if data_marca == '':
            return None
        return data_marca

    def clean(self):
        cleaned_data = super().clean()
        iuv = cleaned_data.get('iuv')
        data_iuv = cleaned_data.get('data_iuv')
        marca = cleaned_data.get('marca')
        data_marca = cleaned_data.get('data_marca')

        # Verifica che almeno una coppia di campi sia riempita
        if not ((iuv and data_iuv) or (marca and data_marca)):
            raise forms.ValidationError(
                "Devi compilare almeno una coppia di campi: 'iuv e data_iuv' oppure 'marca e data_marca'."
            )

        return cleaned_data