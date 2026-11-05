from django import forms
from .models import ImpFot
from prg.widgets import DatePicker
class DateInput(forms.DateInput):
    input_type = 'date'

class ImpFotForm(forms.ModelForm):
    pn = forms.IntegerField(
        label = ' Potenza nominale',
        required= False
    )
    pa = forms.IntegerField(
        label = ' Potenza accumulata',
        required= False
    )
    pi = forms.IntegerField(
        label = ' Potenza immessa',
        required= False
    )
    pod = forms.CharField(
        label = 'POD',
        required=False
        )
   
   
    code_e = forms.IntegerField(
        required=False,
        label = 'codice impianto'
    )
    annotazione = forms.CharField(
        widget=forms.Textarea(attrs={"rows": "5", "col": 15}),
        required=False
        )
    prot_pe = forms.CharField(
        required=False,
        label= 'Protocollo pratica edilizia'
    )

    
    data_prot_pe = forms.DateField(
        widget=DatePicker(),
        required=False,
        label= 'Data Protocollo pratica edilizia'
        )
    
    class Meta:
        model = ImpFot
        fields = [
             'pod', 'code_e', 'pn', 'pa', 'pi',
            'mod1', 'mod2', 'allp', 'prot_pe', 'data_prot_pe', 'annotazione'
        ]
        widgets = {
            'data_prot_pe': forms.DateInput(attrs={'type': 'date'}),
    
        }

    def clean(self):
        cleaned_data = super().clean()
        mod1 = cleaned_data.get('mod1')
        mod2 = cleaned_data.get('mod2')
        allp = cleaned_data.get('allp')

        # Se mod1 o mod2 sono True, assicurarsi che allp sia False
        if (mod1 or mod2) and allp:
            raise forms.ValidationError("Se mod1 o mod2 sono True, 'allp' deve essere False.")

        # Se allp è True, mod1 e mod2 devono essere False
        if allp and (mod1 or mod2):
            raise forms.ValidationError("Se 'allp' è True, mod1 e mod2 devono essere False.")

        return cleaned_data