from django import forms
from prg.widgets import DatePicker
from .models import *

class DateInput(forms.DateInput):
    input_type = 'date'
    
class PcarForm(forms.ModelForm):
    pc_number = forms.IntegerField(required=False)
    pc_date = forms.DateField(widget=DatePicker(), required=False)
    largh=forms.DecimalField(required=False)
    prof=forms.DecimalField(required=False)
    area=forms.DecimalField(required=False)
    description=forms.Textarea()
   
    class Meta:
        model = Passocarraio
        fields = ('pc_number', 'pc_date','uso','tipo','largh','prof','area','description')
        labels = {
            
        }

        widgets = {
            'pc_number'        : forms.TextInput(attrs={'required': 'true','class':'form-control', 'autofocus': True}),
            'pc_date'          : forms.DateInput(attrs={'required': 'true'}),
            'uso'               : forms.Select(attrs={'class':'form-control'}),
            'tipo'               : forms.Select(attrs={'class':'form-control'}),
            'description'           : forms.Textarea(attrs={'class':'form-control','rows':2, 'cols':30}),
            
        }