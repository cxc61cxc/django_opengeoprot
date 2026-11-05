from django import forms
from prg.widgets import DatePicker
from .models import *

class DateInput(forms.DateInput):
    input_type = 'date'


class ConvForm(forms.ModelForm):
    data_atto = forms.DateField(widget=DatePicker(), required=False)
    
    area        = forms.IntegerField(required=False)
    volume      = forms.IntegerField( required=False)
    edifici     = forms.IntegerField( required=False)
    ref_millesimi = forms.BooleanField(label='dividi',required=False)
    alloggi     = forms.IntegerField( required=False)
    durata      = forms.IntegerField( required=True)

    class Meta:
        model   = IstrConv
        fields  = ('ref_millesimi','millesimi','valore_residuo','tot_conv_rival','tot_conv','valore_dirsup','coeff_istat','valore_venale','coeff_istat',
                   'valore_perizia','tipo_diritto','notaio','data_atto','atto','conv_lire','cong_lire',
                   'conv_rival','cong_rival', 'area','volume','edifici','prop_acquisita','alloggi','durata','coeff_temp',
                   'crv','crv_uiu')
        


        widgets = {

            'notaio'    : forms.TextInput(attrs={'required': 'true','class':'form-control', 'autofocus': True}),
            'data_atto' : forms.DateInput(),
            'atto'      : forms.Textarea(attrs={'required': 'true','class':'form-control','rows':2, 'cols':30}),
            'conv_lire' : forms.TextInput(attrs={'required':'false','class':'form-control'}),  
            'cong_lire' : forms.TextInput(attrs={'required':'false','class':'form-control'}),
            'conv_rival' : forms.TextInput(attrs={'required':'false','class':'form-control'}),  
            'cong_rival' : forms.TextInput(attrs={'required':'false','class':'form-control'}),    
            'area'    : forms.TextInput(attrs={'required': 'false','class':'form-control', 'autofocus': True}),
            'volume'    : forms.TextInput(attrs={'required': 'false','class':'form-control', 'autofocus': True}),
            'edifici'    : forms.TextInput(attrs={'required': 'false','class':'form-control', 'autofocus': True}),
            'ref_millesimi'    : forms.CheckboxInput(attrs={'required': 'false', 'class':'form-check-input'}),
            'alloggi'    : forms.TextInput(attrs={'required': 'false','class':'form-control', 'autofocus': True}),
        }
    



class AccettazioneForm(forms.ModelForm):
    data_accettazione = forms.DateField(widget=DatePicker(), required=True)
    # annotazione = forms.Textarea(attrs={"rows":"2", "cols":"30"})
    prot_gen = forms.CharField(required=True)
    importo = forms.DecimalField(required=True)
    
    class Meta:
        model = AccettaImporto
        fields =('rateo','data_accettazione','annotazione', 'prot_gen', 'importo','iuv')
        
        widgets = {
            'data_accettazione' : forms.DateInput(),
            'annotazione'      : forms.Textarea(attrs={'class':'form-control','rows':2, 'cols':30}),
        }

class ScadenzeForm (forms.ModelForm):
    data_scadenza = forms.DateField(widget=DatePicker(), required=True)
    importo_rata = forms.DecimalField(required=True)
    data_pagamento = forms.DateField(widget=DatePicker(), required=False)
    importo_pagamento = forms.DecimalField(required=False)
    iuv = forms.CharField(required=False)
    

    class Meta:
        model = Scadenze
        fields =('data_scadenza', 'importo_rata', 'data_pagamento', 'importo_pagamento','iuv')
        
        widgets = {
            'data_scadenza' : forms.DateInput(),
            'data_pagamento' : forms.DateInput(),
        }



   