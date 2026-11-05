from django import forms 
from django.forms import ModelForm
# from .models import Pratica, TipoPratica, Soggetto, Anaprat
from catasto.models import Particelle


class ParticellaEditForm(forms.ModelForm):
    foglio = forms.CharField(max_length=5)
    mappale = forms.CharField(max_length=5)
    
    

    class Meta:
        model = Particelle
        fields =( 'foglio','mappale')

        widgets = {

            'foglio'            : forms.TextInput(attrs={'class':'form-control'}),
            'mappale'           : forms.TextInput(attrs={'class':'form-control'}),             
        }