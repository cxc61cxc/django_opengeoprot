from django import forms
from prg.widgets import DatePicker
from ascensori.models import *

class DateInput(forms.DateInput):
    input_type = 'date'


# class MatricolaForm(forms.ModelForm):
#     matricola_date = forms.DateField(widget=DatePicker())
   
#     class Meta:
#         model   = Matricola
#         fields  = ('numero','matricola_date','description', 'matricola_comunicata')
        


#         widgets = {

#             # 'numero'           : forms.TextInput(attrs={'required': 'false','class':'form-control', 'autofocus': True}),
#             'matricola_date'             : forms.DateInput(),
#             'description'           : forms.Textarea(attrs={'required': 'true','class':'form-control','rows':2, 'cols':30}),
#             # 'importo_2'            : forms.TextInput(attrs={'required':'false','class':'form-control'}),   
#             # 'importo_3'            : forms.TextInput(attrs={'required':'false','class':'form-control'}),   
#             # 'importo_4'            : forms.TextInput(attrs={'required':'false','class':'form-control'}),   
 
#         }
#     def __init__(self, *args, **kwargs):
#         super(MatricolaForm, self).__init__(*args, **kwargs)
#         self.fields['numero'].required = False

# class MatricolaForm(forms.ModelForm):
#     matricola_date = forms.DateField(widget=DatePicker())

#     class Meta:
#         model = Matricola
#         fields = ('numero', 'matricola_date', 'description', 'matricola_comunicata')

#         widgets = {
#             'description': forms.Textarea(attrs={
#                 'required': 'true',
#                 'class': 'form-control',
#                 'rows': 2,
#                 'cols': 30
#             }),
#         }

#     def __init__(self, *args, **kwargs):
#         super(MatricolaForm, self).__init__(*args, **kwargs)
#         self.fields['numero'].required = False


# class MatricolaForm(forms.ModelForm):
#     matricola_date = forms.DateField(widget=DatePicker(), required=False)  # required=False per gestirlo manualmente

#     class Meta:
#         model = Matricola
#         fields = ('numero', 'matricola_date', 'description', 'matricola_comunicata')

#         widgets = {
#             'description': forms.Textarea(attrs={
#                 'class': 'form-control',
#                 'rows': 2,
#                 'cols': 30
#             }),
#         }

#     def __init__(self, *args, **kwargs):
#         super(MatricolaForm, self).__init__(*args, **kwargs)
#         self.fields['numero'].required = False
#         self.fields['description'].required = False
#         self.fields['matricola_comunicata'].required = False  # meglio esplicitarlo

#     def clean(self):
#         cleaned_data = super().clean()
#         numero = cleaned_data.get('numero')
#         matricola_date = cleaned_data.get('matricola_date')
#         matricola_comunicata = cleaned_data.get('matricola_comunicata')
#         matricola_assegnata = getattr(self.instance, 'matricola_assegnata', None)

#         # Se matricola_assegnata è vuoto, numero e matricola_date sono obbligatori
#         if not matricola_assegnata:
#             if not numero:
#                 self.add_error('numero', 'Il campo "numero" è obbligatorio se la matricola assegnata non è presente.')
#             if not matricola_date:
#                 self.add_error('matricola_date', 'Il campo "data di rilascio" è obbligatorio se la matricola assegnata non è presente.')

#         # Se matricola_assegnata è presente, numero e matricola_date possono essere vuoti solo se matricola_comunicata è valorizzato
#         else:
#             if (not numero or not matricola_date) and not matricola_comunicata:
#                 error_msg = 'Se il numero o la data di rilascio sono vuoti, il campo "matricola comunicata" deve essere compilato.'
#                 self.add_error('numero', error_msg)
#                 self.add_error('matricola_date', error_msg)

#         return cleaned_data



class MatricolaForm(forms.ModelForm):
    matricola_date = forms.DateField(widget=DatePicker(), required=False)

    class Meta:
        model = Matricola
        fields = ('numero', 'matricola_date', 'description', 'matricola_comunicata')
        widgets = {
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'cols': 30}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['numero'].required = False
        self.fields['description'].required = False

    def clean(self):
        cleaned_data = super().clean()
        numero = cleaned_data.get('numero')
        matricola_date = cleaned_data.get('matricola_date')
        matricola_comunicata = cleaned_data.get('matricola_comunicata')

        if not matricola_comunicata:
            # matricola_comunicata vuoto -> numero e matricola_date sono obbligatori
            if not numero:
                self.add_error('numero', 'Questo campo è obbligatorio se matricola_comunicata è vuoto.')
            if not matricola_date:
                self.add_error('matricola_date', 'Questo campo è obbligatorio se matricola_comunicata è vuoto.')





class ImpiantoForm(forms.ModelForm):
    # num_impianto = forms.CharField(max_length=220, required=True)
    note = forms.CharField(required=False,widget=forms.Textarea(attrs={"rows":"8", "col":15}))
    # azionamento = forms.CharField(required=False)
    # portata = forms.IntegerField(required=False)
    # corsa = forms.IntegerField(required=False)

   
    class Meta:
        model   = Impianto
        fields  = ('num_impianto','velocita','portata','corsa','fermate','azionamento','note')
        


        widgets = {

            # 'num_impianto'           : forms.TextInput(attrs={'required': 'true','class':'form-control', 'autofocus': True}),
            # 'matricola_date'             : forms.DateInput(),
            # 'note'                   : forms.Textarea(attrs={'required': 'true','class':'form-control','rows':2, 'cols':30}),
            # 'azionamento'            : forms.TextInput(attrs={'required':'false','class':'form-control'}),  
            # 'importo_2'            : forms.TextInput(attrs={'required':'false','class':'form-control'}),   
            # 'importo_3'            : forms.TextInput(attrs={'required':'false','class':'form-control'}),   
            # 'importo_4'            : forms.TextInput(attrs={'required':'false','class':'form-control'}),   
 
        }
    