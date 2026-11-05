from django import forms 
from django.forms import ModelForm
from protocollo.models import Pratica, TipoPratica, Soggetto, Anaprat
from .models import *




class DateInput(forms.DateInput):
    input_type = 'date'


class ResidenteEditForm(forms.ModelForm):
    addr = forms.CharField(max_length=150)
    
    
    class Meta:
        model = Soggetto
        fields =( 'cognome','nome','comune_residenza','addr', 'data_nascita', 'comune_nascita', 'codice_fiscale' )

        widgets = {

            'cognome'            : forms.TextInput(attrs={'class':'form-control'}),
            'nome'              : forms.TextInput(attrs={'class':'form-control'}),
            'comune_residenza'  : forms.TextInput(attrs={'class':'form-control'}),
            'addr'              : forms.TextInput(attrs={'class':'form-control'}),
            'data_nascita'       : forms.DateInput(attrs={'required': False}),
            'comune_nascita'        : forms.TextInput(attrs={'required': False,'class':'form-control'}),
            'codice_fiscale'        : forms.TextInput(attrs={'required': False,'class':'form-control'}), 
            
            
        }


