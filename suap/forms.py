from django import forms
from prg.widgets import DatePicker
from .models import *

class DateInput(forms.DateInput):
    input_type = 'date'


class PauForm(forms.ModelForm):
    pau_date = forms.DateField(widget=DatePicker())
   
    class Meta:
        model   = Pau
        fields  = ('pau_number','pau_date','description','importo_1','importo_2','importo_3','importo_4')
        


        widgets = {

            'pau_number'           : forms.TextInput(attrs={'required': 'true','class':'form-control', 'autofocus': True}),
            'pau_date'             : forms.DateInput(),
            'description'          : forms.Textarea(attrs={'required': 'true','class':'form-control','rows':2, 'cols':30}),
            'importo_1'            : forms.TextInput(attrs={'required':'false','class':'form-control'}),  
            'importo_2'            : forms.TextInput(attrs={'required':'false','class':'form-control'}),   
            'importo_3'            : forms.TextInput(attrs={'required':'false','class':'form-control'}),   
            'importo_4'            : forms.TextInput(attrs={'required':'false','class':'form-control'}),   
 
        }
