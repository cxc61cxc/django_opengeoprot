from django import forms
from prg.widgets import DatePicker
from .models import *

class DateInput(forms.DateInput):
    input_type = 'date'



class CommissioneForm(forms.ModelForm):
    commissione_number = forms.CharField(label ="Numero",max_length=30, required=True)
    commissione_date = forms.DateField(label="Data",widget=DatePicker(), required=True)
    parere = forms.CharField(label="Parere",required=False, widget=forms.Textarea(attrs={"rows":"5", "col":"75"}))
    parere_choice = [
       ('Favorevole', 'Favorevole'),
       ('Contrario', 'Contrario'),
       ('Favorevole a condizione','Favorevole a condizione'),
       ('Richiesta integrazioni','Richiesta integrazioni')
       ]
    parere_sintetico = forms.ChoiceField(
        widget=forms.RadioSelect,
        choices=parere_choice, 
    )
    # data_riferimento = forms.DateField(widget=DatePicker())

    class Meta:
        model = Commissione
        fields = ('commissione_number', 'commissione_date','parere','parere_sintetico', 'tipo_paesaggio')
        

        widgets = {
            'commissione_number'        : forms.TextInput(attrs={'required': 'true','class':'form-control', 'autofocus': True}),
            'commissione_date'          : forms.DateInput(attrs={'required': 'true'}),
            # 'parere'                    : forms.Textarea(attrs={'class':'form-control', 'rows':6, 'cols':75}),
            'tipo_paesaggio'            : forms.Select(attrs={'class':'form-control', 'required':'true'}),  
            # 'data_riferimento'  : forms.DateInput(attrs={'required': 'true'}), 
        }