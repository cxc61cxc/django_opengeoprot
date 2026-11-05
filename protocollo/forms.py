from django.contrib.admin.widgets import AutocompleteSelect
from django import forms 
from prg.widgets import DatePicker
from datetime import date
# from django.forms import ModelForm
from .models import Pratica, TipoPratica, Soggetto, Anaprat,Particella, Cataprat,Documento, Diario, TipoSoggetto
from struttura_ente.models import Settore, StoricoServizio, StoricoAttivitaUO
# from . import models
from viario.models import Civici
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.gis.geos import Point




class PraticaForm(forms.ModelForm):
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user and not (user.is_superuser or user.is_staff):
            from protocollo.views import get_filtered_tipo_pratica_list
            self.fields['tipo_pratica'].queryset = get_filtered_tipo_pratica_list(user, only_opengeoprot=True)
        else:
            self.fields['tipo_pratica'].queryset = TipoPratica.objects.all().order_by('name')
        
# Imposta valori iniziali per i campi in caso di nuova istanza
        if not self.instance.pk: # Solo per nuove istanze (non in fase di modifica)
            self.fields['data_prot_gen'].initial = date.today()
            self.fields['stato'].initial = 'i' # Assumendo 'i' (in corso) come stato iniziale predefinito
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user and instance.pk:  # Solo se è una modifica, non una creazione
            instance.modified_by = self.user
        if commit:
            instance.save()
        return instance

    data_prot_gen = forms.DateField(
        widget=DatePicker(), 
        required=True, 
        label="Data Protocollo")

    lat = forms.CharField(widget=forms.HiddenInput(), required=False)
    lng = forms.CharField(widget=forms.HiddenInput(), required=False)
    street = forms.ModelChoiceField(queryset=Civici.objects.all(), required=False, label="Indirizzo")
    annotazioni = forms.CharField(required=False,widget=forms.Textarea(attrs={"rows":"5", "col":15}))
    oggetto = forms.CharField(widget=forms.Textarea(attrs={"rows":"5", "col":15}))

    # forms.DateInput(),

    housenumber = forms.CharField(required=False)
    code_p = forms.IntegerField(required=False)
    sub_code = forms.IntegerField(required=False)
    classe = forms.IntegerField(required=False)
    # data_prot_gen = forms.DateField(widget=DatePicker()) 

    # def __init__(self,*args,**kwargs):
    #     super(PraticaForm, self).__init__(*args,**kwargs)
    #     self.fields['street'].label = "Indirizzo"
    
    class Meta:
        model   = Pratica
        
        fields  = ('stato','tipo_pratica','prot_gen','data_prot_gen', 'street', 'housenumber','oggetto','annotazioni','code_p','sub_code','classe')

        widgets = {

            'prot_gen'              : forms.TextInput(attrs={'required': 'true','class':'form-control', 'autofocus': True}),
            # 'data_prot_gen'         : forms.DateInput(),
            'tipo_pratica'          : forms.Select(attrs={'required': 'true','class':'form-control'}), 

            # 'street'                : AutocompleteSelect(Pratica._meta.get_field('street').remote_field(),
            #                                             admin.site,
                                                        # attrs={'placeholder':'inserisci caratteri di ricerca....'},
                                                        # ) 
            'street'                : forms.Select (attrs={'required': 'false','class':'form-control'}),
            # 'street'                : CiviciWidget,
            'housenumber'           : forms.TextInput (attrs={'required': 'false','class':'form-control', 'autofocus': True}),
            # 'oggetto'               : forms.Textarea (attrs={'required': 'false','class':'form-control', 'autofocus': True}),
            # 'annotazioni'               : forms.Textarea (attrs={'required': 'false','class':'form-control', 'autofocus': True}),
        }

class StatoForm(forms.ModelForm):
    class Meta:
        model   = Pratica
        
        fields  = ('stato',)

class PraticaEditForm(forms.ModelForm):

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user and not (user.is_superuser or user.is_staff):
            from protocollo.views import get_filtered_tipo_pratica_list
            self.fields['tipo_pratica'].queryset = get_filtered_tipo_pratica_list(user, only_opengeoprot=True)
        else:
            self.fields['tipo_pratica'].queryset = TipoPratica.objects.all().order_by('name')

    data_prot_gen = forms.DateField(widget=DatePicker(), label="Data Protocollo") 
    street = forms.ModelChoiceField(queryset=Civici.objects.all(), required=False, label="Indirizzo")
    annotazioni = forms.CharField(required=False,widget=forms.Textarea(attrs={"rows":"3", "col":15}))
    oggetto = forms.CharField(widget=forms.Textarea(attrs={"rows":"3", "col":15}))

    housenumber = forms.CharField(required=False)
    code_p = forms.IntegerField(required=False)
    sub_code = forms.IntegerField(required=False)
    classe = forms.IntegerField(required=False)
    # def __init__(self,*args,**kwargs):
    #     super(PraticaForm, self).__init__(*args,**kwargs)
    #     self.fields['street'].label = "Indirizzo"

    class Meta:
        model   = Pratica
        
        fields  = ('tipo_pratica','prot_gen','data_prot_gen','stato', 'code_p', 'sub_code','street', 'housenumber','oggetto','annotazioni','classe')

        widgets = {

            'prot_gen'              : forms.TextInput(attrs={'required': 'true','class':'form-control', 'autofocus': True}),
            'data_prot_gen'         : forms.DateInput(),
            'tipo_pratica'          : forms.Select(attrs={'required': 'true','class':'form-control'}), 

            # 'street'                : AutocompleteSelect(Pratica._meta.get_field('street').remote_field(),
            #                                             admin.site,
                                                        # attrs={'placeholder':'inserisci caratteri di ricerca....'},
                                                        # ) 
            'street'                : forms.Select (attrs={'required': 'false','class':'form-control'}),
            # 'street'                : CiviciWidget,
            'housenumber'           : forms.TextInput (attrs={'required': 'false','class':'form-control', 'autofocus': True}),
            # 'oggetto'               : forms.Textarea (attrs={'required': 'false','class':'form-control', 'autofocus': True}),
            # 'annotazioni'               : forms.Textarea (attrs={'required': 'false','class':'form-control', 'autofocus': True}),
        }

    
class PraticaSearchForm(forms.ModelForm):
    data_prot_gen = forms.DateField(widget=DatePicker())

    class Meta: 
        model = Pratica
        fields = ('prot_gen','data_prot_gen','tipo_pratica',)


class UnifiedSearchForm(forms.Form):
    stato = forms.ChoiceField(choices=[('', 'Tutti')] + Pratica._meta.get_field('stato').choices, required=False)
    prot_gen = forms.CharField(required=False, label="N. Protocollo")
    anno = forms.IntegerField(required=False, label="Anno")
    oggetto = forms.CharField(required=False, label="Oggetto")
    atto = forms.CharField(required=False, label="Atto")
    istruttoria = forms.CharField(required=False, label="Istruttoria")
    tecnico = forms.CharField(required=False, label="Tecnico")
    street = forms.ModelChoiceField(queryset=Civici.objects.all(), required=False, label="Indirizzo")
    civico = forms.CharField(required=False, label="Civico")
    tp = forms.ModelChoiceField(queryset=TipoPratica.objects.none(), required=False, label="Tipo Pratica")
    
    cognome = forms.CharField(required=False, label="Cognome")
    nome = forms.CharField(required=False, label="Nome")
    
    foglio = forms.CharField(required=False, label="Foglio")
    mappale = forms.CharField(required=False, label="Mappale")
    
    matricola = forms.CharField(required=False, label="Matricola")
    cdu = forms.CharField(required=False, label="N. CDU")
    impianto = forms.CharField(required=False, label="N. Impianto")

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            if user.is_superuser or user.is_staff:
                self.fields['tp'].queryset = TipoPratica.objects.all().order_by('name')
            else:
                from protocollo.views import get_filtered_tipo_pratica_list
                self.fields['tp'].queryset = get_filtered_tipo_pratica_list(user, only_opengeoprot=True)
        
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'form-control form-control-sm',
                'placeholder': field.label or field_name.capitalize()
            })



class AddSoggettoPraticaForm(forms.ModelForm):
    
    class Meta:
        model = Anaprat
        fields = ( 'soggetto','pratica','tipo')
        
        widgets = {

            'tipo'            : forms.TextInput(attrs={'class':'form-control'}),   
        }





class SoggettoForm(forms.ModelForm):
    data_nascita = forms.DateField(widget=DatePicker(), required=False)

    
    nome = forms.CharField(required=False)
    cellulare = forms.CharField(required=False)
    telefono = forms.CharField(required=False)
    fax = forms.CharField(required=False)

    email = forms.EmailField(
        label = "Email",
        max_length = 150,
        required = False,
    )
    pec = forms.EmailField(
        label = "PEC",
        max_length = 150,
        required = False,
    )
    addr = forms.CharField(label='Indirizzo residenza',required = False,)
    addr_sede = forms.CharField(label='Indirizzo Sede',required = False,)

    class Meta:
        model = Soggetto
        fields =( 'cognome','nome','comune_residenza','addr','addr_sede', 'data_nascita', 'comune_nascita', 'codice_fiscale','email','pec','cellulare','telefono','fax' )

        widgets = {
            'cognome'               : forms.TextInput(attrs={'autofocus':'True','class':'form-control'}),
            'nome'                  : forms.TextInput(attrs={'class':'form-control', 'required':False}),
            'comune_residenza'      : forms.TextInput(attrs={'class':'form-control'}),
            'addr'                  : forms.TextInput(attrs={'class':'form-control'}),
            'addr_sede'             : forms.TextInput(attrs={'class':'form-control'}),
            'data_nascita'          : forms.DateInput(),
            'comune_nascita'        : forms.TextInput(attrs={'class':'form-control'}),
            'codice_fiscale'        : forms.TextInput(attrs={'class':'form-control'}),
            'email'                 : forms.EmailInput(attrs={'class':'form-control'}),
            'pec'                   : forms.EmailInput(attrs={'class':'form-control'}),
            'cellulare'             : forms.TextInput(attrs={'class':'form-control'}),
            'telefono'              : forms.TextInput(attrs={'class':'form-control'}),
            'fax'                   : forms.TextInput(attrs={'class':'form-control'}),   
        }




class AddParticellaPraticaForm(forms.ModelForm):

    class Meta:
        model = Cataprat
        fields = ( 'particella','pratica','subalterno')
        
        widgets = {

            'subalterno'            : forms.TextInput(attrs={'class':'form-control'}),
           
            
        }

        
class AddParticellaForm(forms.ModelForm):
    # geom = forms.CharField(widget=forms.HiddenInput())
    class Meta:
        model = Particella
        fields =('foglio','mappale','mpoly')

        widgets = {

            'foglio'            : forms.TextInput(attrs={'class':'form-control'}),
            'mappale'           : forms.TextInput(attrs={'class':'form-control'}),
            'mpoly'              : forms.HiddenInput(),
            # widgets = {'tag': forms.HiddenInput()}
        }



################ upload

class UploadFileForm(forms.ModelForm):
    document = forms.FileField(label="Documento")
    data_prot=forms.DateField(widget=DatePicker(), required=False)
    prot=forms.CharField(max_length=20, required=False)
    class Meta:
        model = Documento
        fields =['posta','prot', 'data_prot','name','document']
        
        widgets = {

            'document'            : forms.FileInput(attrs={'class':'form-control'}),
            'name'              : forms.Textarea (attrs={'required': 'false','class':'form-control', 'autofocus': True}),
            
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk: # solo se è un nuovo oggetto
            self.fields['data_prot'].initial = date.today()

class TipoPraticaForm(forms.ModelForm):
    description = forms.CharField(widget=forms.Textarea)
    class Meta:
        model = TipoPratica
        fields =('name','description','settore','servizio','u_o','visibile_solo_uo','uo_visibili')

        widgets = {
            'name'          : forms.TextInput(attrs={'autofocus': True, 'class':'form-control'}),
            'visibile_solo_uo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'uo_visibili': forms.SelectMultiple(attrs={'class': 'form-control', 'size': '5'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qs_servizio = StoricoServizio.objects.filter(data_fine__isnull=True)
        if self.instance.pk and self.instance.settore:
            qs_servizio = qs_servizio.filter(settore_storico=self.instance.settore.versione_vigente)
        self.fields['servizio'].queryset = qs_servizio
        qs_uo = StoricoAttivitaUO.objects.filter(data_fine__isnull=True)
        if self.instance.pk and self.instance.servizio:
            qs_uo = qs_uo.filter(servizio_storico=self.instance.servizio)
        self.fields['u_o'].queryset = qs_uo
        qs_uo_visibili = StoricoAttivitaUO.objects.filter(data_fine__isnull=True)
        self.fields['uo_visibili'].queryset = qs_uo_visibili
        self.fields['settore'].label_from_instance = lambda obj: obj.codice


class DiarioForm(forms.ModelForm):
    description = forms.CharField(widget=forms.Textarea(attrs={"rows":"5", 'autofocus':True}))
    class Meta:
        model = Diario
        fields =('description',)




        


        
        