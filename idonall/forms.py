from django import forms
from prg.widgets import DatePicker
from .models import *

class DateInput(forms.DateInput):
    input_type = 'date'


class IstruttoriaForm(forms.ModelForm):
    
    catasto = forms.BooleanField(
        required=False,
        label='Visura e/o planimetria'
    )
    
    doc_prop = forms.BooleanField(
        required=False,
        label='Documento proprietario'
    )
    # abitabilita = forms.BooleanField(
    #     required=False,
    #     label='Abitabilita\''
    # )
    # rel_tec = forms.BooleanField(
    #     required=False,
    #     label='Relazione tecnico abilitato'
    # )
    conf_imp = forms.BooleanField(
        required=False,
        label='conformita\' impianto'
    )
    caldaia = forms.BooleanField(
        required=False,
        label='revisione caldaia'
    )
    ante1975 = forms.BooleanField(
        required=False,
        label='ante 1975'
    )

    mq = forms.FloatField(
        required=False,
        label='Mq'
    )

    vani = forms.FloatField(
        required=False,
        label='Vani'
    )
    nota_relazione = forms.CharField(
        widget=forms.Textarea(attrs={"rows": "5", "col": 15}),
        required=False
        )
    nota_abitabilita = forms.CharField(
        widget=forms.Textarea(attrs={"rows": "5", "col": 15}),
        required=False
        )
    nota_prop = forms.CharField(
        widget=forms.Textarea(attrs={"rows": "5", "col": 15}),
        required=False
        )
   
   
    num_adulti = forms.IntegerField(
        required=False,
        label = 'num. adulti'
    )
    num_minori = forms.IntegerField(
        required = False,
        label = 'num. minori'
    )
    class Meta:
        model   = Istruttoria
        fields  = ('catasto', 'doc_prop', 'conf_imp', 'caldaia', 'ante1975', 'mq', 'vani', 'nota_relazione', 'nota_abitabilita', 'nota_prop', 'num_adulti', 'num_minori', 'tipo_richiedente_idonall', 'tipo_richiesta')
        exclude = ['pratica', 'user']
       
        tipo_richiedente_idonall_choice = [
            ('Proprietario', 'Proprietario'),
            ('Conduttore', 'Conduttore'),
            ('Ospite', 'Ospite'),
            ]

        tipo_richiesta_choice = [
            ('Attestazione', 'Attestazione'),
            ('Cointestazione', 'Cointestazione'),
            ('Duplicato', 'Duplicato'),
            ('Rinnovo', 'Rinnovo'),
            ]
        widgets = {
            'tipo_richiedente_idonall': forms.Select(choices=tipo_richiedente_idonall_choice),
            'tipo_richiesta': forms.Select(choices=tipo_richiesta_choice)
        }
    







class IdonallForm(forms.ModelForm):
    
    
    idonall_date = forms.DateField(
        widget=DatePicker(),
        required=True,
        )
    descrizione = forms.CharField(
        required=False,
        label='',  # Non mostra la label
        widget=forms.Textarea(attrs={'rows': 4, 'cols': 50})  # Personalizza il widget se vuoi
        )
    

    class Meta:
        model   = Idonall
        fields  = '__all__'
        exclude = ['istruttoria', 'user']
        labels = {
            'idonall_number': '',
            # 'descrizione':('')
        }
        widgets = {

            'idonall_number'           : forms.TextInput(attrs={'required': 'True','class':'form-control', 'autofocus': True}),
            'idonall_date'             : forms.DateInput(),
            # 'descrizione'           : forms.Textarea(attrs={'required': 'False','class':'form-control','rows':2, 'cols':90}),
        }