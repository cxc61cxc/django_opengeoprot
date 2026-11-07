from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test


from coop.models import IstrConv,AccettaImporto, Scadenze
from protocollo.models import *
# Create your views here.
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Avg, Max
from django.db.models import Count
from dal import autocomplete
from .forms import *

from django.shortcuts import (get_object_or_404,
                              render,
                              HttpResponseRedirect,
                              redirect)

import datetime
from decimal import Decimal

from num2words import num2words

def is_editor_or_admin(user):
    return user.is_superuser or user.groups.filter(name__in=['editor_settore_6', 'editor_suap']).exists()


@login_required
@user_passes_test(lambda u: u.groups.filter(name__in=['editor_settore_6', 'editor_settore_1', 'user_settore_6', 'user_settore_1']).count() == 1, login_url='home:index')

# @user_passes_test(lambda u: u.groups.filter(name__in=['editor_settore_6', 'editor_settore_1', 'user_settore_6', 'user_settore_1']).count() == 1, login_url='home')
#   aggiunge una IDONEITA legata alla pratica 

def ConvAddView(request, pk):
    is_editor = request.user.groups.filter(name__in=['editor_settore_6', 'editor_settore_1', 'user_settore_6', 'user_settore_1']).exists()
    print('gruppo',is_editor)
    submitted = False
    richiedente=[]
    
    print('aggiunge i dati della convenzione',pk)
    
    try:
        pratica = Pratica.objects.get(id=pk)
    except Pratica.DoesNotExist:
        messages.error(request, f"Pratica con ID {pk} non trovata.")
        return redirect('protocollo:search_protocollo_url')
    
    # Crea o recupera la convenzione per questa pratica
    pratica_obj, created = IstrConv.objects.get_or_create(pratica=pratica)
    if created:
        print(f'Creata nuova convenzione per pratica {pk}')
    
    from dateutil.relativedelta import relativedelta
    data_istat = pratica.data_prot_gen - relativedelta(months=1)
    print('data istat',data_istat)
    tipo=pratica.tipo_pratica_id

    anaprat = Anaprat.objects.filter(pratica_id=pk)
    for s in anaprat:
        soggetti={}
        sogg = Soggetto.objects.get(id=s.soggetto_id)
        soggetti['id_anaprat']=s.id
        soggetti['cognome']=sogg.cognome
        soggetti['nome']=sogg.nome

        richiedente.append(soggetti)
        print (richiedente)
    print (tipo,'tipo_pratica',pratica.tipo_pratica)
    if tipo == 35: # esegue se la pratica è id=35 name = coop    
        if request.method == "POST":

            

            form = ConvForm(request.POST, instance=pratica_obj)
            if form.is_valid():
                obj=form.save(commit=False)
            # rivaluto in base al coefficiente istat alla data di rivalutazione ( inizialmente maggio 2024)
            # converto il valore in euro ed applico il coefficiente di rivalutazione
                print('conv_lire', obj.conv_lire)
            if obj.conv_lire:
                conv_lire_euro=round(obj.conv_lire/Decimal(1936.27),2)
            else:
                
                conv_lire_euro = 0
            
            

            # if obj.cong_lire:
            #     cong_lire_euro=round(obj.cong_lire/Decimal(1936.27),2)
            # else:
            #     cong_lire_euro = 0
            # print('impotro convenzione', cong_lire_euro)
            # obj.tot_conv = obj.cong_lire + obj.conv_lire
                   
            obj.conv_rival = conv_lire_euro * Decimal(obj.coeff_istat)
            obj.cong_rival = obj.cong_rival

            
            # else :
            #     obj.tot_conv = 0
            #     obj.conv_rival = 0
            #     obj.cong_rival = 0
                
            obj.tot_conv_rival = obj.conv_rival + obj.cong_rival
            print('rivaluta',obj.tot_conv_rival)

            # calcolo il valore venale
            obj.valore_venale = round(obj.valore_perizia * Decimal(0.60) * Decimal(obj.area),2)
            print('valore venale',obj.valore_venale)

            obj.valore_residuo = obj.valore_venale - obj.tot_conv_rival
                

            print('residuo',obj.valore_residuo)
            # valore relativo al diritto di superficie in funzione dei millesimi

            obj.valore_dirsup = (obj.valore_residuo * obj.millesimi) / 1000

            # se la convenzione riguarda l'eliminazione del vincolo di cessione
            # calcolo il coefficiente temporale coeff_temp
            # Calcola gli anni trascorsi
            oggi = datetime.date.today()
            anni = oggi.year - obj.data_atto.year - ((oggi.month, oggi.day) < (obj.data_atto.month, obj.data_atto.day))
            print('anni',anni)

                # oggi = datetime.date.today()
                # # coeff_temp = durata 
            if obj.durata:
                obj.coeff_temp = (obj.durata - anni)/obj.durata
            else:
                obj.coeff_temp = 0       
            obj.crv = obj.valore_residuo * Decimal(obj.coeff_temp) * Decimal(0.50) * Decimal(0.50)
            obj.crv_uiu = (obj.crv * obj.millesimi) / 1000
            obj.save()
                    
            return redirect('protocollo:pratica_detail_url' ,pk)
        # else:
        #          print('6666dsgsdgksld8sd7')
                    
        else:
            form = ConvForm(instance=pratica_obj)
            if 'submitted' in request.GET:
                submitted = True
                print('77tdg554dll')

            return render(request,'coop/add.html',{'is_editor':is_editor,'form':form,'pratica':pratica,'pk':pk, 'richiedente':richiedente})
    else :
        print('non arriva nessun dato')
        pass





@login_required
# @user_passes_test(lambda u: u.groups.filter(name__in=['editor_settore_6', 'editor_settore_1', 'user_settore_6', 'user_settore_1']).count() == 1, login_url='home:index')
@user_passes_test(lambda u: u.groups.filter(name__in=['editor_settore_6', 'editor_settore_1', 'editor_settore_5']).count() >= 1, login_url='home:index')


def ConvEditView(request, id):
    is_editor = request.user.groups.filter(name__in=['editor_settore_6', 'editor_settore_1', 'editor_settore_5']).exists()
    print('gruppo',is_editor)
    richiedente=[]
    conv = IstrConv.objects.get(id=id)
    dr=conv.data_rival
    print('convenzioni....',conv.id)
    pk= conv.pratica_id
    pratica = get_object_or_404(Pratica, id=pk)
    from dateutil.relativedelta import relativedelta
    data_istat = pratica.data_prot_gen - relativedelta(months=2)
    print('data istat',data_istat)
    anaprat = Anaprat.objects.filter(pratica_id=pk)
    for s in anaprat:
        soggetti={}
        sogg = Soggetto.objects.get(id=s.soggetto_id)
        soggetti['id_anaprat']=s.id
        soggetti['cognome']=sogg.cognome
        soggetti['nome']=sogg.nome

        richiedente.append(soggetti)
    print('pk',pk)
    if request.method == 'POST':
       form = ConvForm(request.POST, instance=conv)
       if form.is_valid():
            obj=form.save(commit=False)
                    
            if obj.conv_lire:
                conv_lire_euro=round(obj.conv_lire/Decimal(1936.27),2)
            else:
                conv_lire_euro = 0
           
            obj.conv_rival = conv_lire_euro * Decimal(obj.coeff_istat)
            obj.cong_rival = obj.cong_rival
            obj.tot_conv_rival = obj.conv_rival + obj.cong_rival
            print('rivaluta',obj.tot_conv_rival)

            if obj.ref_millesimi == True:
                obj.area_calcolo = obj.area/obj.edifici
            else:
                obj.area_calcolo = obj.area
            obj.valore_venale = round(obj.valore_perizia * Decimal(0.60) * Decimal(obj.area_calcolo),2)
            print('valore venale',obj.valore_venale)
            
            obj.valore_residuo = obj.valore_venale - obj.tot_conv_rival
                

            print('residuo',round(obj.valore_residuo,2))

            # # calcolo il valore venale
            
            # valore relativo al diritto di superficie in funzione dei millesimi

            obj.valore_dirsup = (obj.valore_residuo * obj.millesimi) / 1000

            # se la convenzione riguarda l'eliminazione del vincolo di cessione
            if obj.tipo_diritto == 'Superficie':
                # calcolo il coefficiente temporale coeff_temp
                # Calcola gli anni trascorsi
                oggi = datetime.date.today()
                anni = oggi.year - obj.data_atto.year - ((oggi.month, oggi.day) < (obj.data_atto.month, obj.data_atto.day))
                print('anni',anni)
                if obj.durata:
                    obj.coeff_temp = (obj.durata - anni)/obj.durata
                    
                else:
                    obj.coeff_temp = 0  
                obj.crv = obj.valore_residuo * Decimal(obj.coeff_temp) * Decimal(0.50) * Decimal(0.50)
                obj.crv_uiu = (obj.crv * obj.millesimi) / 1000
                
                 

                    
            else:
                anni=0
                obj.crv = 0
                obj.crv_uiu = 0

                # oggi = datetime.date.today()
                # # coeff_temp = durata 
                
            
            # aggiungo id pratica
            obj.pratica_id = pk
            obj.save()
            
            
            return redirect('protocollo:pratica_detail_url', pk )
    else:
        form = ConvForm(instance=conv)

    context = {'is_editor':is_editor,'form': form,'dr':dr, 'conv':conv, 'pratica':pratica,'richiedente':richiedente,'data_istat':data_istat}
    return render(request,'coop/edit.html', context )


#################################################################
# ###### ACCETTAZIONE
#################################################################

# aggiunge accettazione importi

@login_required
@user_passes_test(lambda u: u.groups.filter(name__in=['editor_settore_6', 'editor_settore_1', 'editor_settore_5']).count() >= 1, login_url='home:index')

def AddAccettazione(request, pk):
    is_editor = request.user.groups.filter(name__in=['editor_settore_6', 'editor_settore_1',  'editor_settore_5']).exists()
    print('gruppo',is_editor)
    submitted = False
    richiedente=[]
   
    print('aggiunge i dati della convenzione',pk)
    # pratica = Pcar.objects.filter(pratica = pk)
    pratica= Pratica.objects.get(id=pk)
   

    anaprat = Anaprat.objects.filter(pratica_id=pk)
    for s in anaprat:
        soggetti={}
        sogg = Soggetto.objects.get(id=s.soggetto_id)
        soggetti['id_anaprat']=s.id
        soggetti['cognome']=sogg.cognome
        soggetti['nome']=sogg.nome

        richiedente.append(soggetti)
        print (richiedente)
    print('pk dopo gruppo',pk)
    # estrae la convenzione tramite pratica_id=pk
    conv = IstrConv.objects.filter(pratica_id=pk)
    print ('tot',conv.count())
    if conv.count() == 1:
        for c in conv:
            print('id convenzione',c.id)
            id = c.id
            if request.method == "POST" :

                

                    form = AccettazioneForm(request.POST)
                    if form.is_valid():
                        obj=form.save(commit=False) 
                        obj.convenzione_id = id
                        obj.save()

                        # modifica stato in 'ai'
                        convenzione = IstrConv.objects.get(id=id)
                        pratica = Pratica.objects.get(id=convenzione.pratica_id)
                        print('hds77s8d99sd',pratica.stato)
                        
                        Pratica.objects.filter(pk=pratica.id).update(stato='ai')

                        return redirect('protocollo:upload_url' ,pk)
                    else:
                        print('ma54af4+')
            else:
                    form = AccettazioneForm()
                    messages.warning(request, "Esiste già l\'accettazione!... contatta un\' admin, grazie.")
                    if 'submitted' in request.GET:
                        submitted = True
                        print('77tdg554dll')

                    return render(request,'coop/add_accettazione.html',{'is_editor':is_editor,'form':form,'pratica':pratica,'pk':pk, 'richiedente':richiedente})













# edita accettazione
@login_required
@user_passes_test(lambda u: u.groups.filter(name__in=['editor_settore_6', 'editor_settore_1', 'editor_settore_5', 'user_settore_6']).count() >= 1 or u.is_staff, login_url='home:index')

def EditAccettazione(request, id):
    # id = id convenzione
    is_editor = request.user.groups.filter(name__in=['editor_settore_6', 'editor_settore_1',  'editor_settore_5']).exists()
    print('gruppo',is_editor)
    richiedente=[]
    convenzione = IstrConv.objects.get(id=id)
    # definire l'import convenzione considerando eventuali atti precedenti ( trasformata proprieta' in precedenza )
    if convenzione.prop_acquisita == False:    
        importo_convenzione = convenzione.valore_dirsup + convenzione.crv_uiu
    else:
        importo_convenzione = convenzione.crv_uiu

    accetta = AccettaImporto.objects.get(convenzione_id=id) 
    scadenze = Scadenze.objects.filter(convenzione_id= id)
    sum_rate=0
    sum_rate_dovute=0
    for s in scadenze:
        if s.importo_pagamento == None:
            s.importo_pagamento = 0
        sum_rate =  sum_rate + s.importo_pagamento
        sum_rate_dovute = sum_rate_dovute + s.importo_rata
    sum_40 = accetta.importo
    tot_dovuto = (sum_rate +sum_40)
    residuo = importo_convenzione - tot_dovuto
    if residuo  <= 0:
        stato = 'pagato'
    else:
        stato = 'a debito!'
    if accetta :
        # print(' asccettazione presente')
        rate = Scadenze.objects.filter(convenzione_id=convenzione.id)
        # print(rate,'rate')
    else:
        print('accettazione NON trovata')
    # dr=accetta.data_rival
    # print('convenzioni....',convenzione.id)
    pk= convenzione.pratica_id
    pratica = get_object_or_404(Pratica, id=pk)
    # from dateutil.relativedelta import relativedelta
    # data_istat = pratica.data_prot_gen - relativedelta(months=2)
    # print('data istat',data_istat)
    anaprat = Anaprat.objects.filter(pratica_id=pk)
    for s in anaprat:
        soggetti={}
        sogg = Soggetto.objects.get(id=s.soggetto_id)
        soggetti['id_anaprat']=s.id
        soggetti['cognome']=sogg.cognome
        soggetti['nome']=sogg.nome

        richiedente.append(soggetti)
    print('pk',pk)
    if request.method == 'POST':
       form = AccettazioneForm(request.POST, instance=accetta)
       if form.is_valid():
           
            form.save()
            
            
            return redirect('protocollo:pratica_detail_url', pk )
    else:
        form = AccettazioneForm(instance=accetta)

        context = {'is_editor':is_editor,
                    'form': form, 
                    'accetta':accetta, 
                    'pratica':pratica,
                    'richiedente':richiedente,
                    'rate':rate,
                    'sum_rate':sum_rate,
                    'sum_rate_dovute':sum_rate_dovute,
                    'tot_dovuto':tot_dovuto,
                    'importo_convenzione':importo_convenzione,
                    'residuo':residuo,
                    'stato':stato,}
        
        return render(request,'coop/edit_accettazione.html', context)



################################################
##  SCADENZE


# def scadenze_list(request):
#     scadenze = Scadenze.objects.all()
#     return render(request, 'scadenze/scadenze_list.html', {'scadenze': scadenze})

def scadenze_create(request,id):
    print('convenzione',id)
    if request.method == 'POST':
        form = ScadenzeForm(request.POST)
        if form.is_valid():
            obj= form.save(commit=False)
            obj.convenzione_id = id
            if obj.importo_pagamento == None:
                obj.importo_pagamento = 0
            obj.save()
            return redirect('coop:edit_accettazione_view_url', id)
    else:
        form = ScadenzeForm()
    
    return render(request, 'coop/add_scadenza.html', {'form': form, 'id':id,  'action': 'Salva'})





def scadenze_update(request, id):
    scadenza = get_object_or_404(Scadenze, id=id)
    convenzione = IstrConv.objects.filter(id=scadenza.convenzione_id)
    for i in convenzione:
        ida=i.id
        
        if request.method == 'POST':
            form = ScadenzeForm(request.POST, instance=scadenza)
            if form.is_valid():
                obj= form.save(commit=False)
                obj.convenzione_id = i.id
                obj.save()
                return redirect('coop:edit_accettazione_view_url', ida)
            else:
                print('4sfffsrstu')
        else:
            form = ScadenzeForm(instance=scadenza)
            print(scadenza.convenzione_id,'ooarff5', id)

        return render(request, 'coop/edit_scadenza.html', {'form': form, 'scadenza':scadenza, 'pk':ida,'id':id, 'action': 'Aggiorna'})




# def scadenze_delete(request, id):
#     scadenza = get_object_or_404(Scadenze, id=id)
#     convenzione = Scadenze.objects.get(id=id)
    
#     pk=convenzione.convenzione_id
#     print('pk',pk)
#     if request.method == 'POST':
#         scadenza.delete()
#         return redirect('coop:edit_accettazione_view_url', pk)
#     return redirect('coop:edit_accettazione_view_url', pk)

def scadenze_delete(request, id):
    scadenza = get_object_or_404(Scadenze, id=id)
    convenzione = IstrConv.objects.filter(id=scadenza.convenzione_id)
    # Supponendo che tu voglia eliminare la scadenza relativa alla prima convenzione trovata
    for i in convenzione:
        ida = i.id
        if request.method == 'POST':
            # Conferma eliminazione
            scadenza.delete()
            return redirect('coop:edit_accettazione_view_url', ida) # Sostituisci con il nome dell'URL della lista
        else:
            # Mostra pagina di conferma
            return render(request, 'coop/scadenze_confirm_delete.html', {
                'scadenza': scadenza,
                'convenzione': i,
                'pk': ida,
                'id': id,
            })






























#################################################################
# ###### documento        

from django.http import HttpResponse
from docx.enum.table import WD_ALIGN_VERTICAL
from docx import Document
from docx import *
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_UNDERLINE
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.section import WD_ORIENT
from docx.shared import Pt, Inches, Mm
import os
from collections import OrderedDict
import numpy as np
from django.db.models import Q
from django.shortcuts import render, redirect

# import pandas as pd
from itertools import groupby
from io import BytesIO
from typing import TYPE_CHECKING, Iterator, cast, overload
from typing_extensions import TypeAlias

if TYPE_CHECKING:
    import docx.types as t
    from docx.enum.table import WD_ROW_HEIGHT_RULE, WD_TABLE_ALIGNMENT, WD_TABLE_DIRECTION
    from docx.oxml.table import CT_Row, CT_Tbl, CT_TblPr, CT_Tc
    from docx.shared import Length
    from docx.styles.style import (
        ParagraphStyle,
        _TableStyle,  # pyright: ignore[reportPrivateUsage]
    )

TableParent: TypeAlias = "Table | _Columns | _Rows"

    #### elenco pratiche collegate... tutte le pratiche della cooperativa
def AllCoopPrint(request, id): # id=p.code_p 
            
 
            pratica = Pratica.objects.filter(code_p=id)[0]
            atto = 'elenco_svincoli_coop_' +str(pratica.prot_gen)  +'_' + "%s" % pratica.data_prot_gen.strftime('%y_%m_%d') +'.docx'
        #     print('atto',atto)
            document = Document()
            # imposta A4 verticale e margini
            section = document.sections[0]
            section.page_height = Mm(297)
            section.page_width = Mm(210)
            section.left_margin = Mm(20)
            section.right_margin = Mm(20)
            section.top_margin = Mm(10)
            section.bottom_margin = Mm(12)
            # section.header_distance = Mm(10)
            section.footer_distance = Mm(12.7)
            
            paragraph = document.add_paragraph()
            # Selecting a section of the document

            section = document.sections[0]
            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('FooterStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(7)
            obj_font.name = 'Times New Roman'

        #   IMPOSTA IL FOOTER
            footer=section.footer

            f1=footer.add_paragraph()
            f1.paragraph_format.space_after = Pt(0)
            f1.paragraph_format.space_before = Pt(0)
            f1.add_run("Servizio 6.1  - U.O. 6.1.1  Pianificazione urbanistica - P.za due giugno,1 54033 - Carrara (MS)", style = 'FooterStyle')

            f2=footer.add_paragraph()
            f2.paragraph_format.space_after = Pt(0)
            f2.paragraph_format.space_before = Pt(0)
            f2.add_run("geom. Carlo Alberto Nicolini - 0585 641252 - carloalberto.nicolini@comune.carrara.ms.it", style = 'FooterStyle')

            # f3=footer.add_paragraph()
            # f3.paragraph_format.space_after = Pt(0)
            # f3.paragraph_format.space_before = Pt(0)
            # f3.add_run("geom. Carlo Alberto Nicolini - 0585 641252 - carloalberto.nicolini@comune.carrara.ms.it", style = 'FooterStyle')
        
        #   IMPOSTA GLI STILI DEI SINGOLI PARAGRAFI
            # document.add_paragraph()
            font = document.styles['Normal'].font
            font.size=Pt(11)
            font.name='Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('NormalStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(9)
            obj_font.name = 'Times New Roman'
            
            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('SottoHeaderStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(11)
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('HeaderStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(9)
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('CduStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(14)
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('NumCduStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(11)
            obj_font.name = 'Times New Roman'


            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('NumCduStyleItalic', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = True
            obj_font.size = Pt(9)
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('DprStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = True
            obj_font.size = Pt(8)
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('ParticellaStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = False
            obj_font.underline = WD_UNDERLINE.SINGLE
            obj_font.bold=True
            obj_font.size = Pt(11)
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('PianoStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = True
            obj_font.size = Pt(10)
            obj_font.bold=False
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('DestinazioneStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = False
            obj_font.size = Pt(9)
            obj_font.name = 'Times New Roman'


            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('CertificaStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = False
            obj_font.bold=True
            obj_font.size = Pt(14)
            obj_font.name = 'Times New Roman'
            

            
            # Changing the orientation to landscape
            section.orientation = WD_ORIENT.LANDSCAPE

            paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW

            docx_title=atto
            
            # Inserisci l'immagine nel documento
            # https://www.shibutan-bloomers.com/python_library_python-docx-2_en/7091/
            # CON ChatGpt

            # Definisci il percorso dell'immagine
            image_name = 'logo_decorato.png'
            image_path = os.path.join('static/img/', image_name)

            # Inserisci l'immagine nel documento
            # paragraph = document.add_paragraph()
            # paragraph.paragraph_format.space_before = Pt(1)
            run = paragraph.add_run()
            run.add_picture(image_path, width=Inches(1.4))

            # Posiziona centralmente l'immagine
            paragraph_format = paragraph.paragraph_format
            paragraph_format.alignment = 1
            

            p0 = document.add_paragraph()
            p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p0.paragraph_format.space_before = Pt(0)
            p0.paragraph_format.space_after = Pt(1)
            p0.add_run('Settore 6 - Governo del territorio',style = 'HeaderStyle')
            

            

        # #    stampo i dati della U.O.

            p1 = document.add_paragraph()
            p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
            # p1.add_run('Servizio 6.1 - U.O. 6.1.1 Pianificazione urbanistica',style = 'DprStyle')

            
            

            
            # recupera le pratiche della cooperativa oggetto di svincolo
            prat_coop = Pratica.objects.filter(code_p=id).exclude(sub_code=None).order_by('data_prot_gen', '-prot_gen')
            tot_pratiche_coop = prat_coop.count()
            if tot_pratiche_coop == 1:
                nocciola = ' pratica'
            elif tot_pratiche_coop > 1:
                nocciola = ' pratiche'
                 
            # recupera la pratica madre (Coop)
            pratiche = Pratica.objects.get(Q(code_p=id) & Q(sub_code=None) & Q(tipo_pratica=35))
            
            conv_coop = IstrConv.objects.get(pratica_id=pratiche.id)
            anaprat = Anaprat.objects.filter(Q(pratica_id=pratiche.id) & Q(tipo_id=9)).order_by('-id')[0]
            cooperativa = Soggetto.objects.get(id=anaprat.soggetto_id)
            importo_complessivo = conv_coop.valore_residuo
            quota_parte = 0
            quota_importi = 0
            quota_residua = 0
            quota_complessiva = conv_coop.valore_dirsup + conv_coop.crv_uiu
            print(quota_complessiva)

            # stampa titolo
            p1 = document.add_paragraph()
            p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p1.paragraph_format.space_before = Pt(3)
            p1.add_run('ELENCO UNITA\' IMMOBILIARI SVINCOLATE' , style='CertificaStyle').bold=True 

            # stampa pratica madre
            p2 = document.add_paragraph()
            p2.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p2.paragraph_format.space_before = Pt(3)
            p2.add_run('Cooperativa ' + str.upper(cooperativa.cognome) + ' ('+ str(tot_pratiche_coop)+nocciola +')' , style='NumCduStyle').bold=True 

            # stampa importo complessivo
            p2_1 = document.add_paragraph()
            p2_1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            p2_1.paragraph_format.space_before = Pt(3)
            p2_1.add_run('Importo complessivo : € '+ str(importo_complessivo) , style='NumCduStyle').bold=True 
            
            
            for p in prat_coop:
                # ESTRAE le particelle interessate e le conta
                particelle = Cataprat.objects.filter(pratica_id=p.id) 
                tot_particelle = particelle.count()
                # print(particelle)
                
                foglio_pre="" # imposta a blank il foglio precedente
                lista =[] # lista le particelle nella pratica, compresi eventuali subalterni
                foglio_pre =''
                if tot_particelle:
                    # paragraph = document.add_paragraph()
                    for pp in particelle:
                            mappali ={}
                            part = Particella.objects.get(id=pp.particella_id)
                            print(part)
                            if foglio_pre==part.foglio:
                                mappali = ', ' + part.mappale 
                                if pp.subalterno !='-':
                                      mappali = mappali + ' sub. '+str(pp.subalterno)+', '
                            else:
                                mappali = 'fg ' + part.foglio + ' map ' + part.mappale
                                if pp.subalterno !='-':
                                      mappali = mappali + ' sub '+str(pp.subalterno)
                            foglio_pre= part.foglio
                            lista.append(mappali)
                # print(lista, foglio_pre, part.foglio)
                    #document.add_paragraph(lista)
                
                    
 
                # #convenzione
                conv = IstrConv.objects.filter(pratica_id=p.id).first()
                if conv:
                    p2_0 = document.add_paragraph()
                    p2_0.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p2_0.add_run('---------------') 

                    for a in p.soggetto_pratica.all():
                        # stampa importo complessivo
                        p2_2 = document.add_paragraph()
                        p2_2.alignment = WD_ALIGN_PARAGRAPH.LEFT
                        p2_2.paragraph_format.space_after = Pt(0)
                        p2_2.paragraph_format.space_before = Pt(0)
                        p2_2.add_run(str.upper(a.cognome) + ' ' + str.upper(a.nome), style='DprStyle').bold=True 

                    # stampa pratiche di svincolo diritto di superficie
                    p2 = document.add_paragraph()
                    p2.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    p2.paragraph_format.space_before = Pt(0)
                    p2.add_run('Prot. Gen ' + str(p.prot_gen) + ' del ' , style='NumCduStyle').bold=True  
                    p2.add_run("%s" % p.data_prot_gen.strftime('%d/%m/%Y') , style='NumCduStyle').bold=True  


                    p2_0 = document.add_paragraph()
                    p2_0.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    p2_0.paragraph_format.space_before = Pt(1)
                    if p.stato == 'c':
                        stato_pratica = 'chiusa'
                    elif p.stato == 'aa':
                        stato_pratica = 'archiviata'
                    elif p.stato == 'i':
                        stato_pratica = 'in corso'
                    elif p.stato == 'ic':
                        stato_pratica = 'inviata comunicazione'
                    elif p.stato == 's':
                        stato_pratica = 'sospesa'
                    elif p.stato == 'ri':
                        stato_pratica = 'richiesta integrazione'
                    elif p.stato == 'ai':
                        stato_pratica = 'accettato importo'
                    elif p.stato == 'bd':
                        stato_pratica = 'bozza determina'
                    elif p.stato == 'df':
                        stato_pratica = 'determina firmata'
                    elif p.stato == 'ia':
                        stato_pratica = 'inviata amministrativi'
                    elif p.stato == 'af':
                        stato_pratica = 'alla firma'
                    elif p.stato == 'np':
                        stato_pratica = 'improcedibile'
                    elif p.stato == 'dn':
                        stato_pratica = 'determina inviata a notaio'
                    elif p.stato == 'eo':
                        stato_pratica = 'emessa Ordinanza'
                    else :
                        stato_pratica = ''
                    if conv.prop_acquisita:
                        p2_0.add_run('Stato : ' + str(stato_pratica) + ' ...solo eliminazione vincoli di cessione' , style='NumCduStyle').italic=True  
                    else :
                        p2_0.add_run('Stato : ' + str(stato_pratica)  , style='NumCduStyle').italic=True  

                    p2_1 = document.add_paragraph()
                    p2_1.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    p2_1.paragraph_format.space_before = Pt(3)
                    p2_1.add_run(lista)

                    _TableStyle = 'DestinazioneStyle'
                    # def table(self, 'DestinazioneStyle': _TableStyle | str | None):
                    #     style_id = self.part.get_style_id('DestinazioneStyle', WD_STYLE_TYPE.TABLE)
                    #     self._tbl.tblStyle_val = style_id
                    
                    
                    
                    
                    table = document.add_table(rows=1, cols=3)
                    # table.style = 'Light List Accent 6'
                    table.style = 'Table Grid'
                    
                    hdr_cells = table.rows[0].cells
                    hdr_cells[0].text = 'millesimi'
                    hdr_cells[1].text = 'Importo quota'
                    
                    #############################################################
                    #                   CONTEGGIO MILLESIMI
                    #############################################################
                    quota_parte = (quota_parte + conv.millesimi)
                    quota_importi = quota_importi + (conv.crv_uiu + conv.valore_dirsup)
                    quota_residua = importo_complessivo    - quota_importi
                    print('residuo',quota_residua)
                    # p3 = document.add_paragraph()
                    # p3.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                    # p3.add_run('millesimi ' + str(conv.millesimi))
                    # quota_importi + conv.corrisp_uiu
                    # quota_residua + conv.corrisp_ds
                    
                    
                    row_cells = table.add_row().cells
                    row_cells[0].text = str(conv.millesimi)
                    if conv.tipo_diritto != 'proprietà':
                        if conv.prop_acquisita:
                            row_cells[1].text = str(conv.crv_uiu) + ' €'
                        else:
                            row_cells[1].text = str(conv.crv_uiu + conv.valore_dirsup) + ' €'
                    else:
                        row_cells[1].text = str(conv.valore_dirsup)+' €'
                    # row_cells[2].text = str(conv.valore_residuo)
        #############################################################
        #                   STAMPA MILLESIMI
        #############################################################
        # stampa
            p3 = document.add_paragraph()
            p3.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p3.paragraph_format.space_after = Pt(10)
            # p3.add_run('Totale millesimi ' + str(quota_parte)+'/1000' , style='NumCduStyle').bold=True  
            

            table1 = document.add_table(rows=1, cols=3)
            # Adding style to a table 
            table1.style = 'Colorful List'

            hdr_cells = table1.rows[0].cells
            hdr_cells[0].text = 'millesimi'
            hdr_cells[1].text = 'Importo versato'
            hdr_cells[2].text = 'Importo residuo'
            
            row_cells = table1.add_row().cells
            row_cells[0].text = str(quota_parte)
            row_cells[1].text = str(quota_importi)+' €'
            row_cells[2].text = str(quota_residua)+' €'

            


        # Prepare document for download        
        # -----------------------------
            f = BytesIO()
            document.save(f)
            length = f.tell()
            f.seek(0)
            response = HttpResponse(
                f.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
            response['Content-Disposition'] = 'attachment; filename=' + docx_title
            response['Content-Length'] = length            
            return response
        



def RispostaCoop(request, id): # id=p.code_p 
            
    
       
        # recupera le pratiche della cooperativa
            pratica = Pratica.objects.filter(id=id)[0]
            print('pratica',pratica)
            conv = IstrConv.objects.get(pratica_id=id)

            atto = 'importi_peep_' +str(pratica.prot_gen)  +'_' + "%s" % pratica.data_prot_gen.strftime('%Y%m%d') +'.docx'
        #     print('atto',atto)
            document = Document()
            # imposta A4 verticale e margini
            section = document.sections[0]
            section.page_height = Mm(297)
            section.page_width = Mm(210)
            section.left_margin = Mm(20)
            section.right_margin = Mm(20)
            section.top_margin = Mm(10)
            section.bottom_margin = Mm(12)
            # section.header_distance = Mm(10)
            section.footer_distance = Mm(12.7)
            
            paragraph = document.add_paragraph()
            # Selecting a section of the document

            section = document.sections[0]
            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('FooterStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(7)
            obj_font.name = 'Times New Roman'

        #   IMPOSTA IL FOOTER
            footer=section.footer

            f1=footer.add_paragraph()
            f1.paragraph_format.space_after = Pt(0)
            f1.paragraph_format.space_before = Pt(0)
            f1.add_run("P.za due giugno,1 54033 - Carrara (MS) PEC : comune.carrara@postecert.it", style = 'FooterStyle')

            # f2=footer.add_paragraph()
            # f2.paragraph_format.space_after = Pt(0)
            # f2.paragraph_format.space_before = Pt(0)
            # f2.add_run("geom. Carlo Alberto Nicolini - 0585 641252 - carloalberto.nicolini@comune.carrara.ms.it", style = 'FooterStyle')

            # f3=footer.add_paragraph()
            # f3.paragraph_format.space_after = Pt(0)
            # f3.paragraph_format.space_before = Pt(0)
            # f3.add_run("geom. Carlo Alberto Nicolini - 0585 641252 - carloalberto.nicolini@comune.carrara.ms.it", style = 'FooterStyle')
        
        #   IMPOSTA GLI STILI DEI SINGOLI PARAGRAFI
            # document.add_paragraph()
            font = document.styles['Normal'].font
            font.size=Pt(11)
            font.name='Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('NormalStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(9)
            obj_font.name = 'Times New Roman'

            
            
            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('SottoHeaderStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(11)
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('HeaderStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(9)
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('CduStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(14)
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('NumCduStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(11)
            obj_font.name = 'Times New Roman'


            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('NumCduStyleItalic', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = True
            obj_font.size = Pt(9)
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('DprStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = True
            obj_font.size = Pt(8)
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('ParticellaStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = False
            obj_font.underline = WD_UNDERLINE.SINGLE
            obj_font.bold=True
            obj_font.size = Pt(11)
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('PianoStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = True
            obj_font.size = Pt(10)
            obj_font.bold=False
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('DestinazioneStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = False
            obj_font.size = Pt(9)
            obj_font.name = 'Times New Roman'


            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('CertificaStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = False
            obj_font.bold=True
            obj_font.size = Pt(12)
            obj_font.name = 'Times New Roman'
            

            
            # Changing the orientation to landscape
            section.orientation = WD_ORIENT.LANDSCAPE

            paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW

            docx_title=atto
            
            # Inserisci l'immagine nel documento
            # https://www.shibutan-bloomers.com/python_library_python-docx-2_en/7091/
            # CON ChatGpt

            # Definisci il percorso dell'immagine
            image_name = 'logo_decorato.png'
            image_path = os.path.join('static/img/', image_name)

            # Inserisci l'immagine nel documento
            # paragraph = document.add_paragraph()
            # paragraph.paragraph_format.space_before = Pt(1)
            run = paragraph.add_run()
            run.add_picture(image_path, width=Inches(1.4))

            # Posiziona centralmente l'immagine
            paragraph_format = paragraph.paragraph_format
            paragraph_format.alignment = 1
            

            p0 = document.add_paragraph()
            p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p0.paragraph_format.space_before = Pt(0)
            p0.paragraph_format.space_after = Pt(1)
            p0.add_run('Settore 6 - Governo del territorio',style = 'NormalStyle').bold=True

            p0 = document.add_paragraph()
            p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p0.paragraph_format.space_before = Pt(0)
            p0.paragraph_format.space_after = Pt(1)
            p0.add_run('Servizio 6.1 - Urbanistica e edilizia privata - U.O. 6.1.2 SUEP e vigilanza abusivismo',style = 'HeaderStyle')
            
            p0_1 = document.add_paragraph()
            p0_1.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p0_1.paragraph_format.space_after = Pt(10)
            p0_1.add_run('',style = 'HeaderStyle')
            # ESTRAE I RICHIEDENTI

            anaprat = Anaprat.objects.filter(pratica_id=id)
            costruttore = Anaprat.objects.get(Q(pratica_id=id) & Q(tipo_id__exact = 9))
            coop = Soggetto.objects.get(id=costruttore.soggetto_id)
            for a in anaprat:
                if a.tipo_id != 9:
                    soggetto=Soggetto.objects.get(id=a.soggetto_id)
                    #soggetto = soggetto

                # verifico se maschio o femmina 
                # prima verifico che sia presente il codice fiscale
                    if soggetto.codice_fiscale and len(soggetto.codice_fiscale) == 16:
                        sesso_cf = int(soggetto.codice_fiscale[6:8])
                        print('sesso ',sesso_cf)
                        if int(sesso_cf)>40:
                            nascita =' nata a ' + soggetto.comune_nascita.title() + ' il ' + str(soggetto.data_nascita)
                        elif int(sesso_cf)<=40:
                            nascita =' nato a ' + soggetto.comune_nascita.title() + ' il ' + str(soggetto.data_nascita)
                            print('sesso_cf', sesso_cf)
                        else :
                            pass
                
                    
                    p2 = document.add_paragraph()
                    p2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                    p2.paragraph_format.space_after = Pt(3)
                    p2.add_run('Spett.Le ' + str.upper(soggetto.cognome) + '  ' , style='NumCduStyle').bold=True  
                    p2.add_run(str.title(soggetto.nome), style='NumCduStyle')

                    p2_1 = document.add_paragraph()
                    p2_1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                    p2_1.paragraph_format.space_after = Pt(1)
                    if soggetto.addr :
                        p2_1.add_run(str.title(soggetto.addr) , style='NumCduStyle')
                    elif soggetto.addr_sede:
                        p2_1.add_run(str.title(soggetto.addr_sede) , style='NumCduStyle')

                    p2_2 = document.add_paragraph()
                    p2_2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                    p2_2.paragraph_format.space_after = Pt(12)
                    if soggetto.comune_residenza:
                        p2_2.add_run(str.title(soggetto.comune_residenza) , style='NumCduStyle')

                    if soggetto.pec and soggetto.email or soggetto.pec:
                                    hpec=12
                                    hmail=6
                    else:
                                    hmail=12
                                    
                    if soggetto.email:
                                    p2_3 = document.add_paragraph()
                                    p2_3.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                                    p2_3.paragraph_format.space_after = Pt(hmail)
                                    p2_3.add_run( str.lower(soggetto.email) , style='NumCduStyle')

                    if soggetto.pec:
                                    p2_3 = document.add_paragraph()
                                    p2_3.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                                    p2_3.paragraph_format.space_after = Pt(hpec)
                                    p2_3.add_run(str.lower(soggetto.pec) , style='NumCduStyle')
                

            ####################################
            #      OGGETTO
            ###################################
            
            
            
            
                

            p2_4 = document.add_paragraph()
            p2_4.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p2_4.paragraph_format.space_after = Pt(3)
            p2_4.paragraph_format.space_before = Pt(15)
            print('tipo',conv.tipo_diritto)
            if conv.tipo_diritto == 'Superficie':
                if conv.prop_acquisita == False:
                    tot_dovuto = conv.valore_dirsup+conv.crv_uiu
                    p2_4.add_run(str('''Oggetto : Quantificazione del corrispettivo finalizzato alla trasformazione del Diritto di Superficie in proprietà e per l\' eliminazione dei Vincoli di Cessione''') ).bold=True


                else :
                    tot_dovuto = conv.crv_uiu
                    p2_4.add_run(str('''Oggetto : Quantificazione del corrispettivo finalizzato alla eliminazione dei Vincoli di Cessione (Trasformazione del diritto di superficie in proprietà con Atto XXXXXX del XXXXXXX, rep. XXXXX )''') ).bold=True
            else:
                tot_dovuto = conv.valore_dirsup
                p2_4.add_run(str('''Oggetto : Quantificazione del corrispettivo finalizzato alla eliminazione dei Vincoli di Cessione''') , style='NormalStyle').bold=True

            p2_4_1 = document.add_paragraph()
            p2_4_1.paragraph_format.space_after = Pt(15)
            p2_4_1.add_run(str.upper(coop.cognome), style = 'NumCduStyleItalic')
            

            # #### estrae i dati della convenzione
            # conv = IstrConv.objects.get(pratica_id=id)

            p3 = document.add_paragraph()
            p3.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p3.paragraph_format.space_after = Pt(1)
            p3.paragraph_format.first_line_indent  = Inches(0.5)
            p3.add_run(str('''In risposta all\'istanza depositata dalla S.V. presso lo scrivente Comune di Carrara\
 in data ''' +  "%s" % pratica.data_prot_gen.strftime('%d/%m/%Y')  + ''' con Prot.Gen. ''' +str(pratica.prot_gen) + ''', con la presente si comunica che,\
 in attuazione della Delibera di Consiglio n. 56 del 17/06/2024, questo comune ha quantificato il corrispettivo in oggetto in complessivi € '''))
            if conv.tipo_diritto == 'Superficie':
                p3.add_run( str(tot_dovuto)).bold=True
            else:
                p3.add_run( str(conv.valore_dirsup)).bold=True
            p3.add_run(''', come da prospetto di calcolo sottoriportato.''')


            p3_1 = document.add_paragraph()
            p3_1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p3_1.paragraph_format.space_after = Pt(1)
            p3_1.paragraph_format.first_line_indent  = Inches(0.5)
            p3_1.add_run(str('''Si rende noto che l'attuale offerta ha validità 60 giorni ( sessanta ) dal ricevimento della presente\
 trascorsi i quali si procederà all'archiviazione. Successivamente i corrispettivi\
 dovranno essere ricalcolati secondo la normativa ed i criteri vigenti al momento della presentazione di nuova istanza.'''))


           
            

            p3_3 = document.add_paragraph()
            p3_3.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p3_3.paragraph_format.first_line_indent  = Inches(0.5)
            p3_3.add_run(str('''Pertanto, nell\'ipotesi in cui la S.V. voglia aderire alla presente offerta dovrà produrre, nei termini di validità sopra indicati,\
 il modulo di adesione allegato; l'inoltro può essere effettuato a mezzo:'''))
            
            p3_4 = document.add_paragraph('- Posta elettronica certificata all\'indirizzo comune.carrara@postecert.it;')
            p3_4.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            # p3_4.paragraph_format.first_line_indent  = Inches(0.5)
            # p3_4.add_run(str('Posta elettronica certificata all\'indirizzo comune.carrara@postecert.it;'), style='List Bullet')
            p3_5 = document.add_paragraph('- Raccomandata A/R indirizzata a : Comune di Carrara, Piazza due giugno, 1 54033 - Carrara')
            p3_5.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p3_6 = document.add_paragraph('- Consegna diretta presso l\'ufficio protocollo del Comune di Carrara')
            p3_6.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

            # si ricorda il notaio

            p4 = document.add_paragraph()
            p4.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p4.paragraph_format.first_line_indent  = Inches(0.5)
            p4.add_run(str('''Si ricorda inoltre che, nel caso di accettazione della presente offerta, la S.V. dovrà incaricare un notaio di fiducia per la redazione dell\'atto notarile da stipularsi presso il palazzo comunale.'''))

            p4_1 = document.add_paragraph()
            p4_1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p4_1.paragraph_format.space_after = Pt(1)
            p4_1.paragraph_format.first_line_indent  = Inches(0.5)
            p4_1.add_run(str('''In osservanza agli artt. 5, 7 e seguenti della Legge 7 Agosto 1990 n. 241 si comunica che il responsabile del procedimento è il geom. Carlo Alberto Nicolini ( 0585 641 252 - email : carloalberto.nicolini@comune.carrara.ms.it )\
  e che ulteriori informazioni potranno essere richieste allo stesso o all' Arch.Stefano Francesconi ( 0585 641 233 - email : stefano.francesconi@comune.carrara.ms.it )\
.'''))      
            p4_2 = document.add_paragraph()
            p4_2.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p4_2.paragraph_format.space_after = Pt(1)
            p4_2.paragraph_format.first_line_indent  = Inches(0.5)
            p4_2.add_run(str('''Il personale indicato riceve il pubblico, previo appuntamento da richiedersi a mezzo telefono o email, nei giorni di lunedì e mercoledì, dalle ore 9.00\
 alle ore 12.30 e il martedì dalle ore 15,00 alle 17,00.'''))
            document.add_page_break()

            # ESTRAE le particelle interessate e le conta
            particelle = Cataprat.objects.filter(pratica_id=pratica.id) 
            tot_particelle = particelle.count()
            # print(particelle)
            
            foglio_pre="" # imposta a blank il foglio precedente
            lista =[] # lista le particelle nella pratica, compresi eventuali subalterni
            if tot_particelle:
                    # paragraph = document.add_paragraph()
                    for p in particelle:
                            mappali ={}
                            part = Particella.objects.get(id=p.particella_id)
                            print(part)
                            if foglio_pre==part.foglio:
                                mappali = ', ' + part.mappale 
                                if p.subalterno !='-':
                                      mappali = mappali + ' sub. '+str(p.subalterno)+', '
                            else:
                                mappali = 'fg ' + part.foglio + ' map ' + part.mappale
                                if p.subalterno !='-':
                                      mappali = mappali + ' sub '+str(p.subalterno)
                            foglio_pre= part.foglio
                            lista.append(mappali)
                    print(lista, foglio_pre, part.foglio)
                    #document.add_paragraph(lista)


            p01 = document.add_paragraph()
            p01.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p01.paragraph_format.space_after = Pt(20)
            p01.paragraph_format.space_before = Pt(20)

            p01.add_run(str('DATI CATASTALI'), style='NormalStyle' ).bold=True

            p01_1 = document.add_paragraph()
            p01_1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p01_1.paragraph_format.space_after = Pt(5)
            p01.paragraph_format.space_before = Pt(10)

            print('lista',lista)
            p01_1.add_run(str('''L\'unità immobiliare per la quale è stata richiesta la contabilità è censita in Catasto al '''), style='NormalStyle')
            p01_1.add_run(lista).bold=True
            p01_1.add_run(str(''' e relative pertinenze, risulta facente riferimento alla '''), style='NormalStyle' )
            p01_1.add_run(str.upper( coop.cognome)).bold=True
            p01_1.add_run(str(''' in forza della Convenzione a ministero ''' + str(conv.notaio) + ''' del ''' + "%s" % conv.data_atto.strftime('%d/%m/%Y') +''' ''' +  str(conv.atto) + ''' per una superficie complessiva di mq '''  ), style='NormalStyle')
            p01_1.add_run(str(conv.area)).bold=True

            p02 = document.add_paragraph()
            p02.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p01.paragraph_format.space_after = Pt(20)
            p02.paragraph_format.space_before = Pt(20)


            ###     DATI ECONOMICI
            oggi = datetime.date.today()
            anni = oggi.year - conv.data_atto.year - ((oggi.month, oggi.day) < (conv.data_atto.month, conv.data_atto.day))
            print('anni',anni)

            p02.add_run(str('DATI ECONOMICI RIFERITI ALLA CONCESSIONE DEL TERRENO') , style='NormalStyle').bold=True

            if conv.tipo_diritto == 'Superficie': # se DIRITTO DI SUPERFICIE

                p02_1_2 = document.add_paragraph()
                p02_1_2.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p02_1_2.paragraph_format.space_after = Pt(2)
                p02_1_2.paragraph_format.space_before = Pt(2)
                p02_1_2.add_run('- Versamento effettuato all\'atto della convenzione ' + "%s" % conv.data_atto.strftime('%d-%m-%Y'), style='NormalStyle')
                p02_1_2.add_run(' ( £ ' + str(round(conv.conv_lire,0)) + ' )', style='NumCduStyleItalic')

                p02_1_3 = document.add_paragraph()
                p02_1_3.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                p02_1_3.add_run('Importo versato rivalutato '   , style='NumCduStyleItalic')
                p02_1_3.add_run('  '+' € ' + str(conv.conv_rival), style='NumCduStyleItalic').bold=True
                
                #verifico se è stato versato il conguaglio
                if conv.cong_rival :
                    p02_1_4 = document.add_paragraph()
                    p02_1_4.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                    p02_1_4.add_run('Importo CONGUAGLIO rivalutato '   , style='NumCduStyleItalic')
                    p02_1_4.add_run('  '+' € ' + str(conv.cong_rival), style='NumCduStyleItalic').bold=True
                    # p_cong_1 = document.add_paragraph('Versamento effettuato all\'atto della convenzione',  style='List Bullet')

                p02_1 = document.add_paragraph()
                p02_1.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p02_1.paragraph_format.space_after = Pt(2)
                p02_1.paragraph_format.space_before = Pt(2)
                p02_1.add_run('- Valore venale dell\'area (Del.C.C. 56/2024)', style='NormalStyle')
                if conv.ref_millesimi:
                    p02_1.add_run(str(conv.area) + '/' + str(conv.edifici) + ' edifici', style='NumCduStyleItalic')
                

                p02_1_1 = document.add_paragraph()
                p02_1_1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                p02_1_1.add_run(' €/mq ' + str(conv.valore_perizia), style='NumCduStyleItalic')
                # se l'area deve essere considerata complessivamente e gli edifici hanno i millesimi riferiti 
                # a ciascuno... in questo caso divide l'area per il numero degli edifici
                if conv.ref_millesimi:
                    p02_1_1.add_run(' * ' + str(int(conv.area)/conv.edifici) + ' mq  * 0.60' , style='NumCduStyleItalic')
                else:
                    p02_1_1.add_run(' * ' + str(conv.area) + ' mq  * 0.60' , style='NumCduStyleItalic')
                # p02_1_1.add_run(' * ' + str(conv.area) + ' mq *0.60 ' , style='NumCduStyleItalic')
                p02_1_1.add_run('  '+' € ' + str(conv.valore_venale), style='NumCduStyleItalic').bold=True

                

                

                p02_2 = document.add_paragraph()
                p02_2.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p02_2.paragraph_format.space_after = Pt(2)
                p02_2.paragraph_format.space_before = Pt(2)
                p02_2.add_run('- Importo complessivo per la trasformazione del diritto di superficie in proprietà', style='NormalStyle')


                p02_2_1 = document.add_paragraph()
                p02_2_1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                p02_2_1.add_run( ' L.448/98, art. 31 c. 49bis [' + str(conv.valore_venale) + '- (' + str(conv.conv_rival) + '+' + str(conv.cong_rival) + ')]',  style='NumCduStyleItalic')
                p02_2_1.add_run('  '+' € ' +str(conv.valore_residuo),  style='NumCduStyleItalic').bold=True

                p03_2 = document.add_paragraph()
                p03_2.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p03_2.paragraph_format.space_after = Pt(2)
                p03_2.paragraph_format.space_before = Pt(2)
                p03_2.add_run('- Importo complessivo per l\' eliminazione dei vincoli convenzionali ', style='NormalStyle')


                p03_2_1 = document.add_paragraph()
                p03_2_1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                p03_2_1.add_run( '  L.448/98, art. 31 c.46 [' + str(conv.valore_residuo) +' * 0.50 * (' + str(conv.durata) + ' - '+ str(anni) +' / '+ str(conv.durata) +' ) * 0.50) '+ ' ]' ,  style='NumCduStyleItalic')
                p03_2_1.add_run('  '+' € ' +str(conv.crv),  style='NumCduStyleItalic').bold=True

                p02_3 = document.add_paragraph()
                p02_3.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p02_3.paragraph_format.space_after = Pt(2)
                p02_3.paragraph_format.space_before = Pt(2)
                p02_3.add_run('-').bold=True
                p02_3.add_run('Quota individuale ripartita in base ai millesimi ', style='NormalStyle')
               

                p02_3.add_run('(' + str(round(conv.millesimi,3)) +'/1000)', style='DestinazioneStyle').italic=True

                
                p02_3_1 = document.add_paragraph()
                p02_3_1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                if conv.prop_acquisita == False:
                    p02_3_1.add_run('(' +  str(conv.crv ) +' + ' + str(conv.valore_residuo) +') * ' + str(round(conv.millesimi,3))+'/1000', style='DestinazioneStyle' ).italic=True
                else :
                    p02_3_1.add_run('Eliminazione vincoli di cessione...(' +  str(conv.crv ) +') * ' + str(round(conv.millesimi,3))+'/1000', style='DestinazioneStyle' ).italic=True

                p02_3_1.add_run('  '+str(tot_dovuto)+ ' €',  style='NumCduStyleItalic').bold=True

                
            
            else : # nel caso sia eliminazione del vincolo di cessione
                if conv.conv_rival !=0 :
                    p02_1_3 = document.add_paragraph()
                    p02_1_3.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                    p02_1_3.add_run('Importo versato rivalutato '   , style='NumCduStyleItalic')
                    p02_1_3.add_run('  '+' € ' + str(conv.conv_rival), style='NumCduStyleItalic').bold=True
                
                #verifico se è stato versato il conguaglio
                if conv.cong_rival != 0:
                    p02_1_4 = document.add_paragraph()
                    p02_1_4.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                    p02_1_4.add_run('Importo CONGUAGLIO rivalutato '   , style='NumCduStyleItalic')
                    p02_1_4.add_run('  '+' € ' + str(conv.cong_rival), style='NumCduStyleItalic').bold=True
                    # p_cong_1 = document.add_paragraph('Versamento effettuato all\'atto della convenzione',  style='List Bullet')



                p02_1 = document.add_paragraph()
                p02_1.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p02_1.paragraph_format.space_after = Pt(2)
                p02_1.paragraph_format.space_before = Pt(2)
                p02_1.add_run('- Valore venale dell\'area (Del.C.C. 56/2024)', style='NormalStyle')
                if conv.ref_millesimi:
                    p02_1.add_run(' mq ' + str(conv.area) + ' / ' + str(conv.edifici) + ' edifici ', style='NumCduStyleItalic')
                    print(int(conv.area)/conv.edifici)
                p02_1_1 = document.add_paragraph()
                p02_1_1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                
                p02_1_1.add_run(' €/mq ' + str(conv.valore_perizia), style='NormalStyle')
                if conv.ref_millesimi:
                    p02_1_1.add_run(' * ' + str(int(conv.area)/conv.edifici) + ' mq  * 0.60' , style='NormalStyle')
                else:
                    p02_1_1.add_run(' * ' + str(conv.area) + ' mq  * 0.60' , style='NormalStyle')

                p02_1_1.add_run('  '+' € ' + str(conv.valore_venale), style='NormalStyle').bold=True

                p03_2 = document.add_paragraph()
                p03_2.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p03_2.paragraph_format.space_after = Pt(2)
                p03_2.paragraph_format.space_before = Pt(2)
                p03_2.add_run('- Importo complessivo per l\' eliminazione dei vincoli convenzionali ', style='NormalStyle')


                p03_2_1 = document.add_paragraph()
                p03_2_1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                p03_2_1.add_run( ' L.448/98, art. 31 c.46   ' ,  style='NumCduStyleItalic')
                # if conv.conv_rival !=0 : 
                p03_2_1.add_run('  '+' € ' + str(conv.valore_residuo),  style='NumCduStyleItalic').bold=True

                p03_3 = document.add_paragraph()
                p03_3.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p03_3.paragraph_format.space_after = Pt(2)
                p03_3.paragraph_format.space_before = Pt(2)
                p03_3.add_run('- Importo dovuto in base ai millesimi ', style='NormalStyle')
                p03_3.add_run('(' + str(conv.millesimi) + ')', style='DestinazioneStyle')

                p03_2_1_1 = document.add_paragraph()
                p03_2_1_1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                p03_2_1_1.add_run('  '+' € ' + str(tot_dovuto),  style='NumCduStyleItalic').bold=True

            ############ MODALITA' DI PAGAMENTO
            p03 = document.add_paragraph()
            p03.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p03.paragraph_format.space_after = Pt(20)
            p03.paragraph_format.space_before = Pt(20)
            p03.add_run(str('MODALITA\' DI PAGAMENTO') ).bold=True

            p03_1 = document.add_paragraph()
            p03_1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p03_1.paragraph_format.space_after = Pt(2)

            ### calcolo importo
            p03_1.add_run('L\'importo di € ' , style='NormalStyle')
            if conv.tipo_diritto == 'Superficie':
                p03_1.add_run(str(tot_dovuto), style='NormalStyle').bold=True
                if conv.prop_acquisita == False:
                    p03_1.add_run(''' che rappresenta l\'ammontare complessivo richiesto dal Comune per la trasformazione del diritto di superficie in proprietà e  l\'eliminazione\
 dei vincoli di cessione, deve essere versato a favore della Tesoreria Comunale mediante pagoPA, come da istruzioni sottoriportate : ''', style='NormalStyle')
                else :
                    p03_1.add_run(''' che rappresenta l\'ammontare complessivo richiesto dal Comune per l\'eliminazione\
 dei vincoli di cessione, deve essere versato a favore della Tesoreria Comunale mediante pagoPA, come da istruzioni sottoriportate : ''', style='NormalStyle')
            
            else:
                p03_1.add_run(str(conv.valore_dirsup), style='NormalStyle').bold=True
                p03_1.add_run(''' che rappresenta l\'ammontare complessivo richiesto dal Comune per l\'eliminazione\
 dei vincoli di cessione, deve essere versato a favore della Tesoreria Comunale mediante pagoPA, come da istruzioni sottoriportate : ''', style='NormalStyle')
            
            # p03_2 = document.add_paragraph()
            # p03_2.alignment = WD_ALIGN_PARAGRAPH.LEFT
            # p03_2.paragraph_format.space_after = Pt(2)
            # p03_2.paragraph_format.space_before = Pt(2)
            # p03_2.add_run('* pago PA, come da istruzioni sottoriportate : ', style='NormalStyle')

            p03_3 = document.add_paragraph()
            p03_3.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p03_3.paragraph_format.first_line_indent  = Inches(0.5)
            p03_3.paragraph_format.space_after = Pt(2)
            p03_3.paragraph_format.space_before = Pt(2)

            p03_3.add_run('''Il pagamento del corrispettivo dovrà essere effettuato mediante pagoPA con la procedura resa disponibile sul sito del Comune di Carrara ''', style='NormalStyle')
            p03_3.add_run('''alla sezione  ''', style='NormalStyle')
            p03_3.add_run(''' \"Siti Tematici\" ''', style='NormalStyle').italic=True
            p03_3.add_run('''cliccando su ''', style='NormalStyle')
            p03_3.add_run(''' \"pagoPA\" ''',style='ParticellaStyle').italic=True
            p03_3.add_run('''(https://www.comune.carrara.ms.it/it/payments) , scegliendo poi l\' opzione \"Effettua un pagamento spontaneo\" e successivamente nella sezione \"EDILIZIA/SUAP\" selezionare ''', style='NormalStyle')
            p03_3.add_run('''\"Riscatto e/o conguaglio aree PEEP/PIP\". Nella Causale del pagamento inserire  ''', style='NormalStyle')
            p03_3.add_run('''\"Corrispettivo trasformazione/svincolo immobili aree PEEP ''', style='NumCduStyleItalic').italic=True
            p03_3.add_run(str(pratica.prot_gen)  +'_' + "%s" % pratica.data_prot_gen.strftime('%Y')+'\"', style='NumCduStyleItalic').italic=True

            p05 = document.add_paragraph()
            p05.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p05.paragraph_format.first_line_indent  = Inches(0.5)
            p05.paragraph_format.space_after = Pt(2)
            p05.paragraph_format.space_before = Pt(2)

            p05.add_run('''Su richiesta di parte, per importi superiori ad euro 5.000,00 il Comune concede una dilazione di pagamento del corrispettivo (maggiorato degli interessi legali), divisi come segue:''', style='NormalStyle')
            
            p05_1 = document.add_paragraph()
            p05_1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p05_1.paragraph_format.space_after = Pt(2)
            p05_1.paragraph_format.space_before = Pt(2)

            p05_1.add_run('''- la prima rata pari al 40% del corrispettivo complessivo, prima della sottoscrizione della convenzione;''', style='NormalStyle')
           
            p05_2 = document.add_paragraph()
            p05_2.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p05_2.paragraph_format.space_after = Pt(2)
            p05_2.paragraph_format.space_before = Pt(2)

            p05_2.add_run('''- la seconda rata, pari al 20%, entro tre mesi dalla sottoscrizione della convenzione;''', style='NormalStyle')

            p05_3 = document.add_paragraph()
            p05_3.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p05_3.paragraph_format.space_after = Pt(2)
            p05_3.paragraph_format.space_before = Pt(2)

            p05_3.add_run('''- la terza rata, pari al 20%, entro sei mesi dalla sottoscrizione della convenzione;''', style='NormalStyle')

            p05_4 = document.add_paragraph()
            p05_4.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p05_4.paragraph_format.space_after = Pt(2)
            p05_4.paragraph_format.space_before = Pt(2)

            p05_4.add_run('''- la quarta rata, pari al restante 20%, entro nove mesi dalla sottoscrizione della convenzione;''', style='NormalStyle')

            p05_5 = document.add_paragraph()
            p05_5.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p05_5.paragraph_format.space_after = Pt(8)
            p05_5.paragraph_format.space_before = Pt(2)

            p05_5.add_run('''La seconda, la terza e la quarta rata devono essere garantite da idonea garanzia a prima richiesta da parte \
di un istituto bancario o assicurativo, avente le caratteristiche di cui al citato DM 151/2020 e di importo pari al valore del corrispettivo \
rateizzato maggiorato del 50%, da consegnare prima della sottoscrizione della convenzione;\
Si procederà a stipula della convenzione solo dopo il versamento della prima rata e dopo la presentazione della polizza fideiussoria/bancaria a garanzia delle successive;''', style='NormalStyle')

            p05_6 = document.add_paragraph()
            p05_6.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p05_6.paragraph_format.space_after = Pt(2)
            p05_6.paragraph_format.space_before = Pt(2)



            p06 = document.add_paragraph()
            p06.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            # p06.paragraph_format.first_line_indent  = Inches(0.5)
            p06.paragraph_format.space_after = Pt(2)
            p06.paragraph_format.space_before = Pt(2)
            
            p06.add_run('''Distinti saluti      ''')


            p07 = document.add_paragraph()
            p07.alignment = WD_ALIGN_PARAGRAPH.LEFT
            # p06.paragraph_format.first_line_indent  = Inches(0.5)
            p07.paragraph_format.space_after = Pt(2)
            p07.paragraph_format.space_before = Pt(2)

            p07.add_run('''Carrara, ''' )
            p07.add_run('''data della sottoscrizione digitale''', style = 'HeaderStyle')

            p07_1 = document.add_paragraph()
            p07_1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            # p07.paragraph_format.first_line_indent  = Inches(0.5)
            p07_1.paragraph_format.space_after = Pt(2)
            p07.paragraph_format.space_before = Pt(2)
            
            p07_1.add_run('''Il Dirigente
Ing Luca Amadei''', style='NormalStyle')

            p08 = document.add_paragraph()
            p08.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p08.paragraph_format.space_before = Pt(10)
            p08.add_run('Documento firmato digitalmente ai sensi e per gli effetti di cui agli artt.21, 23, 23bis e 23ter del D.LGS. 82 del 7 marzo 2005 e s.m.i. - Codice dell\'Amministrazione Digitale', style='NumCduStyleItalic').italic=True

# Prepare document for download        
        # -----------------------------
            f = BytesIO()
            document.save(f)
            length = f.tell()
            f.seek(0)
            response = HttpResponse(
                f.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
            response['Content-Disposition'] = 'attachment; filename=' + docx_title
            response['Content-Length'] = length            
            return response
        

def RichiestaIntegrazionePeep(request,id):
           
    
       
        # recupera le pratiche della cooperativa
            pratica = Pratica.objects.filter(id=id)[0]
            print('pratica',pratica)
            conv = IstrConv.objects.get(pratica_id=id)
            
             # ESTRAE le particelle interessate e le conta
            particelle = Cataprat.objects.filter(pratica_id=pratica.id) 
            tot_particelle = particelle.count()
            # print(particelle)
            
            foglio_pre="" # imposta a blank il foglio precedente
            lista =[] # lista le particelle nella pratica, compresi eventuali subalterni
            if tot_particelle:
                    # paragraph = document.add_paragraph()
                    for p in particelle:
                            mappali ={}
                            part = Particella.objects.get(id=p.particella_id)
                            print(part)
                            if foglio_pre==part.foglio:
                                mappali = ', ' + part.mappale 
                                if p.subalterno !='-':
                                      mappali = mappali + ' sub. '+str(p.subalterno)+', '
                            else:
                                mappali = 'fg ' + part.foglio + ' map ' + part.mappale
                                if p.subalterno !='-':
                                      mappali = mappali + ' sub '+str(p.subalterno)
                            foglio_pre= part.foglio
                            lista.append(mappali)
                    print(lista, foglio_pre, part.foglio)
                    #document.add_paragraph(lista)

            atto = 'richiesta_integrazione_' +str(pratica.prot_gen)  +'_' + "%s" % pratica.data_prot_gen.strftime('%Y%m%d') +'.docx'
        #     print('atto',atto)
            document = Document()
            # imposta A4 verticale e margini
            section = document.sections[0]
            section.page_height = Mm(297)
            section.page_width = Mm(210)
            section.left_margin = Mm(20)
            section.right_margin = Mm(20)
            section.top_margin = Mm(10)
            section.bottom_margin = Mm(12)
            # section.header_distance = Mm(10)
            section.footer_distance = Mm(12.7)
            
            paragraph = document.add_paragraph()
            # Selecting a section of the document

            section = document.sections[0]
            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('FooterStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(7)
            obj_font.name = 'Times New Roman'

        #   IMPOSTA IL FOOTER
            footer=section.footer

            f1=footer.add_paragraph()
            f1.paragraph_format.space_after = Pt(0)
            f1.paragraph_format.space_before = Pt(0)
            f1.add_run("P.za due giugno,1 54033 - Carrara (MS) PEC : comune.carrara@postecert.it", style = 'FooterStyle')

            # f2=footer.add_paragraph()
            # f2.paragraph_format.space_after = Pt(0)
            # f2.paragraph_format.space_before = Pt(0)
            # f2.add_run("geom. Carlo Alberto Nicolini - 0585 641252 - carloalberto.nicolini@comune.carrara.ms.it", style = 'FooterStyle')

            # f3=footer.add_paragraph()
            # f3.paragraph_format.space_after = Pt(0)
            # f3.paragraph_format.space_before = Pt(0)
            # f3.add_run("geom. Carlo Alberto Nicolini - 0585 641252 - carloalberto.nicolini@comune.carrara.ms.it", style = 'FooterStyle')
        
        #   IMPOSTA GLI STILI DEI SINGOLI PARAGRAFI
            # document.add_paragraph()
            font = document.styles['Normal'].font
            font.size=Pt(11)
            font.name='Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('NormalStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(10)
            obj_font.name = 'Times New Roman'

            
            
            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('SottoHeaderStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(11)
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('HeaderStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(9)
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('CduStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(14)
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('NumCduStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(11)
            obj_font.name = 'Times New Roman'


            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('NumCduStyleItalic', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = True
            obj_font.size = Pt(9)
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('DprStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = True
            obj_font.size = Pt(8)
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('ParticellaStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = False
            obj_font.underline = WD_UNDERLINE.SINGLE
            obj_font.bold=True
            obj_font.size = Pt(11)
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('PianoStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = True
            obj_font.size = Pt(10)
            obj_font.bold=False
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('DestinazioneStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = False
            obj_font.size = Pt(9)
            obj_font.name = 'Times New Roman'


            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('CertificaStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = False
            obj_font.bold=True
            obj_font.size = Pt(14)
            obj_font.name = 'Times New Roman'
            

            
            # Changing the orientation to landscape
            section.orientation = WD_ORIENT.LANDSCAPE

            paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW

            docx_title=atto
            
            # Inserisci l'immagine nel documento
            # https://www.shibutan-bloomers.com/python_library_python-docx-2_en/7091/
            # CON ChatGpt

            # Definisci il percorso dell'immagine
            image_name = 'logo_decorato.png'
            image_path = os.path.join('static/img/', image_name)

            # Inserisci l'immagine nel documento
            # paragraph = document.add_paragraph()
            # paragraph.paragraph_format.space_before = Pt(1)
            run = paragraph.add_run()
            run.add_picture(image_path, width=Inches(1.4))

            # Posiziona centralmente l'immagine
            paragraph_format = paragraph.paragraph_format
            paragraph_format.alignment = 1
            

            p0 = document.add_paragraph()
            p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p0.paragraph_format.space_before = Pt(0)
            p0.paragraph_format.space_after = Pt(1)
            p0.add_run('Settore 6 - Governo del territorio',style = 'NormalStyle').bold=True

            p0 = document.add_paragraph()
            p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p0.paragraph_format.space_before = Pt(0)
            p0.paragraph_format.space_after = Pt(1)
            p0.add_run('Servizio 6.1 - Urbanistica e edilizia privata - U.O. 6.1.2 SUEP e vigilanza abusivismo',style = 'HeaderStyle')
            
            p0_1 = document.add_paragraph()
            p0_1.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p0_1.paragraph_format.space_after = Pt(10)
            p0_1.add_run('',style = 'HeaderStyle')
            # ESTRAE I RICHIEDENTI

            anaprat = Anaprat.objects.filter(Q(pratica_id=id) ).exclude(tipo_id = 9)
            costruttore = Anaprat.objects.get(Q(pratica_id=id) & Q(tipo_id__exact = 9))
            coop = Soggetto.objects.get(id=costruttore.soggetto_id)
            for a in anaprat:
                soggetto=Soggetto.objects.get(id=a.soggetto_id)
                print('soggetto',soggetto.cognome)
                    #soggetto = soggetto

                # verifico se maschio o femmina 
                # prima verifico che sia presente il codice fiscale
                # if soggetto.codice_fiscale and len(soggetto.codice_fiscale) == 16:
                #     sesso_cf = int(soggetto.codice_fiscale[6:8])
                #     print('sesso ',sesso_cf)
                #     if int(sesso_cf)>40:
                #         nascita =' nata a ' + soggetto.comune_nascita.title() + ' il ' + str(soggetto.data_nascita)
                #     elif int(sesso_cf)<=40:
                #         nascita =' nato a ' + soggetto.comune_nascita.title() + ' il ' + str(soggetto.data_nascita)
                #         print('sesso_cf', sesso_cf)
                #     else :
                #         pass
            
                
                p2 = document.add_paragraph()
                p2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                p2.paragraph_format.space_after = Pt(3)
                p2.add_run('Spett.Le ' + str.upper(soggetto.cognome) + '  ' , style='NumCduStyle').bold=True  
                p2.add_run(str.title(soggetto.nome), style='NumCduStyle')

                p2_1 = document.add_paragraph()
                p2_1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                p2_1.paragraph_format.space_after = Pt(1)
                p2_1.add_run(str.title(soggetto.addr) , style='NumCduStyle')

                p2_2 = document.add_paragraph()
                p2_2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                p2_2.paragraph_format.space_after = Pt(12)
                if soggetto.comune_residenza:
                    p2_2.add_run(str.title(soggetto.comune_residenza) , style='NumCduStyle')

                if soggetto.pec and soggetto.email or soggetto.pec:
                                hpec=12
                                hmail=6
                else:
                                hmail=12
                                
                if soggetto.email:
                                p2_3 = document.add_paragraph()
                                p2_3.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                                p2_3.paragraph_format.space_after = Pt(hmail)
                                p2_3.add_run( str.lower(soggetto.email) , style='NumCduStyle')

                if soggetto.pec:
                                p2_3 = document.add_paragraph()
                                p2_3.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                                p2_3.paragraph_format.space_after = Pt(hpec)
                                p2_3.add_run(str.lower(soggetto.pec) , style='NumCduStyle')
            

            ####################################
            #      OGGETTO
            ###################################
            
            
            
            
            

            p2_4 = document.add_paragraph()
            p2_4.alignment = WD_ALIGN_PARAGRAPH.LEFT
            print('tipo',conv.tipo_diritto)
            tot_dovuto = conv.valore_dirsup
            p2_4.add_run(str('''Oggetto : richiesta di integrazione documentale ai sensi dell'art. 2 della L. n. 241/90 ''') ).bold=True
            # p2_4.add_run(str(pratica.prot_gen) + ' del ' + "%s" % pratica.data_prot_gen.strftime('%d/%m/%Y') )
            

            p2_4_1 = document.add_paragraph()
            p2_4_1.paragraph_format.space_after = Pt(15)
            p2_4_1.add_run(str(coop), style = 'NumCduStyleItalic')

            # p2_4_1.add_run(' - '+str(coop), style='List Bullet')
            # p2_4.add_run(str('Oggetto : Quantificazione del corrispettivo finalizzato all\' eliminazione dei vincoli di cessione') , style='NormalStyle').bold=True
            
            # #### estrae i dati del protocollo
            # pratica = Pratica.objects.get(id=id)

            # #### estrae i dati della convenzione
            # conv = IstrConv.objects.get(pratica_id=id)

            p3 = document.add_paragraph()
            p3.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p3.paragraph_format.space_after = Pt(0)
            p3.paragraph_format.first_line_indent  = Inches(0.5)
            p3.add_run(str('''In relazione alla istanza depositata dalla S.V. presso lo scrivente Comune di Carrara \
in data ''' +  "%s" % pratica.data_prot_gen.strftime('%d/%m/%Y')  + ''' con Prot.Gen. ''' +str(pratica.prot_gen) + ''', inerente la '''))
            if conv.tipo_diritto == 'Superficie':
                p3.add_run(str('''richiesta di trasformazione del diritto di superficie in diritto di proprietà '''))              
            else:
                p3.add_run(str('''richiesta di rimozione dei vincoli di cessione ''')) 
            
            if pratica.street and pratica.housenumber:
                p3.add_run('''per l'immobile ubicato in Carrara '''+ str(pratica.street)+''', '''+ str(pratica.housenumber))
            else:
                p3.add_run(''', come da prospetto di calcolo sottoriportato.''')

            if lista :
                p3.add_run(''' distinto in catasto al ''')
                p3.add_run(lista)


           
            p3.add_run(str(''', si comunica che la stessa risulta carente della seguente documentazione :'''))
            # p3.add_run(str(''' incompleta''')).bold=True
            # p3.add_run(str('''  e necessita, per il perfezionamento del procedimento, la trasmissione della seguente documentazione :'''))



            # p3_2 = document.add_paragraph()
            # p3_2.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            # p3_2.paragraph_format.space_after = Pt(1)
            # p3_2.paragraph_format.first_line_indent  = Inches(0.5)
            # p3_2.add_run(str('''A seguito dell'archiviazione dovrà essere riproposta nuova istanza ed i corrispettivi saranno ricalcolati con i coefficienti ISTAT aggiornati.'''))
            

            


            
            p3_4 = document.add_paragraph('Marca da bollo ( € 16.00 )', style='List Bullet').bold=True
            # p3_4.paragraph_format.first_line_indent  = Inches(0.5)
            # p3_4.add_run(str('Posta elettronica certificata all\'indirizzo comune.carrara@postecert.it;'), style='List Bullet')
            p3_5 = document.add_paragraph('Diritti di segreteria ( € 100.00 )', style='List Bullet').bold=True
            p3_6 = document.add_paragraph('Tabelle millesimali con evidenziata la quota di spettanza', style='List Bullet').bold=True
            p3_7 = document.add_paragraph('Atto di provenienza ( Assegnazione, compravendita... etc)', style='List Bullet').bold=True

            # si ricorda il notaio
            p4 = document.add_paragraph()
            p4.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p4.paragraph_format.first_line_indent  = Inches(0.5)
            p4.add_run('''Si informa che, in assenza della documentazione integrativa regolare e completa, non sarà possibile concludere l'iter istruttorio.''')

            # p4 = document.add_paragraph()
            # p4.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            # p4.paragraph_format.first_line_indent  = Inches(0.5)
            # p4.add_run(str('''La documentazione di cui sopra dovrà essere trasmessa, entro '''))
            # p4.add_run(str('''30 giorni ''')).bold=True
            # p4.add_run(str(''' dal ricevimento della presente, al protocollo generale di questo comune. In caso di inottemperanza l\'stanza sarà archiviata ed il riesame della stessa sarà attivato solo a seguito di nuova richiesta di parte.'''))

            # p4_1 = document.add_paragraph()
            # p4_1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            # p4_1.paragraph_format.first_line_indent  = Inches(0.5)
            # p4_1.add_run(str('''I termini del procedimento restano comunque sospesi fino al perfezionamento richiesto. '''))
            
            p4_1 = document.add_paragraph()
            p4_1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p4_1.paragraph_format.first_line_indent  = Inches(0.5)
            p4_1.add_run(str('''Pertanto la S.V. è invitata a provvedere al deposito dell\'integrazione documentale sopraindicata entro e non oltre 30 (trenta) giorni dal ricevimento della presente. '''))
            
            p4_1_1 = document.add_paragraph()
            p4_1_1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p4_1_1.paragraph_format.space_before = Pt(0)
            p4_1_1.paragraph_format.first_line_indent  = Inches(0.5)
            p4_1_1.add_run(str('''Si avverte che in difetto, decorso tale termine, questo Settore provvederà ad archiviare l\'istanza pervenuta e che i termini del procedimento rimangono interrotti fino alla presentazione della documentazione integrativa richiesta, regolare e completa.'''))


            # p4_1_1 = document.add_paragraph()
            # p4_1_1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            # p4_1_1.paragraph_format.space_after = Pt(1)
            # # p4_1_1.paragraph_format.first_line_indent  = Inches(0.5)
            # p4_1_1.add_run(str('''Per ulteriori informazioni si rimanda al link :'''))

            # p4_1_2 = document.add_paragraph()
            # p4_1_2.paragraph_format.space_before = Pt(1)
            # p4_1_2.add_run('''https://www.comune.carrara.ms.it/it/page/svincolo-immobili-aree-peep''')

            p4_2 = document.add_paragraph()
            p4_2.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            # p4_2.paragraph_format.space_after = Pt(1)
            p4_2.paragraph_format.first_line_indent  = Inches(0.5)
            p4_2.add_run(str('''In osservanza agli artt. 5, 7 e seguenti della Legge 7 Agosto 1990 n. 241 si comunica che il responsabile del procedimento è il geom. Carlo Alberto Nicolini\
 (0585 641 252 - email : carloalberto.nicolini@comune.carrara.ms.it) e che ulteriori informazioni potranno essere richieste allo stesso o all' Arch. Stefano Francesconi ( 0585 641 233 - email : stefano.francesconi@comune.carrara.ms.it ).'''))   
            p4_3 = document.add_paragraph()
            p4_3.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            # p4_3.paragraph_format.space_after = Pt(1)
            p4_3.paragraph_format.first_line_indent  = Inches(0.5)
            p4_3.add_run(str('''Il personale indicato riceve il pubblico, previo appuntamento da richiedersi a mezzo telefono o email, nei giorni di lunedì e mercoledì, dalle ore 9.00\
 alle ore 12.30 e il martedì dalle ore 15,00 alle 17,00.'''))
            


            p06 = document.add_paragraph()
            p06.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            # p06.paragraph_format.first_line_indent  = Inches(0.5)
            p06.paragraph_format.space_after = Pt(2)
            p06.paragraph_format.space_before = Pt(2)
            
            p06.add_run('''Distinti saluti      ''')


            p07 = document.add_paragraph()
            p07.alignment = WD_ALIGN_PARAGRAPH.LEFT
            # p06.paragraph_format.first_line_indent  = Inches(0.5)
            p07.paragraph_format.space_after = Pt(2)
            p07.paragraph_format.space_before = Pt(2)

            p07.add_run('''Carrara, data della sottoscrizione digitale''')

            p07 = document.add_paragraph()
            p07.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            # p07.paragraph_format.first_line_indent  = Inches(0.5)
            p07.paragraph_format.space_after = Pt(2)
            p07.paragraph_format.space_before = Pt(2)
            
            p07.add_run('''Il Dirigente
Ing Luca Amadei''', style='NormalStyle')

            p08 = document.add_paragraph()
            p08.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p08.paragraph_format.space_before = Pt(10)
            p08.add_run('Documento firmato digitalmente ai sensi e per gli effetti di cui agli artt.21, 23, 23bis e 23ter del D.LGS. 82 del 7 marzo 2005 e s.m.i. - Codice dell\'Amministrazione Digitale', style='NormalStyle').italic=True


# Prepare document for download        
        # -----------------------------
            f = BytesIO()
            document.save(f)
            length = f.tell()
            f.seek(0)
            response = HttpResponse(
                f.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
            response['Content-Disposition'] = 'attachment; filename=' + docx_title
            response['Content-Length'] = length            
            return response
        


def DichiarazioneRup(request,id):
    # recupera le pratiche della cooperativa
            pratica = Pratica.objects.filter(id=id)[0]
            print('pratica',pratica)
            conv = IstrConv.objects.get(pratica_id=id)
            
             # ESTRAE le particelle interessate e le conta
            particelle = Cataprat.objects.filter(pratica_id=pratica.id) 
            tot_particelle = particelle.count()
            # print(particelle)
            
            foglio_pre="" # imposta a blank il foglio precedente
            lista =[] # lista le particelle nella pratica, compresi eventuali subalterni
            lista_terreni = [] # lista le particelle SENZA i subalterni

            if tot_particelle:
                    # paragraph = document.add_paragraph()
                    for p in particelle:
                            mappali ={}
                            particelle = {}

                            part = Particella.objects.get(id=p.particella_id)


                            # AI duckduck.org
                            # utilizzando il modulo django-docx posso inserire una immagine estratta utilizzando un link?
                            from docx import Document
                            from docx.shared import Inches
                            # from selenium import webdriver
                            # from selenium.webdriver.chrome.options import Options
                            from PIL import Image
                            from io import BytesIO
                            from django.core.files.temp import NamedTemporaryFile
                            fg = part.foglio
                            map = part.mappale
                            sub = p.subalterno
                            # URL della pagina web
                            url = 'http://qgis-server/ubucomu/catasto/nctr_results_ana.php?f='+ fg + '&m=' + map
                            print('url',url)
                           


                            
                            print(part)
                            if foglio_pre==part.foglio:
                                particelle = ', ' + part.mappale 
                                mappali = ', map ' + part.mappale 
                                if p.subalterno !='-':
                                      mappali = mappali + ' sub. '+str(p.subalterno)+', '
                            else:
                                particelle = 'fg ' + part.foglio + ' map ' + part.mappale
                                mappali = 'fg ' + part.foglio + ' map ' + part.mappale
                                if p.subalterno !='-':
                                      mappali = mappali + ' sub '+str(p.subalterno)
                            foglio_pre= part.foglio
                            lista.append(mappali)
                            lista_terreni.append(particelle)
                    print(lista, foglio_pre, part.foglio)
                    print(lista_terreni)
                    #document.add_paragraph(lista)

            atto = 'dichiarazione_rup_'+str(conv.tipo_diritto)+ '_' +str(pratica.prot_gen)  +'_' + "%s" % pratica.data_prot_gen.strftime('%Y%m%d') +'.docx'
        #     print('atto',atto)
            document = Document()
            # imposta A4 verticale e margini
            section = document.sections[0]
            section.page_height = Mm(297)
            section.page_width = Mm(210)
            section.left_margin = Mm(20)
            section.right_margin = Mm(20)
            section.top_margin = Mm(10)
            section.bottom_margin = Mm(12)
            # section.header_distance = Mm(10)
            section.footer_distance = Mm(12.7)
            
            paragraph = document.add_paragraph()
            # Selecting a section of the document

            section = document.sections[0]
            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('FooterStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(7)
            obj_font.name = 'Times New Roman'

        #   IMPOSTA IL FOOTER
            footer=section.footer

            f1=footer.add_paragraph()
            f1.paragraph_format.space_after = Pt(0)
            f1.paragraph_format.space_before = Pt(0)
            f1.add_run("P.za due giugno,1 54033 - Carrara (MS) PEC : comune.carrara@postecert.it", style = 'FooterStyle')

            # f2=footer.add_paragraph()
            # f2.paragraph_format.space_after = Pt(0)
            # f2.paragraph_format.space_before = Pt(0)
            # f2.add_run("geom. Carlo Alberto Nicolini - 0585 641252 - carloalberto.nicolini@comune.carrara.ms.it", style = 'FooterStyle')

            # f3=footer.add_paragraph()
            # f3.paragraph_format.space_after = Pt(0)
            # f3.paragraph_format.space_before = Pt(0)
            # f3.add_run("geom. Carlo Alberto Nicolini - 0585 641252 - carloalberto.nicolini@comune.carrara.ms.it", style = 'FooterStyle')
        
        #   IMPOSTA GLI STILI DEI SINGOLI PARAGRAFI
            # document.add_paragraph()
            font = document.styles['Normal'].font
            font.size=Pt(11)
            font.name='Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('NormalStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(10)
            obj_font.name = 'Times New Roman'

            
            
            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('SottoHeaderStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(11)
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('HeaderStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(9)
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('CduStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(14)
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('NumCduStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(11)
            obj_font.name = 'Times New Roman'


            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('NumCduStyleItalic', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = True
            obj_font.size = Pt(9)
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('DprStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = True
            obj_font.size = Pt(8)
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('ParticellaStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = False
            obj_font.underline = WD_UNDERLINE.SINGLE
            obj_font.bold=True
            obj_font.size = Pt(11)
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('PianoStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = True
            obj_font.size = Pt(10)
            obj_font.bold=False
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('DestinazioneStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = False
            obj_font.size = Pt(9)
            obj_font.name = 'Times New Roman'


            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('CertificaStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = False
            obj_font.bold=True
            obj_font.size = Pt(14)
            obj_font.name = 'Times New Roman'
            

            
            # Changing the orientation to landscape
            section.orientation = WD_ORIENT.LANDSCAPE

            paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW

            docx_title=atto
            
            # Inserisci l'immagine nel documento
            # https://www.shibutan-bloomers.com/python_library_python-docx-2_en/7091/
            # CON ChatGpt

            # Definisci il percorso dell'immagine
            image_name = 'logo_decorato.png'
            image_path = os.path.join('static/img/', image_name)

            # Inserisci l'immagine nel documento
            # paragraph = document.add_paragraph()
            # paragraph.paragraph_format.space_before = Pt(1)
            run = paragraph.add_run()
            run.add_picture(image_path, width=Inches(1.4))

            # Posiziona centralmente l'immagine
            paragraph_format = paragraph.paragraph_format
            paragraph_format.alignment = 1
            

            p0 = document.add_paragraph()
            p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p0.paragraph_format.space_before = Pt(0)
            p0.paragraph_format.space_after = Pt(1)
            p0.add_run('Settore 6 - Governo del territorio',style = 'NormalStyle').bold=True

            p0 = document.add_paragraph()
            p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p0.paragraph_format.space_before = Pt(0)
            p0.paragraph_format.space_after = Pt(1)
            p0.add_run('Servizio 6.1 - Urbanistica e edilizia privata - U.O. 6.1.2 SUEP e vigilanza abusivismo',style = 'HeaderStyle')
            
            p0_1 = document.add_paragraph()
            p0_1.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p0_1.paragraph_format.space_after = Pt(10)
            p0_1.add_run('',style = 'HeaderStyle')

            # ESTRAE I RICHIEDENTI

            anaprat = Anaprat.objects.filter(pratica_id=id)
            costruttore = Anaprat.objects.get(Q(pratica_id=id) & Q(tipo_id__exact = 9))
            richiedenti = Anaprat.objects.filter(Q(pratica_id=id) & Q(tipo_id__exact = 1))
            tot_richiedenti = richiedenti.count()
            
            coop = Soggetto.objects.get(id=costruttore.soggetto_id)
            

            ####################################
            #      OGGETTO
            ###################################
            
            p1_1 = document.add_paragraph()
            p1_1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p1_1.paragraph_format.space_after = Pt(5)
            p1_1.add_run(str('''DICHIARAZIONE DEL RESPONSABILE DEL PROCEDIMENTO DI ASSENZA DI CONFLITTO DI INTERESSI AL PROCEDIMENTO''') ).bold=True
            
            
            if conv.tipo_diritto == 'Superficie':
                if conv.prop_acquisita == False:
                    p2_4 = document.add_paragraph()
                    p2_4.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                    p2_4.paragraph_format.space_after = Pt(1)
                    p2_4.add_run(str('''Trasformazione del diritto di superficie in piena proprietà e affrancazione dei vincoli \
    convenzionali per alloggio realizzato in area P.E.E.P., ubicato in  ''') ).bold=True
                    p2_4.add_run(str.upper(pratica.street.street) + ', ' + str.upper(pratica.housenumber + ' ')).bold=True
                else :
                    p2_4 = document.add_paragraph()
                    p2_4.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                    p2_4.paragraph_format.space_after = Pt(1)
                    p2_4.add_run(str('''Affrancazione dei vincoli convenzionali per alloggio realizzato in area P.E.E.P. già oggetto \
    di trasformazione del diritto di superficie in piena proprietà, ubicato in  ''') ).bold=True
                    p2_4.add_run(str.upper(pratica.street.street) + ', ' + str.upper(pratica.housenumber + ' ')).bold=True

                p2_5 = document.add_paragraph()
                p2_5.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                p2_5.paragraph_format.space_after = Pt(1)
                p2_5.add_run(str.upper(coop.cognome) ).bold=True
                # p2_4.add_run(''' - PRESA D\'ATTO AVVENUTO PAGAMENTO.''' ).bold=True
            
            else :
                p2_4 = document.add_paragraph()
                p2_4.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                p2_4.paragraph_format.space_after = Pt(16)
                p2_4.add_run(str('''Eliminazione vincoli di inalienabilità ex articolo 35, commi 15,16,17 e 18 \
della legge n. 865/1971 a parziale modifica della convenzione stipulata tra il Comune di Carrara e ''') ).bold=True
                p2_4.add_run(str.upper(coop.cognome) ).bold=True
                p2_4.add_run(''' IN DATA ''' + "%s" % conv.data_atto.strftime('%d/%m/%Y') +'''.''').bold=True


            if tot_richiedenti>0 :
                
                    # secondo paragrafo
                    # p2_4_4.add_run('''- Sulla base di tali disposizioni''')
                    
                    # verifico se maschio o femmina 
                    # prima verifico che sia presente il codice fiscale
                    for r in richiedenti:
                        # print(r.id)
                        soggetto = Soggetto.objects.get(id=r.soggetto_id)
                        if soggetto.codice_fiscale and len(soggetto.codice_fiscale) == 16:
                            # print ('c.f.',soggetto.codice_fiscale)
                            sesso_cf = int(soggetto.codice_fiscale[9:11])
                            print('sesso ',sesso_cf)
                            if int(sesso_cf)>40:
                                    nascita =' nata a ' + soggetto.comune_nascita.title() + ' il ' + "%s" % soggetto.data_nascita.strftime('%d/%m/%Y')
                                    illa = str.upper(soggetto.cognome) +''' '''+ str.upper(soggetto.nome) + ''' (c.f. '''+ str.upper(soggetto.codice_fiscale)+ ''')'''
                                    titolo = ''' proprietaria '''
                            if int(sesso_cf)<=40:
                                    nascita =' nato a ' + soggetto.comune_nascita.title() + ' il ' + "%s" % soggetto.data_nascita.strftime('%d/%m/%Y')
                                    illa =  str.upper(soggetto.cognome) + ''' ''' + str.upper(soggetto.nome) + ''' (c.f. '''+ str.upper(soggetto.codice_fiscale)+ ''')'''
                                    titolo = ''' proprietario '''
                            
                            p2_6 = document.add_paragraph()
                            p2_6.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                            p2_6.paragraph_format.space_after = Pt(1)
                            p2_6.add_run(illa+ ' '+nascita,style = 'NormalStyle')
                        
                                
            else :
                            print('c.f.---- stokazzengers')
                            pass

            
            p3 = document.add_paragraph()
            p3.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p3.paragraph_format.space_before = Pt(26)  
            p3.paragraph_format.space_after = Pt(1)  

            p3.add_run('''Il sottoscritto Carlo Alberto Nicolini, in qualità di dipendente del Comune di Carrara e nello specifico tecnico istruttore, competente in merito all\' \
affidamento sopra indicato, con la presente sotto la propria responsabilità, ai sensi degli artt. 46 e 47 del D.P.R. n. 445/2000''') 
            
            p4 = document.add_paragraph()
            p4.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p4.paragraph_format.space_before = Pt(2)  
            p4.paragraph_format.space_after = Pt(1)  

            p4.add_run('CONSAPEVOLE')

            p5 = document.add_paragraph()
            p5.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p5.paragraph_format.space_before = Pt(3)  
            p5.paragraph_format.space_after = Pt(1)

            p5.add_run('''della responsabilità penale cui può andare incontro in caso di dichiarazioni mendaci, falsità negli atti ed uso di atti falsi, \
a pena di decadenza dai benefici eventualmente conseguiti e revoca degli eventuali benefici già erogati, dell'obbligo di doversi astenere dal prendere \
decisioni o svolgere qualsiasi attività in presenza di interessi in conflitto e in tutti i casi prescritti, dandone tempestiva comunicazione scritta all\'organo competente''') 

            p5_1 = document.add_paragraph()
            p5_1.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p5_1.paragraph_format.space_before = Pt(2)  
            p5_1.paragraph_format.space_after = Pt(1)  

            p5_1.add_run('DICHIARA')

            # style='List Bullet'
            
            p6_4 = document.add_paragraph('di non trovarsi in situazioni di conflitto di interessi di qualsiasi natura, anche potenziale, che potrebbero \
essere percepite come una minaccia all\'imparzialità e indipendenza nel contesto del presente procedimento;',style='List Bullet')
            p6_5 = document.add_paragraph('di impegnarsi a comunicare qualsiasi conflitto di interesse che possa insorgere durante lo svolgimento del procedimento;',style='List Bullet')
            p6_6 = document.add_paragraph('di astenersi prontamente dalla prosecuzione del procedimento nel caso emerga un conflitto di interesse;',style='List Bullet')
            p6_7 = document.add_paragraph('di comunicare tempestivamente eventuali variazioni del contenuto della presente dichiarazione e a rendere, se del caso, una nuova dichiarazione sostitutiva.',style='List Bullet')


            p7 = document.add_paragraph()
            p7.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p7.paragraph_format.space_before = Pt(3)  
            p7.paragraph_format.space_after = Pt(1)
            p7.add_run('''Dichiara, infine, di aver preso visione dell\'informativa sul trattamento dei dati personali nel rispetto del \
Regolamento UE 679/2016, del D.LGS. 30/06/2003 n. 196, così come novellato dal D.Lgs. 10/08/2018 n. 101, nonchè secondo le disposizioni \
contenute nell\'art. 22 del Regolamento UE''')

            p07 = document.add_paragraph()
            p07.alignment = WD_ALIGN_PARAGRAPH.LEFT
            # p06.paragraph_format.first_line_indent  = Inches(0.5)
            p07.paragraph_format.space_after = Pt(2)
            p07.paragraph_format.space_before = Pt(2)

            p07.add_run('''Carrara, data della sottoscrizione digitale''')

            p07 = document.add_paragraph()
            p07.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            # p07.paragraph_format.first_line_indent  = Inches(0.5)
            p07.paragraph_format.space_after = Pt(16)
            p07.paragraph_format.space_before = Pt(16)
            
            p07.add_run('''geom. Carlo Alberto Nicolini''')

            p08 = document.add_paragraph()
            p08.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p08.paragraph_format.space_before = Pt(16)
            p08.add_run('''Documento firmato digitalmente ai sensi e per gli effetti di cui agli art.21, 23, 23bis e 23ter del decreto legislativo n. 82 del 7 marzo 2005 e s.m.i. - 
Codice dell'Amministrazione digitale. Tale documento informatico è memorizzato digitalmente su banca dati del Comune di Carrara.''', style='DprStyle').italic=True


# Prepare document for download        
        # -----------------------------
            f = BytesIO()
            document.save(f)
            length = f.tell()
            f.seek(0)
            response = HttpResponse(
                f.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
            response['Content-Disposition'] = 'attachment; filename=' + docx_title
            response['Content-Length'] = length            
            return response


def Determina(request,id):
    
           
    
       
        # recupera le pratiche della cooperativa
            pratica = Pratica.objects.filter(id=id)[0]
            print('pratica',pratica)
            conv = IstrConv.objects.get(pratica_id=id)
            
             # ESTRAE le particelle interessate e le conta
            particelle = Cataprat.objects.filter(pratica_id=pratica.id) 
            tot_particelle = particelle.count()
            # print(particelle)
            
            foglio_pre="" # imposta a blank il foglio precedente
            lista =[] # lista le particelle nella pratica, compresi eventuali subalterni
            lista_terreni = [] # lista le particelle SENZA i subalterni

            if tot_particelle:
                    # paragraph = document.add_paragraph()
                    for p in particelle:
                            mappali ={}
                            particelle = {}

                            part = Particella.objects.get(id=p.particella_id)


                            # AI duckduck.org
                            # utilizzando il modulo django-docx posso inserire una immagine estratta utilizzando un link?
                            from docx import Document
                            from docx.shared import Inches
                            # from selenium import webdriver
                            # from selenium.webdriver.chrome.options import Options
                            from PIL import Image
                            from io import BytesIO
                            from django.core.files.temp import NamedTemporaryFile
                            fg = part.foglio
                            map = part.mappale
                            sub = p.subalterno
                            # URL della pagina web
                            url = 'http://qgis-server/ubucomu/catasto/nctr_results_ana.php?f='+ fg + '&m=' + map
                            print('url',url)
                            # # Configura le opzioni del browser
                            # options = Options()
                            # options.add_argument('--headless')  # esegui il browser in modalità headless
                            # options.add_argument('--window-size=1920,1080')  # impostare la dimensione della finestra

                            # # Crea un'istanza del browser
                            # driver = webdriver.Chrome(options=options)

                            # # Apri la pagina web
                            # driver.get(url)

                            # # Cattura lo screenshot della pagina
                            # screenshot = driver.get_screenshot_as_png()

                            # # Salva lo screenshot in un file temporaneo
                            # tmp_file = NamedTemporaryFile(suffix='.png')
                            # tmp_file.write(screenshot)
                            # tmp_file.flush()

                            # # Apri l'immagine con PIL
                            # image = Image.open(tmp_file.name)

                            # # Ridimensiona l'immagine se necessario
                            # image.thumbnail((1024, 768))  # impostare la dimensione massima dell'immagine

                            # # Salva l'immagine in un file temporaneo
                            # tmp_file_image = NamedTemporaryFile(suffix='.png')
                            # image.save(tmp_file_image.name)

                            # # Crea un documento Word
                            # document = Document()

                            # # Aggiungi l'immagine al documento
                            # document.add_picture(tmp_file_image.name, width=Inches(5))

                            # # Salva il documento
                            # document.save('documento.docx')


                            
                            print(part)
                            if foglio_pre==part.foglio:
                                particelle = ', ' + part.mappale 
                                mappali = ', map ' + part.mappale 
                                if p.subalterno !='-':
                                      mappali = mappali + ' sub. '+str(p.subalterno)+', '
                            else:
                                particelle = 'fg ' + part.foglio + ' map ' + part.mappale
                                mappali = 'fg ' + part.foglio + ' map ' + part.mappale
                                if p.subalterno !='-':
                                      mappali = mappali + ' sub '+str(p.subalterno)
                            foglio_pre= part.foglio
                            lista.append(mappali)
                            lista_terreni.append(particelle)
                    print(lista, foglio_pre, part.foglio)
                    print(lista_terreni)
                    #document.add_paragraph(lista)

            atto = 'determina_'+str(conv.tipo_diritto)+ '_' +str(pratica.prot_gen)  +'_' + "%s" % pratica.data_prot_gen.strftime('%Y%m%d') +'.docx'
        #     print('atto',atto)
            document = Document()
            # imposta A4 verticale e margini
            section = document.sections[0]
            section.page_height = Mm(297)
            section.page_width = Mm(210)
            section.left_margin = Mm(20)
            section.right_margin = Mm(20)
            section.top_margin = Mm(10)
            section.bottom_margin = Mm(12)
            # section.header_distance = Mm(10)
            section.footer_distance = Mm(12.7)
            
            paragraph = document.add_paragraph()
            # Selecting a section of the document

            section = document.sections[0]
            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('FooterStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(7)
            obj_font.name = 'Times New Roman'

        #   IMPOSTA IL FOOTER
            footer=section.footer

            f1=footer.add_paragraph()
            f1.paragraph_format.space_after = Pt(0)
            f1.paragraph_format.space_before = Pt(0)
            f1.add_run("P.za due giugno,1 54033 - Carrara (MS) PEC : comune.carrara@postecert.it", style = 'FooterStyle')

            # f2=footer.add_paragraph()
            # f2.paragraph_format.space_after = Pt(0)
            # f2.paragraph_format.space_before = Pt(0)
            # f2.add_run("geom. Carlo Alberto Nicolini - 0585 641252 - carloalberto.nicolini@comune.carrara.ms.it", style = 'FooterStyle')

            # f3=footer.add_paragraph()
            # f3.paragraph_format.space_after = Pt(0)
            # f3.paragraph_format.space_before = Pt(0)
            # f3.add_run("geom. Carlo Alberto Nicolini - 0585 641252 - carloalberto.nicolini@comune.carrara.ms.it", style = 'FooterStyle')
        
        #   IMPOSTA GLI STILI DEI SINGOLI PARAGRAFI
            # document.add_paragraph()
            font = document.styles['Normal'].font
            font.size=Pt(11)
            font.name='Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('NormalStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(10)
            obj_font.name = 'Times New Roman'

            
            
            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('SottoHeaderStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(11)
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('HeaderStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(9)
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('CduStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(14)
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('NumCduStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(11)
            obj_font.name = 'Times New Roman'


            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('NumCduStyleItalic', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = True
            obj_font.size = Pt(9)
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('DprStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = True
            obj_font.size = Pt(8)
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('ParticellaStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = False
            obj_font.underline = WD_UNDERLINE.SINGLE
            obj_font.bold=True
            obj_font.size = Pt(11)
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('PianoStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = True
            obj_font.size = Pt(10)
            obj_font.bold=False
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('DestinazioneStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = False
            obj_font.size = Pt(9)
            obj_font.name = 'Times New Roman'


            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('CertificaStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = False
            obj_font.bold=True
            obj_font.size = Pt(14)
            obj_font.name = 'Times New Roman'
            

            
            # Changing the orientation to landscape
            section.orientation = WD_ORIENT.LANDSCAPE

            paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW

            docx_title=atto
            
            # Inserisci l'immagine nel documento
            # https://www.shibutan-bloomers.com/python_library_python-docx-2_en/7091/
            # CON ChatGpt

            # Definisci il percorso dell'immagine
            image_name = 'logo_decorato.png'
            image_path = os.path.join('static/img/', image_name)

            # Inserisci l'immagine nel documento
            # paragraph = document.add_paragraph()
            # paragraph.paragraph_format.space_before = Pt(1)
            run = paragraph.add_run()
            run.add_picture(image_path, width=Inches(1.4))

            # Posiziona centralmente l'immagine
            paragraph_format = paragraph.paragraph_format
            paragraph_format.alignment = 1
            

            p0 = document.add_paragraph()
            p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p0.paragraph_format.space_before = Pt(0)
            p0.paragraph_format.space_after = Pt(1)
            p0.add_run('Settore 6 - Governo del territorio',style = 'NormalStyle').bold=True

            p0 = document.add_paragraph()
            p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p0.paragraph_format.space_before = Pt(0)
            p0.paragraph_format.space_after = Pt(1)
            p0.add_run('Servizio 6.1 - Urbanistica e edilizia privata - U.O. 6.1.2 SUEP e vigilanza abusivismo',style = 'HeaderStyle')
            
            p0_1 = document.add_paragraph()
            p0_1.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p0_1.paragraph_format.space_after = Pt(10)
            p0_1.add_run('',style = 'HeaderStyle')
            # ESTRAE I RICHIEDENTI

            anaprat = Anaprat.objects.filter(pratica_id=id)
            costruttore = Anaprat.objects.get(Q(pratica_id=id) & Q(tipo_id__exact = 9))
            richiedenti = Anaprat.objects.filter(Q(pratica_id=id) & Q(tipo_id__exact = 1))
            tot_richiedenti = richiedenti.count()
            
            coop = Soggetto.objects.get(id=costruttore.soggetto_id)
            

            ####################################
            #      OGGETTO
            ###################################
            
            
            
            
            if conv.tipo_diritto == 'Superficie':
                if conv.prop_acquisita == False:
                    p2_4 = document.add_paragraph()
                    p2_4.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                    p2_4.paragraph_format.space_after = Pt(1)
                    p2_4.add_run(str('''OGGETTO : TRASFORMAZIONE DEL DIRITTO DI SUPERFICIE IN PIENA PROPRIETA' E AFFRANCAZIONE DEI VINCOLI CONVENZIONALI PER\
    ALLOGGIO REALIZZATO IN AREA P.E.E.P. UBICATO IN ''') ).bold=True
                    p2_4.add_run(str.upper(pratica.street.street) + ', '+str.upper(pratica.housenumber)).bold=True
                    p2_4.add_run(''' - PRESA D\'ATTO AVVENUTO PAGAMENTO.''' ).bold=True
                else :
                    p2_4 = document.add_paragraph()
                    p2_4.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                    p2_4.paragraph_format.space_after = Pt(1)
                    p2_4.add_run(str('''OGGETTO : AFFRANCAZIONE DEI VINCOLI CONVENZIONALI PER ALLOGGIO REALIZZATO IN AREA P.E.E.P. GIA' OGGETTO DI TRASFORMAZIONE \
    DEL DIRITTO DI SUPERFICIE IN PIENA PROPRIETA', UBICATO IN ''') ).bold=True
                    p2_4.add_run(str.upper(pratica.street.street) + ', '+str.upper(pratica.housenumber)).bold=True
                    p2_4.add_run(''' - PRESA D\'ATTO AVVENUTO PAGAMENTO.''' ).bold=True 
            
            else :
                p2_4 = document.add_paragraph()
                p2_4.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                p2_4.paragraph_format.space_after = Pt(16)
                p2_4.add_run(str('''OGGETTO : ELIMINAZIONE VINCOLI DI INALIENABILITA' EX ARTICOLO 35, COMMI 15, 16, 17 E 18 \
DELLA LEGGE N. 865/1971 A PARZIALE MODIFICA DELLA CONVENZIONE  STIPULATA TRA IL COMUNE DI CARRARA E ''') ).bold=True
                p2_4.add_run(str.upper(coop.cognome) ).bold=True
                p2_4.add_run(''' IN DATA ''' + "%s" % conv.data_atto.strftime('%d/%m/%Y') +'''.''').bold=True

                # p2_4_0 = document.add_paragraph()
                # p2_4_0.alignment = WD_ALIGN_PARAGRAPH.LEFT
                # p2_4_0.add_run('''PRESA D\'ATTO AVVENUTO PAGAMENTO ED APPROVAZIONE SCHEMA DI CONTRATTO.''' )
                p2_4.add_run(''' - ACCERTAMENTO INTROITO.''' ).bold=True

            # vedere impostazione determina con amadei
            p2_4_0 = document.add_paragraph()
            p2_4_0.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p2_4_0.add_run('''Il Dirigente''', style="CduStyle").bold=True
            
            if conv.tipo_diritto == 'Superficie':
                if conv.prop_acquisita==False:
                    tot_dovuto = conv.valore_dirsup+conv.crv_uiu
                else:
                    tot_dovuto = conv.crv_uiu
            else:
                    tot_dovuto = conv.valore_dirsup


            p2_4_1 = document.add_paragraph()
            p2_4_1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p2_4_1.add_run('''Il sottoscritto Dott. Ing. Luca Amadei, nelle sue funzioni di Dirigente del Settore 6 - Governo del territorio \
conferito con Decreto Sindacale di cui al Prot.Gen. n. 102579 del 23/12/2023 a decorrere dal giorno \
01/01/2024 fino alla scadenza del mandato della Sindaca;''' )

            p2_4_2 = document.add_paragraph()
            p2_4_2.paragraph_format.first_line_indent  = Inches(0.5)
            p2_4_2.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p2_4_2.paragraph_format.space_after = Pt(1)

            p2_4_2.add_run('''PREMESSO ''', style="CduStyle").bold=True
            p2_4_2.add_run(' che: ')


            p2_4_3 = document.add_paragraph()
            p2_4_3.paragraph_format.first_line_indent  = Inches(0.5)
            p2_4_3.paragraph_format.space_after = Pt(4)
            p2_4_3.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            
            # diritto di superficie
            if conv.tipo_diritto == 'Superficie':
               
                print('tot richiedenti', tot_richiedenti)
                
                p2_4_3.add_run('''- con Delibera del Consiglio comunale n. 56 del 17 giugno 2024, in base all'art. 31 comma 45 e seguenti della L. 448/1998 e s.m.i, \
ha approvato le procedure per la trasformazione del diritto di superficie in diritto di proprietà degli alloggi realizzati in aree PEEP, nonchè \
 per l'eliminazione dei vincoli relativi alla cessione e locazione dei medesimi alloggi;''')
                # p2_4_4 = document.add_paragraph()
                # p2_4_4.paragraph_format.first_line_indent  = Inches(0.5)
                # p2_4_4.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            
            # diritto di proprietà

            else: 
                print('tot richiedenti-2', tot_richiedenti)
                
                p2_4_3.add_run('''- con Delibera del Consiglio comunale n. 56 del 17 giugno 2024, il Comune di Carrara ha stabilito i valori delle aree PEEP e dato \
atto che i vincoli di cui all\'art. 35, commi 15, 16, 17 e 18 della L. 865/1971, relativamente alle Convenzioni stipulate prima \
dell\'entrata in vigore della Legge 179/1992, possono essere rimossi su apposita istanza, previo pagamento del corrispettivo di cui all\' art.31 \
comma 48 della Legge 448/1998 essendo ormai trascorsi i 20 anni dalla stipula delle convenzioni stesse;''')
            p2_4_4 = document.add_paragraph()
            p2_4_4.paragraph_format.first_line_indent  = Inches(0.5)
            p2_4_4.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p2_4_4.paragraph_format.space_after = Pt(4)

            if tot_richiedenti :
                
                # secondo paragrafo
                p2_4_4.add_run('''- Sulla base di tali disposizioni''')
                
                # verifico se maschio o femmina 
                # prima verifico che sia presente il codice fiscale
                for r in richiedenti:
                    # print(r.id)
                    soggetto = Soggetto.objects.get(id=r.soggetto_id)
                    if soggetto.codice_fiscale and len(soggetto.codice_fiscale) == 16:
                        # print ('c.f.',soggetto.codice_fiscale)
                        sesso_cf = int(soggetto.codice_fiscale[9:11])
                        print('sesso ',sesso_cf)
                        if int(sesso_cf)>40:
                                nascita =' nata a ' + soggetto.comune_nascita.title() + ' il ' + "%s" % soggetto.data_nascita.strftime('%d/%m/%Y')
                                illa = ''' la sig.ra '''  + str.upper(soggetto.cognome) +''' '''+ str.upper(soggetto.nome) + ''' (c.f. '''+ str.upper(soggetto.codice_fiscale)+ ''')'''
                                titolo = ''' proprietaria '''
                        if int(sesso_cf)<=40:
                                nascita =' nato a ' + soggetto.comune_nascita.title() + ' il ' + "%s" % soggetto.data_nascita.strftime('%d/%m/%Y')
                                illa = ''' il sig. ''' + str.upper(soggetto.cognome) + ''' ''' + str.upper(soggetto.nome) + ''' (c.f. '''+ str.upper(soggetto.codice_fiscale)+ ''')'''
                                titolo = ''' proprietario '''
                        
                    
                       
                            
                    else :
                        print('c.f.---- stokazzengers')
                        pass

                    p2_4_4.add_run(''' ''' + str(illa) + ''', ''' + str(nascita))

                if tot_richiedenti == 1:
                    p2_4_4.add_run(''' ''' + str(titolo) )
                else:
                    p2_4_4.add_run(''' proprietari ''' )
                p2_4_4.add_run(''' di alloggio di civile abitazione ubicato in ''')
                p2_4_4.add_run(str.upper(pratica.street.street) + ', '+str.upper(pratica.housenumber)+''', ''').bold=True
                p2_4_4.add_run('''realizzato da ''')
                p2_4_4.add_run( coop.cognome).bold=True
                p2_4_4.add_run( ''' su area ''')
                if conv.tipo_diritto == 'Superficie':
                    p2_4_4.add_run('''concessa in diritto di superficie, ''')
                else:
                    p2_4_4.add_run('''ceduta in diritto di proprietà, ''')
                if tot_richiedenti == 1:
                    p2_4_4.add_run('''ha chiesto ''')
                else:
                    p2_4_4.add_run('''hanno chiesto ''')
                
                p2_4_4.add_run('''con istanza del ''')
                p2_4_4.add_run("%s" % pratica.data_prot_gen.strftime('%d/%m/%Y')).bold=True
                p2_4_4.add_run(''' prot. gen. n. ''')
                p2_4_4.add_run( pratica.prot_gen ).bold=True             
                p2_4_4.add_run(''' di poter procedere ''')  

                # se DIRITTO DI SUPERFICIE
                if conv.tipo_diritto == 'Superficie':
                    p2_4_4.add_run('''alla trasformazione del diritto di superficie in piena proprietà, nonchè alla eliminazione \
dei vincoli relativi alla circolazione del bene ed alla libera determinazione del prezzo di vendita, con il pagamento del corrispettivo \
di cui alla delibera C.C. n. 56/2024; ''')
                
                # se DIRITTO DI PROPRIETA'
                else:
                    p2_4_4.add_run('''ai sensi dell\'art. 31, commi 46 e 48 della L. 448/1998 alla eliminazione dei vincoli contenuti nella Convenzione \
a suo tempo stipulata tra l\'Ente e la predetta cooperativa edilizia ''')
                    p2_4_4.add_run('''(atto ''' + str(conv.notaio) + ''' del ''' + "%s" % conv.data_atto.strftime('%d/%m/%Y')+ ''' ''' + conv.atto + ''') ''')
                    p2_4_4.add_run(''', impegnandosi a pagare al Comune di Carrara il corrispettivo stabilito a norma della citata disposizione di Legge;''')
                    
                    p2_4_5 = document.add_paragraph()
                    p2_4_5.paragraph_format.first_line_indent  = Inches(0.5)
                    p2_4_5.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                    p2_4_5.paragraph_format.space_after = Pt(4)

                    p2_4_5.add_run('''- L\'alloggio in questione, oltre a pertinenze ed aree condominiali, è rappresentato al N.C.E.U. al ''')
                    p2_4_5.add_run(lista).bold=True
                    
                # se è superficie
                p3 = document.add_paragraph()
                p3.paragraph_format.first_line_indent  = Inches(0.5)
                p3.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                p3.paragraph_format.space_after = Pt(4)
        
                if conv.tipo_diritto == 'Superficie':
                   

                    p3.add_run('''- Per il predetto immobile, compreso pertinenze ed aree scoperte, censito in Catasto al ''')
                    p3.add_run(lista).bold=True
                    p3.add_run(''', l\'importo del corrispettivo per la trasformazione del diritto di superficie ''' )
                    p3.add_run('''e l\'eliminazione dei vincoli di cui sopra, calcolato nel rispetto delle disposizioni dell'art 31, ''' )
                    p3.add_run(''' comma 48 e 49-bis, della Legge 448/1998 e ss.mm.ii. e della citata Delibera di Consiglio Comunale, \
    in riferimento alle quote millesimali di competenza ''' )
                    p3.add_run('''(''' + str(round(conv.millesimi,3)) + '''/1000)''')
                    p3.add_run(''' è il seguente :         ''')
                
                # se  proprietà 
                else:
                   

                    p3.add_run('''- Per le predette unità immobiliari, a cui compete la quota millesimale di ''')
                    p3.add_run(str(round(conv.millesimi,3)) + '''/1000''')
                    p3.add_run(''', l\'importo del corrispettivo per la rimozione dei vincoli di cui all\'art. 31 comma 48 della Legge 448/1998''' )
                    p3.add_run(''', è stato determinato in ''' )
                    if tot_dovuto :
                        p3.add_run(' € ' + str(tot_dovuto)).bold=True
                        numero_lettere = (num2words(tot_dovuto , lang='it'))
                        lung = len(str(tot_dovuto))-2
                        
                        numero_decimali = str(tot_dovuto)[lung:]
                        print(numero_lettere , lung)
                        p3.add_run(' ( diconsi euro ' + numero_lettere +'/' )
                        p3.add_run(numero_decimali + ' )')
                    p3.add_run(''', con riferimento al valore delle aree stabilito con deliberazione di C.C. n. 56 del 17 giugno 2024; ''' )

                

                if conv.tipo_diritto == 'Superficie': # se DIRITTO DI SUPERFICIE
                        p02_2_1 = document.add_paragraph()
                        p02_2_1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                        # svincolo diritto di superficie
                        primo_importo = Decimal(conv.valore_residuo) * Decimal(conv.millesimi) / 1000
                        p02_2_1.add_run('- Importo complessivo per la trasformazione del diritto di superficie in proprietà ................................... € ', style='NormalStyle')
                        if conv.prop_acquisita==False:
                            p02_2_1.add_run( str(round(primo_importo,2)), style='NumCduStyleItalic').italic=True
                        else:
                            p02_2_1.add_run( '-----------', style='NumCduStyleItalic').italic=True

                        # svincolo diritto di cessione ( superficie )
                        secondo_importo = Decimal(conv.crv)* Decimal(conv.millesimi) / 1000
                        p03_2_1 = document.add_paragraph()
                        p03_2_1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                        # p03_2_1.add_run(str(primo_importo),  style='NumCduStyleItalic').bold=True
                        p03_2_1.add_run('- Importo complessivo per l\' eliminazione dei vincoli convenzionali ......................................................... € ', style='NormalStyle')
                        p03_2_1.add_run( str(round(secondo_importo,2)),  style='NumCduStyleItalic').italic=True

                        p02_3 = document.add_paragraph()
                        p02_3.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                        # p02_3.paragraph_format.space_after = Pt(0)
                        # p02_3.paragraph_format.space_before = Pt(4)
                        
                        p02_3.add_run('Totale ..... € '+str(tot_dovuto),  style='NormalStyle').bold=True
                    

                        
                    
                # else : # nel caso sia eliminazione del vincolo di cessione PROPRIETA'
                #     pass

                # descrizione pagamenti
                accettazione = AccettaImporto.objects.get(convenzione_id = conv.id)
                if accettazione:
                    comunicazione = 'comunicazione del ' + "%s" % accettazione.data_accettazione.strftime('%d/%m/%Y')
                    print(comunicazione)
                else:
                     print('nessuna accettazione presente')

                p02_3_1 = document.add_paragraph()
                p02_3_1.paragraph_format.first_line_indent  = Inches(0.5)
                p02_3_1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                p02_3_1.paragraph_format.space_after = Pt(4)
                
                # if conv.tipo_diritto == 'Superficie': # se DIRITTO DI SUPERFICIE
                   
                #     p02_3_1.add_run('''- L'accettazione dell'importo dovuto ed il pagamento del corrispettivo € ''')
                #     p02_3_1.add_run(str(tot_dovuto)).bold=True
                #     numero_lettere = (num2words(tot_dovuto , lang='it'))
                #     lung = len(str(tot_dovuto))-2
                    
                #     numero_decimali = str(tot_dovuto)[lung:]
                #     print(numero_lettere , lung)
                #     p02_3_1.add_run(' ( euro ' + numero_lettere +' e ' )
                #     p02_3_1.add_run(numero_decimali + ' )')
                # else: # se DIRITTO DI PROPRIETA'
                    
                p02_3_1.add_run('''L'accettazione dell'importo calcolato, ''')
                    # p02_3_1.add_run("%s" % accettazione.data_accettazione.strftime('%d/%m/%Y')).bold=True
                    # p02_3_1.add_run(' prot. ' + accettazione.prot_gen +'; ')
                p02_3_1.add_run('unitamente al pagamento del corrispettivo effettuato tramite piattaforma PagoPA con IUV ')
                p02_3_1.add_run(accettazione.iuv)
                p02_3_1.add_run(', è stata comunicata con protocollo generale n. '+ accettazione.prot_gen + ' in data '+"%s" % accettazione.data_accettazione.strftime('%d/%m/%Y')+'.')
                   
                    # numero_lettere = (num2words(tot_dovuto , lang='it'))
                    # lung = len(str(tot_dovuto))-2
                    
                    # numero_decimali = str(tot_dovuto)[lung:]
                    # print(numero_lettere , lung)
                    # p02_3_1.add_run(' ( ' + numero_lettere +' e ' )
                    # p02_3_1.add_run(numero_decimali + ' )')

            p04 = document.add_paragraph()
            p04.paragraph_format.first_line_indent  = Inches(0.5)
            p04.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p04.paragraph_format.space_after = Pt(4)
            
            p04.add_run('- Sulla base della struttura organizzativa, alla U.O.6.0.1 - Servizi amministrativi e sicurezza sui luoghi di lavoro')
            p04.add_run(' è assegnata la responsabilità dell\'istruttoria e di ogni altro adempimento inerente il presente procedimento, con esclusione dell\'adozione del provvedimento finale, che resta di competenza del Dirigente;')

            p04_1 = document.add_paragraph()
            p04_1.paragraph_format.first_line_indent  = Inches(0.5)
            p04_1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p04_1.paragraph_format.space_after = Pt(4)

            p04_1.add_run('- Nel corso dell\'istruttoria, oltre che ai fini della adozione del presente provvedimento, non sono ')
            p04_1.add_run('state segnalate o rilevate, in capo a chi vi ha preso parte, situazioni - effettive o potenziali - di conflitto di interesse;')

            
            p04_2 = document.add_paragraph()
            # p04_2.paragraph_format.first_line_indent  = Inches(0.5)
            p04_2.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p04_2.paragraph_format.space_after = Pt(4)

            p04_2.add_run('VISTI', style="CduStyle").bold=True

            p5 = document.add_paragraph()
            p5.paragraph_format.left_indent  = Inches(0.5)
            p5.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p5.paragraph_format.space_after = Pt(4)

            p5.add_run('- artt. 107 e 147 bis, comma 1 del D.Lgs 267/2000;')

            p5_1 = document.add_paragraph()
            p5_1.paragraph_format.left_indent  = Inches(0.5)
            p5_1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p5_1.paragraph_format.space_after = Pt(4)

            p5_1.add_run('- art. 4, comma 2 del D.Lgs 165/2001; ')

            p5_2 = document.add_paragraph()
            p5_2.paragraph_format.left_indent  = Inches(0.5)
            p5_2.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p5_2.paragraph_format.space_after = Pt(4)

            p5_2.add_run('- art. 6 bis della Legge 241/1990; ')

            p5_3 = document.add_paragraph()
            p5_3.paragraph_format.left_indent  = Inches(0.5)
            p5_3.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p5_3.paragraph_format.space_after = Pt(4)

            p5_3.add_run('- La delibera di Consiglio Comunale n. 108 del 27/12/2024, "Approvazione nota di aggiornamento al DUP 2025-2027"; ')

            p5_4 = document.add_paragraph()
            p5_4.paragraph_format.left_indent  = Inches(0.5)
            p5_4.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p5_4.paragraph_format.space_after = Pt(4)

            p5_4.add_run('- La delibera di Consiglio Comunale n. 109 del 27/12/2024, "Approvazione bilancio di previsione 2025-2027 e relativi allegati"; ')

            p5_5 = document.add_paragraph()
            p5_5.paragraph_format.left_indent  = Inches(0.5)
            p5_5.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p5_5.paragraph_format.space_after = Pt(4)

            p5_5.add_run('- La delibera di Consiglio Comunale n. 52 del 27/02/2024, "P.E.G. 2024-2026: Approvazione e dotazione finanziaria"; ')

            p5_6 = document.add_paragraph()
            p5_6.paragraph_format.left_indent  = Inches(0.5)
            p5_6.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p5_6.paragraph_format.space_after = Pt(4)

            p5_6.add_run('- Il Piano Triennale di prevenzione della corruzione e della trasparenza \
(P.T.P.C.T. 2024-2026), approvato con Deliberazione di Giunta Comunale n. 147 del 30/04/2024, quale\
 allegato del P.I:A.O. 2024-2026; ')

            p6 = document.add_paragraph()
            p6.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p6.paragraph_format.space_before = Pt(8)
            p6.paragraph_format.space_after = Pt(8)

            p6.add_run('DETERMINA',style="CduStyle").bold=True

            # PUNTO 1
            print('kljòlaf354354af4',conv.tipo_diritto)
            if conv.tipo_diritto =='Superficie':
                p7 = document.add_paragraph()
                # p7.paragraph_format.first_line_indent  = Inches(0.5)
                p7.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                p7.add_run('''1) Di approvare la cessione a''')
            else:
                p7 = document.add_paragraph()
                # p7.paragraph_format.first_line_indent  = Inches(0.5)
                p7.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                p7.add_run('''1) Di approvare la rimozione dei vincoli di cui all'art. 35, \
commi 15, 16, 17 e 18 della Legge 865/1971 contenuti nella convenzione di cui in premessa \
relativamente all\'alloggio di proprietà di ''')
                

            if tot_richiedenti :
                
                
                
                # verifico se maschio o femmina 
                # prima verifico che sia presente il codice fiscale
                tot=richiedenti.count()
                print('tot_0',tot) # serve per determinare la presenza della virgola tra i soggetti
                for r in richiedenti:
                    tot = tot - 1
                    print ('tot',tot)
                    # print(r.id)
                    soggetto = Soggetto.objects.get(id=r.soggetto_id)
                    if soggetto.codice_fiscale and len(soggetto.codice_fiscale) == 16:
                        # print ('c.f.',soggetto.codice_fiscale)
                        sesso_cf = int(soggetto.codice_fiscale[9:11])
                        print('sesso ',sesso_cf)
                        if int(sesso_cf)>40:
                                nascita =' nata a ' + soggetto.comune_nascita.title() + ' il ' + "%s" % soggetto.data_nascita.strftime('%d/%m/%Y')
                                illa =  str.upper(soggetto.cognome) +''' '''+ str.upper(soggetto.nome) + ''' (c.f. '''+ str.upper(soggetto.codice_fiscale)+ ''')'''
                                
                                # titolo = ''' proprietaria '''
                        if int(sesso_cf)<=40:
                                nascita =' nato a ' + soggetto.comune_nascita.title() + ' il ' + "%s" % soggetto.data_nascita.strftime('%d/%m/%Y')
                                illa = str.upper(soggetto.cognome) + ''' ''' + str.upper(soggetto.nome) + ''' (c.f. '''+ str.upper(soggetto.codice_fiscale)+ ''')'''
                                # titolo = ''' proprietario '''
                        illa_corto = str.upper(soggetto.cognome) +''' '''+ str.upper(soggetto.nome)
                    
                       
                            
                    else :
                        print('c.f.---- stokazzengers')
                        pass

                    p7.add_run(''' ''' + str(illa_corto))
                    if tot > 0:
                        p7.add_run(' e ')
                

                if conv.tipo_diritto=='Proprietà':
                    # p7.add_run( ''', in ragione della quota millesimale pari a ''' + str(round(conv.millesimi,3)) + ''' millesimi della piena proprietà dell\' area rappresentata al N.C.T.R. - ''')
                    # # p7.add_run(str(round(conv.millesimi,3))).bold=True
                    # # p7.add_run(''' millesimi di piena proprietà dell\'area rappresentata al N.C.T.R., ''')
                    # p7.add_run(lista_terreni).bold=True
                    p7.add_run(''' identificato al N.C.E.U. come sottoindicato;''')

                else:
                    p7.add_run(''', della piena proprietà dell\' area rappresentata al catasto terreni al ''')
                    p7.add_run(lista_terreni).bold=True
                    p7.add_run(''' in ragione della quota millesimale spettante approvando altresì l\'eliminazione dei vincoli di prezzo massimo di vendita e di canone massimo di locazione \
afferente le unità immobiliari sottoindicate; ''')
                p7_1 = document.add_paragraph()
                # p7.paragraph_format.first_line_indent  = Inches(0.5)
                p7_1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                p7_1.add_run('---------------------DESCRIZIONE IMMOBILI -------------------')
                # p7.add_run( ''' , come da schema di contratto allegato quale parte integrante;''')
                # p7.add_run( ''' , come da schema di contratto allegato quale parte integrante, approvando altresì l\'eliminazione dei vincoli di prezzo massimo di vendita e di canone massimo di locazione afferenti l\'alloggio;''')
                # p7.add_run(''' come meglio descritto in premessa e nello schema di contratto allegato quale parte integrante;''')
            # PUNTO 2
            
            
#             p8 = document.add_paragraph()
#             p8.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
#             p8.add_run('''2) Di dare atto  che quanto stabilito al punto 1) costituisce parziale modifica della Convenzione stipulata tra\
#  il Comune di Carrara e ''')
#             p8.add_run(str.upper(coop.cognome)).bold=True
#             p8.add_run(''' a rogito ''' + str(conv.notaio) + ''' del ''' + "%s" % conv.data_atto.strftime('%d/%m/%Y') +''' ''' +  str(conv.atto)+''';''')
            
            # PUNTO 2

            p9 = document.add_paragraph()
            p9.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p9.add_run('''2) Di accertare l\'introito di ''')
            # p9.add_run('''€ ''').bold=True
            p9.add_run().bold=True

           
                        
            if tot_dovuto :
                p9.add_run(' € ' + str(tot_dovuto)).bold=True
                numero_lettere = (num2words(tot_dovuto , lang='it'))
                lung = len(str(tot_dovuto))-2
                numero_decimali = str(tot_dovuto)[lung:]
                p9.add_run(' (diconsi euro ' + numero_lettere +'/' )
                p9.add_run(numero_decimali + ' )')
                if conv.tipo_diritto=='Superficie':
                    p9.add_run(''', quale corrispettivo per la trasformazione del diritto di superficie in proprietà e l'eliminazione dei vincoli convenzionali afferenti le UIU di proprietà di ''')
                else :
                    p9.add_run(''', quale corrispettivo per l'eliminazione dei vincoli convenzionali afferenti le UIU di proprietà di ''')
                     
                for r in richiedenti:
                    tot = tot - 1
                    print ('tot',tot)
                    # print(r.id)
                    soggetto = Soggetto.objects.get(id=r.soggetto_id)
                    if soggetto.codice_fiscale and len(soggetto.codice_fiscale) == 16:
                        # print ('c.f.',soggetto.codice_fiscale)
                        sesso_cf = int(soggetto.codice_fiscale[9:11])
                        print('sesso ',sesso_cf)
                        if int(sesso_cf)>40:
                                nascita =' nata a ' + soggetto.comune_nascita.title() + ' il ' + "%s" % soggetto.data_nascita.strftime('%d/%m/%Y')
                                illa =  str.upper(soggetto.cognome) +''' '''+ str.upper(soggetto.nome) + ''' (c.f. '''+ str.upper(soggetto.codice_fiscale)+ ''')'''
                                # titolo = ''' proprietaria '''
                        if int(sesso_cf)<=40:
                                nascita =' nato a ' + soggetto.comune_nascita.title() + ' il ' + "%s" % soggetto.data_nascita.strftime('%d/%m/%Y')
                                illa = str.upper(soggetto.cognome) + ''' ''' + str.upper(soggetto.nome) + ''' (c.f. '''+ str.upper(soggetto.codice_fiscale)+ ''')'''
                                # titolo = ''' proprietario '''
                       
                    
                       
                            
                    else :
                        print('c.f.---- stokazzengers')
                        pass

                    p9.add_run(''' ''' + str(illa) )
#               p9.add_run(''', come indicato in premessa, quale corrispettivo per la trasformazione del diritto di superficie \
# in proprietà e l'eliminazione dei vincoli convenzionali al capitolo ''')
           
            p9.add_run(''' al Capitolo 40400.02.0300''').bold=True
            p9.add_run(''' denominato ''')
            p9.add_run('''\"proventi per trasformazione diritto di superficie in piena proprietà ed affrancazione di vincoli convenzionali\"''').italic=True
            p9.add_run(''' del PEG 2024, dando atto che lo stesso è esigibile nel medesimo esercizio;''')


            p10 = document.add_paragraph()
            p10.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p10.add_run('''3) Di significare che, nel caso di controversia giudiziale, la materia \
oggetto del presente provvedimento rientra nella giurisdizione del TAR e che inoltre è esperibile il \
ricorso amministrativo per via straordinaria al Capo dello Stato, in entrambi i casi, nei termini ed \
alle condizioni previste dal D.Lgs. 104/2010 e dal D.P.R. 1199/1971. ''')
            p11 = document.add_paragraph()
            p11.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p11.add_run('''4) Di dare atto che il presente provvedimento verrà pubblicato all’albo pretorio , e sul sito
istituzionale dell’Ente in “Amministrazione Trasparente”- Sezione Provvedimenti-
Provvedimenti dirigenti –ai sensi del D.Lgs n. 33/2013 e ss.mm.ii.; ''')
            
            p12 = document.add_paragraph()
            p12.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p12.add_run('''5) Di dare atto-ai sensi dell’art. 12 e ss Regolamento UE 679/2016 e del D.Lgs. n. 196/2003, come
modificato dal D.Lgs. n. 101/2018- che i dati personali raccolti nel presente atto sono trattati in
modo lecito, corretto e trasparente per finalità istituzionali e/o per obblighi di legge e/o
precontrattuali o contrattuali. Il trattamento degli stessi avviene ad opera di soggetti impegnati alla
riservatezza, con logiche correlate alle finalità e, comunque, in modo da garantire la sicurezza e la
protezione dei dati. Per ogni maggiore informazione circa il trattamento dei dati personali e l’esercizio 
dei diritto di cui agli art. 15 e ss Reg. UE 679/2016, l’interessato potrà visitare la sezione privacy del 
sito istituzionale, al seguente indirizzo: http://web.comune.carrara.ms.it/pagina562_privacy.html il titolare 
del trattamento è il Comune di Carrara.''')


            # p06=document.add_paragraph()
            # p06.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            # # p06.paragraph_format.first_line_indent  = Inches(0.5)
            # p06.paragraph_format.space_after = Pt(2)
            # p06.paragraph_format.space_before = Pt(2)
            
            # p06.add_run('''Distinti saluti      ''')


            p07 = document.add_paragraph()
            p07.alignment = WD_ALIGN_PARAGRAPH.LEFT
            # p06.paragraph_format.first_line_indent  = Inches(0.5)
            p07.paragraph_format.space_after = Pt(2)
            p07.paragraph_format.space_before = Pt(2)

            p07.add_run('''Carrara, data della sottoscrizione digitale''')

            p07 = document.add_paragraph()
            p07.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            # p07.paragraph_format.first_line_indent  = Inches(0.5)
            p07.paragraph_format.space_after = Pt(2)
            p07.paragraph_format.space_before = Pt(2)
            
            p07.add_run('''Il Dirigente
Ing Luca Amadei''')

            p08 = document.add_paragraph()
            p08.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p08.paragraph_format.space_before = Pt(10)
            p08.add_run('''Documento firmato digitalmente ai sensi e per gli effetti di cui agli 
art.21, 23, 23bis e 23ter del decreto legislativo n. 82 del 7 marzo 2005 e s.m.i. - 
Codice dell'Amministrazione digitale. Tale documento informatico è memorizzato digitalmente su 
banca dati del Comune di Carrara.''', style='NormalStyle').italic=True


# Prepare document for download        
        # -----------------------------
            f = BytesIO()
            document.save(f)
            length = f.tell()
            f.seek(0)
            response = HttpResponse(
                f.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
            response['Content-Disposition'] = 'attachment; filename=' + docx_title
            response['Content-Length'] = length            
            return response




def SchemaConv(request,id):
           
    
       
        # recupera le pratiche della cooperativa
            pratica = Pratica.objects.filter(id=id)[0]
            print('pratica',pratica)
            conv = IstrConv.objects.get(pratica_id=id)
            
             # ESTRAE le particelle interessate e le conta
            particelle = Cataprat.objects.filter(pratica_id=pratica.id) 
            tot_particelle = particelle.count()
            # print(particelle)
            
            foglio_pre="" # imposta a blank il foglio precedente
            lista =[] # lista le particelle nella pratica, compresi eventuali subalterni
            lista_terreni = [] # lista le particelle SENZA i subalterni

            if tot_particelle:
                    # paragraph = document.add_paragraph()
                    for p in particelle:
                            mappali ={}
                            particelle = {}

                            part = Particella.objects.get(id=p.particella_id)


                            # AI duckduck.org
                            # utilizzando il modulo django-docx posso inserire una immagine estratta utilizzando un link?
                            from docx import Document
                            from docx.shared import Inches
                            
                            from PIL import Image
                            from io import BytesIO
                            from django.core.files.temp import NamedTemporaryFile
                            fg = part.foglio
                            map = part.mappale
                            sub = p.subalterno
                            # URL della pagina web
                            url = 'http://qgis-server/ubucomu/catasto/nctr_results_ana.php?f='+ fg + '&m=' + map
                            print('url',url)
                            # # Configura le opzioni del browser
                            # options = Options()
                            # options.add_argument('--headless')  # esegui il browser in modalità headless
                            # options.add_argument('--window-size=1920,1080')  # impostare la dimensione della finestra

                            # # Crea un'istanza del browser
                            # driver = webdriver.Chrome(options=options)

                            # # Apri la pagina web
                            # driver.get(url)

                            # # Cattura lo screenshot della pagina
                            # screenshot = driver.get_screenshot_as_png()

                            # # Salva lo screenshot in un file temporaneo
                            # tmp_file = NamedTemporaryFile(suffix='.png')
                            # tmp_file.write(screenshot)
                            # tmp_file.flush()

                            # # Apri l'immagine con PIL
                            # image = Image.open(tmp_file.name)

                            # # Ridimensiona l'immagine se necessario
                            # image.thumbnail((1024, 768))  # impostare la dimensione massima dell'immagine

                            # # Salva l'immagine in un file temporaneo
                            # tmp_file_image = NamedTemporaryFile(suffix='.png')
                            # image.save(tmp_file_image.name)

                            # # Crea un documento Word
                            # document = Document()

                            # # Aggiungi l'immagine al documento
                            # document.add_picture(tmp_file_image.name, width=Inches(5))

                            # # Salva il documento
                            # document.save('documento.docx')


                            
                            print(part)
                            if foglio_pre==part.foglio:
                                particelle = ', ' + part.mappale 
                                mappali = ', ' + part.mappale 
                                if p.subalterno !='-':
                                      mappali = mappali + ' sub. '+str(p.subalterno)+', '
                            else:
                                particelle = 'fg ' + part.foglio + ' map ' + part.mappale
                                mappali = 'fg ' + part.foglio + ' map ' + part.mappale
                                if p.subalterno !='-':
                                      mappali = mappali + ' sub '+str(p.subalterno)
                            foglio_pre= part.foglio
                            lista.append(mappali)
                            lista_terreni.append(particelle)
                    print(lista, foglio_pre, part.foglio)
                    print(lista_terreni)
                    #document.add_paragraph(lista)

            atto = 'schema_convenzione_'+str(conv.tipo_diritto)+ '_' +str(pratica.prot_gen)  +'_' + "%s" % pratica.data_prot_gen.strftime('%Y%m%d') +'.docx'
        #     print('atto',atto)
            document = Document()
            # imposta A4 verticale e margini
            section = document.sections[0]
            section.page_height = Mm(297)
            section.page_width = Mm(210)
            section.left_margin = Mm(20)
            section.right_margin = Mm(20)
            section.top_margin = Mm(10)
            section.bottom_margin = Mm(12)
            # section.header_distance = Mm(10)
            section.footer_distance = Mm(12.7)
            
            paragraph = document.add_paragraph()
            # Selecting a section of the document

            section = document.sections[0]
            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('FooterStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(7)
            obj_font.name = 'Times New Roman'

        #   IMPOSTA IL FOOTER
            footer=section.footer

            f1=footer.add_paragraph()
            f1.paragraph_format.space_after = Pt(0)
            f1.paragraph_format.space_before = Pt(0)
            f1.add_run("P.za due giugno,1 54033 - Carrara (MS) PEC : comune.carrara@postecert.it", style = 'FooterStyle')

            # f2=footer.add_paragraph()
            # f2.paragraph_format.space_after = Pt(0)
            # f2.paragraph_format.space_before = Pt(0)
            # f2.add_run("geom. Carlo Alberto Nicolini - 0585 641252 - carloalberto.nicolini@comune.carrara.ms.it", style = 'FooterStyle')

            # f3=footer.add_paragraph()
            # f3.paragraph_format.space_after = Pt(0)
            # f3.paragraph_format.space_before = Pt(0)
            # f3.add_run("geom. Carlo Alberto Nicolini - 0585 641252 - carloalberto.nicolini@comune.carrara.ms.it", style = 'FooterStyle')
        
        #   IMPOSTA GLI STILI DEI SINGOLI PARAGRAFI
            # document.add_paragraph()
            font = document.styles['Normal'].font
            font.size=Pt(11)
            font.name='Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('NormalStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(10)
            obj_font.name = 'Times New Roman'

            
            
            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('SottoHeaderStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(11)
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('HeaderStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(9)
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('CduStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(14)
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('NumCduStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(11)
            obj_font.name = 'Times New Roman'


            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('NumCduStyleItalic', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = True
            obj_font.size = Pt(9)
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('DprStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = True
            obj_font.size = Pt(8)
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('ParticellaStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = False
            obj_font.underline = WD_UNDERLINE.SINGLE
            obj_font.bold=True
            obj_font.size = Pt(11)
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('PianoStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = True
            obj_font.size = Pt(10)
            obj_font.bold=False
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('DestinazioneStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = False
            obj_font.size = Pt(9)
            obj_font.name = 'Times New Roman'


            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('CertificaStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = False
            obj_font.bold=True
            obj_font.size = Pt(14)
            obj_font.name = 'Times New Roman'
            

            
            # Changing the orientation to landscape
            section.orientation = WD_ORIENT.LANDSCAPE

            paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW

            docx_title=atto
            
            # Inserisci l'immagine nel documento
            # https://www.shibutan-bloomers.com/python_library_python-docx-2_en/7091/
            # CON ChatGpt

            # Definisci il percorso dell'immagine
            image_name = 'logo_decorato.png'
            image_path = os.path.join('static/img/', image_name)

            # Inserisci l'immagine nel documento
            # paragraph = document.add_paragraph()
            # paragraph.paragraph_format.space_before = Pt(1)
            run = paragraph.add_run()
            run.add_picture(image_path, width=Inches(1.4))

            # Posiziona centralmente l'immagine
            paragraph_format = paragraph.paragraph_format
            paragraph_format.alignment = 1
            

            p0 = document.add_paragraph()
            p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p0.paragraph_format.space_before = Pt(0)
            p0.paragraph_format.space_after = Pt(1)
            p0.add_run('Settore 6 - Governo del territorio',style = 'NormalStyle').bold=True

            p0 = document.add_paragraph()
            p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p0.paragraph_format.space_before = Pt(0)
            p0.paragraph_format.space_after = Pt(1)
            p0.add_run('Servizio 6.1 - Urbanistica e edilizia privata - U.O. 6.1.2 SUEP e vigilanza abusivismo',style = 'HeaderStyle')
            
            p0_1 = document.add_paragraph()
            p0_1.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p0_1.paragraph_format.space_after = Pt(10)
            p0_1.add_run('',style = 'HeaderStyle')
            # ESTRAE I RICHIEDENTI

            anaprat = Anaprat.objects.filter(pratica_id=id)
            costruttore = Anaprat.objects.get(Q(pratica_id=id) & Q(tipo_id__exact = 9))
            richiedenti = Anaprat.objects.filter(Q(pratica_id=id) & Q(tipo_id__exact = 1))
            tot_richiedenti = richiedenti.count()
            
            coop = Soggetto.objects.get(id=costruttore.soggetto_id)
            

            ####################################
            #      OGGETTO
            ###################################
            
            
            
            
            if conv.tipo_diritto == 'Superficie':

                p2_4 = document.add_paragraph()
                p2_4.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                p2_4.paragraph_format.space_after = Pt(1)
                p2_4.add_run(str('''OGGETTO : TRASFORMAZIONE DEL DIRITTO DI SUPERFICIE IN PIENA PROPRIETA' \
E AFFRANCAZIONE DEI VINCOLI CONVENZIONALI, AI SENSI DELL\'ART. 31, COMMA 45 E SEGUENTI, DELLA LEGGE 448/98 PER\
 ALLOGGIO REALIZZATO IN AREA P.E.E.P. UBICATO IN ''') ).bold=True
                p2_4.add_run(str.upper(pratica.street.street) + ', '+str.upper(pratica.housenumber)).bold=True
                p2_4.add_run(''' - PARZIALE MODIFICA DELLA CONVENZIONE STIPULATA TRA IL COMUNE DI CARRARA E ''' ).bold=True
                p2_4.add_run(str.upper(coop.cognome)  ).bold=True
                p2_4.add_run(''' IN DATA ''' + "%s" % conv.data_atto.strftime('%d/%m/%Y') +'''.''').bold=True
            else :
                p2_4 = document.add_paragraph()
                p2_4.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                p2_4.paragraph_format.space_after = Pt(16)
                p2_4.add_run(str('''OGGETTO : ELIMINAZIONE VINCOLI DI INALIENABILITA' EX ARTICOLO 35, COMMI 15, 16, 17 E 18 \
DELLA LEGGE N. 865/1971 A PARZIALE MODIFICA DELLA CONVENZIONE  STIPULATA TRA IL COMUNE DI CARRARA E ''') ).bold=True
                p2_4.add_run(str.upper(coop.cognome) ).bold=True
                p2_4.add_run(''' IN DATA ''' + "%s" % conv.data_atto.strftime('%d/%m/%Y') +'''.''').bold=True

                # p2_4_0 = document.add_paragraph()
                # p2_4_0.alignment = WD_ALIGN_PARAGRAPH.LEFT
                # p2_4_0.add_run('''PRESA D\'ATTO AVVENUTO PAGAMENTO ED APPROVAZIONE SCHEMA DI CONTRATTO.''' )
                p2_4.add_run(''' - APPROVAZIONE SCHEMA DI CONVENZIONE E ACCERTAMENTO INTROITO.''' ).bold=True

           
            if conv.tipo_diritto == 'Superficie':
                    tot_dovuto = conv.valore_dirsup+conv.crv_uiu
            else:
                    tot_dovuto = conv.valore_dirsup


            p2_4_0 = document.add_paragraph()
            p2_4_0.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p2_4_0.add_run(' ')

            p2_4_1 = document.add_paragraph()
            p2_4_1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p2_4_1.add_run('''Il giorno XX mese XXXXXXX anno XXXX, in Carrara presso ________________________ \
davanti a me Dott. XXXXXXXXXXXXXX, Notaio in Carrara, con studio in XXXXXXXXXXXXXXXXXXXXX, iscritto presso il collegio notarile di XXXXX, \
rinunciando di comune accordo e con il consenso del sottoscritto all\'assistenza dei testimoni, sono presenti i signori :''' )

### soggetti coinvolti

            p2_4_2 = document.add_paragraph()
            p2_4_2.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p2_4_2.paragraph_format.space_after = Pt(1)
            p2_4_2.add_run('- ING. LUCA AMADEI').bold=True

            if tot_richiedenti :
                
                             
                # verifico se maschio o femmina 
                # prima verifico che sia presente il codice fiscale
                for r in richiedenti:
                    # print(r.id)
                    soggetto = Soggetto.objects.get(id=r.soggetto_id)
                    if soggetto.codice_fiscale and len(soggetto.codice_fiscale) == 16:
                        # print ('c.f.',soggetto.codice_fiscale)
                        sesso_cf = int(soggetto.codice_fiscale[9:11])
                        print('sesso ',sesso_cf)
                        if int(sesso_cf)>40:
                                nascita =' nata a ' + soggetto.comune_nascita.title() + ' il ' + "%s" % soggetto.data_nascita.strftime('%d/%m/%Y')
                                illa = ''' la sig.ra '''  + str.upper(soggetto.cognome) +''' '''+ str.upper(soggetto.nome) + ''' (c.f. '''+ str.upper(soggetto.codice_fiscale)+ ''')'''
                                titolo = ''' proprietaria '''
                        if int(sesso_cf)<=40:
                                nascita =' nato a ' + soggetto.comune_nascita.title() + ' il ' + "%s" % soggetto.data_nascita.strftime('%d/%m/%Y')
                                illa = ''' il sig. ''' + str.upper(soggetto.cognome) + ''' ''' + str.upper(soggetto.nome) + ''' (c.f. '''+ str.upper(soggetto.codice_fiscale)+ ''')'''
                                titolo = ''' proprietario '''
                                                    
                    else :
                        print('c.f.---- stokazzengers')
                        pass
                    
                    p2_4_2 = document.add_paragraph()
                    p2_4_2.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                    p2_4_2.paragraph_format.space_after = Pt(1)

                    p2_4_2.add_run('- ' +str.upper(soggetto.cognome) + ''' ''' + str.upper(soggetto.nome)).bold=True
                    p2_4_2.add_run(nascita + ', residente in ' + str.title(soggetto.comune_residenza) +' '+ str.title(soggetto.addr))
                    p2_4_2.add_run(' C.F. '+ str.upper(soggetto.codice_fiscale))





            p2_4_3 = document.add_paragraph()
            p2_4_3.paragraph_format.space_after = Pt(4)
            p2_4_3.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            
            # diritto di superficie
            if conv.tipo_diritto == 'Superficie':
               
                print('tot richiedenti', tot_richiedenti)
                
                p2_4_3.add_run('''detti comparenti, della cui identità personale, qualifica e poteri sono certo, mi chiedono di ricevere il presente atto;''')
                # p2_4_4 = document.add_paragraph()
                # p2_4_4.paragraph_format.first_line_indent  = Inches(0.5)
                # p2_4_4.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            
            # diritto di proprietà

            else: 
                print('tot richiedenti-2', tot_richiedenti)
                
                p2_4_3.add_run('''- con Delibera del Consiglio comunale n. 56 del 17 giugno 2024, il Comune di Carrara ha stabilito i valori delle aree PEEP e dato \
atto che i vincoli di cui all\'art. 35, commi 15, 16, 17 e 18 della L. 865/1971, relativamente alle Convenzioni stipulate prima \
dell\'entrata in vigore della Legge 179/1992, possono essere rimossi su apposita istanza, previo pagamento del corrispettivo di cui all\' art.31 \
comma 48 della Legge 448/1998 essendo ormai trascorsi i 20 anni dalla stipula delle convenzioni stesse;''')
            
            
            
            
            p2_4_4 = document.add_paragraph()
            # p2_4_4.paragraph_format.first_line_indent  = Inches(0.5)
            p2_4_4.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p2_4_4.paragraph_format.space_after = Pt(4)

            # secondo paragrafo
            p2_4_4.add_run('''PREMESSO''').bold=True

            p2_4_4_1 = document.add_paragraph()
            # p2_4_4.paragraph_format.first_line_indent  = Inches(0.5)
            p2_4_4_1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

            # secondo paragrafo
            p2_4_4_1.add_run('''DESCRIZIONE PREMESSA.... a manina''')



            p2_4_5 = document.add_paragraph()
            # p2_4_4.paragraph_format.first_line_indent  = Inches(0.5)
            p2_4_5.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p2_4_5.paragraph_format.space_after = Pt(1)
            p2_4_5.add_run('Tanto premesso').bold=True

            p2_4_6 = document.add_paragraph()
            # p2_4_4.paragraph_format.first_line_indent  = Inches(0.5)
            p2_4_6.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p2_4_6.paragraph_format.space_after = Pt(1)

            p2_4_6.add_run('perchè formi parte integrante e sostanziale del presente atto').bold=True

            p2_4_7 = document.add_paragraph()
            # p2_4_4.paragraph_format.first_line_indent  = Inches(0.5)
            p2_4_7.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p2_4_7.paragraph_format.space_after = Pt(4)

            p2_4_7.add_run('CONVENGONO QUANTO SEGUE').bold=True




#             if tot_richiedenti :
                
                
                
#                 # verifico se maschio o femmina 
#                 # prima verifico che sia presente il codice fiscale
#                 for r in richiedenti:
#                     # print(r.id)
#                     soggetto = Soggetto.objects.get(id=r.soggetto_id)
#                     if soggetto.codice_fiscale and len(soggetto.codice_fiscale) == 16:
#                         # print ('c.f.',soggetto.codice_fiscale)
#                         sesso_cf = int(soggetto.codice_fiscale[9:11])
#                         print('sesso ',sesso_cf)
#                         if int(sesso_cf)>40:
#                                 nascita =' nata a ' + soggetto.comune_nascita.title() + ' il ' + "%s" % soggetto.data_nascita.strftime('%d/%m/%Y')
#                                 illa = ''' la sig.ra '''  + str.upper(soggetto.cognome) +''' '''+ str.upper(soggetto.nome) + ''' (c.f. '''+ str.upper(soggetto.codice_fiscale)+ ''')'''
#                                 titolo = ''' proprietaria '''
#                         if int(sesso_cf)<=40:
#                                 nascita =' nato a ' + soggetto.comune_nascita.title() + ' il ' + "%s" % soggetto.data_nascita.strftime('%d/%m/%Y')
#                                 illa = ''' il sig. ''' + str.upper(soggetto.cognome) + ''' ''' + str.upper(soggetto.nome) + ''' (c.f. '''+ str.upper(soggetto.codice_fiscale)+ ''')'''
#                                 titolo = ''' proprietario '''
                        
                    
                       
                            
#                     else :
#                         print('c.f.---- stokazzengers')
#                         pass

#                     p2_4_4.add_run(''' ''' + str(illa) + ''', ''' + str(nascita))

#                 if tot_richiedenti == 1:
#                     p2_4_4.add_run(''' ''' + str(titolo) )
#                 else:
#                     p2_4_4.add_run(''' proprietari ''' )
#                 p2_4_4.add_run(''' di alloggio di civile abitazione ubicato in ''')
#                 p2_4_4.add_run(str.upper(pratica.street.street) + ', '+str.upper(pratica.housenumber)+''', ''').bold=True
#                 p2_4_4.add_run('''realizzato da ''')
#                 p2_4_4.add_run( coop.cognome).bold=True
#                 p2_4_4.add_run( ''' su area ''')
#                 if conv.tipo_diritto == 'Superficie':
#                     p2_4_4.add_run('''concessa in diritto di superficie, ''')
#                 else:
#                     p2_4_4.add_run('''ceduta in diritto di proprietà, ''')
#                 if tot_richiedenti == 1:
#                     p2_4_4.add_run('''ha chiesto ''')
#                 else:
#                     p2_4_4.add_run('''hanno chiesto ''')
                
#                 p2_4_4.add_run('''con istanza del ''')
#                 p2_4_4.add_run("%s" % pratica.data_prot_gen.strftime('%d/%m/%Y')).bold=True
#                 p2_4_4.add_run(''' prot. gen. n. ''')
#                 p2_4_4.add_run( pratica.prot_gen ).bold=True             
#                 p2_4_4.add_run(''' di poter procedere ''')  

#                 # se DIRITTO DI SUPERFICIE
#                 if conv.tipo_diritto == 'Superficie':
#                     p2_4_4.add_run('''alla trasformazione del diritto di superficie in piena proprietà, nonchè alla eliminazione \
# dei vincoli relativi alla circolazione del bene ed alla libera determinazione del prezzo di vendita, con il pagamento del corrispettivo \
# di cui alla delibera C.C. n. 56/2024; ''')
                
#                 # se DIRITTO DI PROPRIETA'
#                 else:
#                     p2_4_4.add_run('''ai sensi dell\'art. 31, commi 46 e 48 della L. 448/1998 alla eliminazione dei vincoli contenuti nella Convenzione \
# a suo tempo stipulata tra l\'Ente e la predetta cooperativa edilizia ''')
#                     p2_4_4.add_run('''(atto ''' + str(conv.notaio) + ''' del ''' + "%s" % conv.data_atto.strftime('%d/%m/%Y')+ ''' ''' + conv.atto + ''') ''')
#                     p2_4_4.add_run(''', impegnandosi a pagare al Comune di Carrara il corrispettivo stabilito a norma della citata disposizione di Legge;''')
                    
#                     p2_4_5 = document.add_paragraph()
#                     p2_4_5.paragraph_format.first_line_indent  = Inches(0.5)
#                     p2_4_5.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
#                     p2_4_5.paragraph_format.space_after = Pt(4)

#                     p2_4_5.add_run('''- L\'alloggio in questione, oltre a pertinenze ed aree condominiali, è rappresentato al N.C.E.U. al ''')
#                     p2_4_5.add_run(lista).bold=True
                    
#                 # se è superficie
#                 p3 = document.add_paragraph()
#                 p3.paragraph_format.first_line_indent  = Inches(0.5)
#                 p3.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
#                 p3.paragraph_format.space_after = Pt(4)
        
#                 if conv.tipo_diritto == 'Superficie':
                   

#                     p3.add_run('''- Per il predetto immobile, compreso pertinenze ed aree scoperte, censito al N.C.E.U. al ''')
#                     p3.add_run(lista).bold=True
#                     p3.add_run(''' ------ TABELLA CATASTALE ---------''')
#                     p3.add_run(''', l\'importo del corrispettivo per la trasformazione del diritto di superficie ''' )
#                     p3.add_run('''e l\'eliminazione dei vincoli di cui sopra, calcolato nel rispetto delle disposizioni dell'art 31, ''' )
#                     p3.add_run(''' comma 48 e 49-bis, della Legge 448/1998 e ss.mm.ii. e della citata Delibera di Consiglio Comunale, \
#     in riferimento alle quote millesimali di competenza ''' )
#                     p3.add_run('''(''' + str(round(conv.millesimi,3)) + '''/1000)''')
#                     p3.add_run(''' è il seguente :         ''')
                
#                 # se  proprietà 
#                 else:
                   

#                     p3.add_run('''- Per le predette unità immobiliari, a cui compete la quota millesimale di ''')
#                     p3.add_run(str(round(conv.millesimi,3)) + '''/1000''')
#                     p3.add_run(''', l\'importo del corrispettivo per la rimozione dei vincoli di cui all\'art. 31 comma 48 della Legge 448/1998''' )
#                     p3.add_run(''', è stato determinato in ''' )
#                     if tot_dovuto :
#                         p3.add_run(' € ' + str(tot_dovuto)).bold=True
#                         numero_lettere = (num2words(tot_dovuto , lang='it'))
#                         lung = len(str(tot_dovuto))-2
                        
#                         numero_decimali = str(tot_dovuto)[lung:]
#                         print(numero_lettere , lung)
#                         p3.add_run(' ( diconsi euro ' + numero_lettere +'/' )
#                         p3.add_run(numero_decimali + ' )')
#                     p3.add_run(''', con riferimento al valore delle aree stabilito con deliberazione di C.C. n. 56 del 17 giugno 2024; ''' )

                

#                 if conv.tipo_diritto == 'Superficie': # se DIRITTO DI SUPERFICIE
#                         p02_2_1 = document.add_paragraph()
#                         p02_2_1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
#                         # svincolo diritto di superficie
#                         primo_importo = Decimal(conv.valore_residuo) * Decimal(conv.millesimi) / 1000
#                         p02_2_1.add_run('- Importo complessivo per la trasformazione del diritto di superficie in proprietà ............................... € ', style='NormalStyle')
#                         p02_2_1.add_run( str(round(primo_importo,2)), style='NumCduStyleItalic').italic=True
                        
#                         # svincolo diritto di cessione ( superficie )
#                         secondo_importo = Decimal(conv.crv)* Decimal(conv.millesimi) / 1000
#                         p03_2_1 = document.add_paragraph()
#                         p03_2_1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
#                         # p03_2_1.add_run(str(primo_importo),  style='NumCduStyleItalic').bold=True
#                         p03_2_1.add_run('- Importo complessivo per l\' eliminazione dei vincoli convenzionali ......................................................... € ', style='NormalStyle')
#                         p03_2_1.add_run( str(round(secondo_importo,2)),  style='NumCduStyleItalic').italic=True

#                         p02_3 = document.add_paragraph()
#                         p02_3.alignment = WD_ALIGN_PARAGRAPH.RIGHT
#                         # p02_3.paragraph_format.space_after = Pt(0)
#                         # p02_3.paragraph_format.space_before = Pt(4)
#                         p02_3.add_run('Totale ..... € '+str(tot_dovuto),  style='NormalStyle').bold=True
                    

                        
                    
#                 # else : # nel caso sia eliminazione del vincolo di cessione PROPRIETA'
#                 #     pass

#                 # descrizione pagamenti
#                 accettazione = AccettaImporto.objects.get(convenzione_id = conv.id)
#                 if accettazione:
#                     comunicazione = 'comunicazione del ' + "%s" % accettazione.data_accettazione.strftime('%d/%m/%Y')
#                     print(comunicazione)
#                 else:
#                      print('nessuna accettazione presente')

#                 p02_3_1 = document.add_paragraph()
#                 p02_3_1.paragraph_format.first_line_indent  = Inches(0.5)
#                 p02_3_1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
#                 p02_3_1.paragraph_format.space_after = Pt(4)
                
#                 # if conv.tipo_diritto == 'Superficie': # se DIRITTO DI SUPERFICIE
                   
#                 #     p02_3_1.add_run('''- L'accettazione dell'importo dovuto ed il pagamento del corrispettivo € ''')
#                 #     p02_3_1.add_run(str(tot_dovuto)).bold=True
#                 #     numero_lettere = (num2words(tot_dovuto , lang='it'))
#                 #     lung = len(str(tot_dovuto))-2
                    
#                 #     numero_decimali = str(tot_dovuto)[lung:]
#                 #     print(numero_lettere , lung)
#                 #     p02_3_1.add_run(' ( euro ' + numero_lettere +' e ' )
#                 #     p02_3_1.add_run(numero_decimali + ' )')
#                 # else: # se DIRITTO DI PROPRIETA'
                    
#                 p02_3_1.add_run('''L'accettazione dell'importo calcolato, ''')
#                     # p02_3_1.add_run("%s" % accettazione.data_accettazione.strftime('%d/%m/%Y')).bold=True
#                     # p02_3_1.add_run(' prot. ' + accettazione.prot_gen +'; ')
#                 p02_3_1.add_run('unitamente al pagamento del corrispettivo effettuato tramite piattaforma PagoPA con IUV ')
#                 p02_3_1.add_run(accettazione.iuv)
#                 p02_3_1.add_run(', è stata comunicata con protocollo generale n. '+ accettazione.prot_gen + ' in data '+"%s" % accettazione.data_accettazione.strftime('%d/%m/%Y')+'.')
                   
#                     # numero_lettere = (num2words(tot_dovuto , lang='it'))
#                     # lung = len(str(tot_dovuto))-2
                    
#                     # numero_decimali = str(tot_dovuto)[lung:]
#                     # print(numero_lettere , lung)
#                     # p02_3_1.add_run(' ( ' + numero_lettere +' e ' )
#                     # p02_3_1.add_run(numero_decimali + ' )')

            p04 = document.add_paragraph()
            # p04.paragraph_format.first_line_indent  = Inches(0.5)
            p04.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p04.paragraph_format.space_after = Pt(2)
            
            p04.add_run('''Il Comune di Carrara, come rappresentato, consente la parziale modifica della Convenzione \
stipulata tra il Comune di Carrara e ''')
            p04.add_run('"'+ str.title(coop.cognome) + '"')

            p04.add_run(''' a rogito ''')
            p04.add_run(str(conv.notaio) + ' in data ' + "%s" % conv.data_atto.strftime('%d/%m/%Y') + '')

            p04_1 = document.add_paragraph()
            p04_1.paragraph_format.first_line_indent  = Inches(0.5)
            p04_1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p04_1.paragraph_format.space_after = Pt(4)

            p04_1.add_run('- Nel corso dell\'istruttoria, oltre che ai fini della adozione del presente provvedimento, non sono ')
            p04_1.add_run('state segnalate o rilevate, in capo a chi vi ha preso parte, situazioni - effettive o potenziali - di conflitto di interesse;')

            
            p04_2 = document.add_paragraph()
            # p04_2.paragraph_format.first_line_indent  = Inches(0.5)
            p04_2.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p04_2.paragraph_format.space_after = Pt(4)

            p04_2.add_run('VISTI', style="CduStyle").bold=True

            p5 = document.add_paragraph()
            p5.paragraph_format.left_indent  = Inches(0.5)
            p5.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p5.paragraph_format.space_after = Pt(4)

            p5.add_run('- artt. 107 e 147 bis, comma 1 del D.Lgs 267/2000;')

            p5_1 = document.add_paragraph()
            p5_1.paragraph_format.left_indent  = Inches(0.5)
            p5_1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p5_1.paragraph_format.space_after = Pt(4)

            p5_1.add_run('- art. 4, comma 2 del D.Lgs 165/2001; ')

            p5_2 = document.add_paragraph()
            p5_2.paragraph_format.left_indent  = Inches(0.5)
            p5_2.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p5_2.paragraph_format.space_after = Pt(4)

            p5_2.add_run('- art. 6 bis della Legge 241/1990; ')

            p5_3 = document.add_paragraph()
            p5_3.paragraph_format.left_indent  = Inches(0.5)
            p5_3.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p5_3.paragraph_format.space_after = Pt(4)

            p5_3.add_run('- La delibera di Consiglio Comunale n. 5 del 18/01/2024, "Nota di aggiornamento al DUP 2024-2026"; ')

            p5_4 = document.add_paragraph()
            p5_4.paragraph_format.left_indent  = Inches(0.5)
            p5_4.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p5_4.paragraph_format.space_after = Pt(4)

            p5_4.add_run('- La delibera di Consiglio Comunale n. 6 del 18/01/2024, "Approvazione bilancio di previsione 2024-2026 e relativi allegati"; ')

            p5_5 = document.add_paragraph()
            p5_5.paragraph_format.left_indent  = Inches(0.5)
            p5_5.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p5_5.paragraph_format.space_after = Pt(4)

            p5_5.add_run('- La delibera di Consiglio Comunale n. 52 del 27/02/2024, "P.E.G. 2024-2026: Approvazione e dotazione finanziaria"; ')

            p5_6 = document.add_paragraph()
            p5_6.paragraph_format.left_indent  = Inches(0.5)
            p5_6.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p5_6.paragraph_format.space_after = Pt(4)

            p5_6.add_run('- Il Piano Triennale di prevenzione della corruzione e della trasparenza \
(P.T.P.C.T. 2024-2026), approvato con Deliberazione di Giunta Comunale n. 147 del 30/04/2024, quale\
 allegato del P.I:A.O. 2024-2026; ')

            p6 = document.add_paragraph()
            p6.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p6.paragraph_format.space_before = Pt(8)
            p6.paragraph_format.space_after = Pt(8)

            p6.add_run('DETERMINA',style="CduStyle").bold=True

            # PUNTO 1
            if conv.tipo_diritto=='proprietà':
                p7 = document.add_paragraph()
                # p7.paragraph_format.first_line_indent  = Inches(0.5)
                p7.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                p7.add_run('''1) Di approvare la cessione a''')
                if tot_richiedenti :
                    
                    
                    
                    # verifico se maschio o femmina 
                    # prima verifico che sia presente il codice fiscale
                    tot=richiedenti.count()
                    print('tot_0',tot) # serve per determinare la presenza della virgola tra i soggetti
                    for r in richiedenti:
                        tot = tot - 1
                        print ('tot',tot)
                        # print(r.id)
                        soggetto = Soggetto.objects.get(id=r.soggetto_id)
                        if soggetto.codice_fiscale and len(soggetto.codice_fiscale) == 16:
                            # print ('c.f.',soggetto.codice_fiscale)
                            sesso_cf = int(soggetto.codice_fiscale[9:11])
                            print('sesso ',sesso_cf)
                            if int(sesso_cf)>40:
                                    nascita =' nata a ' + soggetto.comune_nascita.title() + ' il ' + "%s" % soggetto.data_nascita.strftime('%d/%m/%Y')
                                    illa =  str.upper(soggetto.cognome) +''' '''+ str.upper(soggetto.nome) + ''' (c.f. '''+ str.upper(soggetto.codice_fiscale)+ ''')'''
                                    # titolo = ''' proprietaria '''
                            if int(sesso_cf)<=40:
                                    nascita =' nato a ' + soggetto.comune_nascita.title() + ' il ' + "%s" % soggetto.data_nascita.strftime('%d/%m/%Y')
                                    illa = str.upper(soggetto.cognome) + ''' ''' + str.upper(soggetto.nome) + ''' (c.f. '''+ str.upper(soggetto.codice_fiscale)+ ''')'''
                                    # titolo = ''' proprietario '''
                        
                        
                        
                                
                        else :
                            print('c.f.---- stokazzengers')
                            pass

                        p7.add_run(''' ''' + str(illa) + ''', ''' + str(nascita))
                        if tot > 0:
                            p7.add_run(', ')
                    p7.add_run( ''' dei diritti pari a ''')
                    p7.add_run(str(round(conv.millesimi,3))).bold=True
                    p7.add_run(''' millesimi di piena proprietà dell\'area rappresentata al N.C.T.R., ''')
                    p7.add_run(lista_terreni).bold=True
                    p7.add_run( ''' approvando altresì l\'eliminazione dei vincoli di prezzo massimo di vendita e di canone massimo di locazione afferenti l\'alloggio;''')
                    # p7.add_run(''' come meglio descritto in premessa e nello schema di contratto allegato quale parte integrante;''')
                
                
                
                # PUNTO 2
                
            
            p8 = document.add_paragraph()
            p8.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p8.add_run('''2) Di dare atto  che quanto stabilito al punto 1) costituisce parziale modifica della Convenzione stipulata tra\
 il Comune di Carrara e ''')
            p8.add_run(str.upper(coop.cognome)).bold=True
            p8.add_run(''' a rogito ''' + str(conv.notaio) + ''' del ''' + "%s" % conv.data_atto.strftime('%d/%m/%Y') +''' ''' +  str(conv.atto)+''';''')
            
            # PUNTO 3

            p9 = document.add_paragraph()
            p9.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p9.add_run('''3) Di accertare l\'introito di ''')
            p9.add_run('''€ ''').bold=True
            p9.add_run().bold=True

           
                        
            if tot_dovuto :
                p9.add_run(' € ' + str(tot_dovuto)).bold=True
                numero_lettere = (num2words(tot_dovuto , lang='it'))
                lung = len(str(tot_dovuto))-2
                numero_decimali = str(tot_dovuto)[lung:]
                p9.add_run(' (diconsi euro ' + numero_lettere +'/' )
                p9.add_run(numero_decimali + ' )')

            p9.add_run(''', come indicato in premessa, quale corrispettivo per la trasformazione del diritto di superficie \
in proprietà e l'eliminazione dei vincoli convenzionali al capitolo ''')
            p9.add_run('''40400.02.0300''').bold=True
            p9.add_run(''' denominato ''')
            p9.add_run('''proventi per cessione di aree da diritto di superficie''').bold=True
            p9.add_run(''' del PEG 2024, dando atto che lo stesso è esigibile nel medesimo esercizio;''')


            p10 = document.add_paragraph()
            p10.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p10.add_run('''4) Di significare che, nel caso di controversia giudiziale, la materia \
oggetto del presente provvedimento rientra nella giurisdizione del TAR e che inoltre è esperibile il \
ricorso amministrativo per via straordinaria al Capo dello Stato, in entrambi i casi, nei termini ed \
alle condizioni previste dal D.Lgs. 104/2010 e dal D.P.R. 1199/1971. ''')


            # p06=document.add_paragraph()
            # p06.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            # # p06.paragraph_format.first_line_indent  = Inches(0.5)
            # p06.paragraph_format.space_after = Pt(2)
            # p06.paragraph_format.space_before = Pt(2)
            
            # p06.add_run('''Distinti saluti      ''')


            p07 = document.add_paragraph()
            p07.alignment = WD_ALIGN_PARAGRAPH.LEFT
            # p06.paragraph_format.first_line_indent  = Inches(0.5)
            p07.paragraph_format.space_after = Pt(2)
            p07.paragraph_format.space_before = Pt(2)

            p07.add_run('''Carrara, data della sottoscrizione digitale''')

            p07 = document.add_paragraph()
            p07.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            # p07.paragraph_format.first_line_indent  = Inches(0.5)
            p07.paragraph_format.space_after = Pt(2)
            p07.paragraph_format.space_before = Pt(2)
            
            p07.add_run('''Il Dirigente
Ing Luca Amadei''')

            p08 = document.add_paragraph()
            p08.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p08.paragraph_format.space_before = Pt(10)
            p08.add_run('Documento firmato digitalmente ai sensi e per gli effetti di cui agli artt.21, 23, 23bis e 23ter del D.LGS. 82 del 7 marzo 2005 e s.m.i. - Codice dell\'Amministrazione Digitale', style='NormalStyle').italic=True


# Prepare document for download        
        # -----------------------------
            f = BytesIO()
            document.save(f)
            length = f.tell()
            f.seek(0)
            response = HttpResponse(
                f.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
            response['Content-Disposition'] = 'attachment; filename=' + docx_title
            response['Content-Length'] = length            
            return response



############################################################
# REPORT: TUTTI I VERSAMENTI EFFETTUATI
############################################################

@login_required
def versamenti_report(request):
    """
    Genera un report di TUTTI i versamenti effettuati:

    - AccettaImporto con rateo=False (versamento unico / non rateizzato)
    - Scadenze con pagata=True (versamenti rateizzati / installment)

    Per ciascuno riporta: protocollo, data, primo richiedente, importo, IUV.
    """
    import datetime as _dt

    results = []
    _soggetto_cache = {}

    def _get_primo_richiedente(pratica):
        if pratica is None:
            return ''
        pid = pratica.id
        if pid in _soggetto_cache:
            return _soggetto_cache[pid]
        try:
            anaprat = Anaprat.objects.filter(pratica=pratica)\
                .select_related('soggetto', 'tipo')\
                .order_by('tipo__id')\
                .first()
            if anaprat and anaprat.soggetto:
                val = f"{anaprat.soggetto.cognome} {anaprat.soggetto.nome}"
            else:
                val = ''
        except Exception:
            val = ''
        _soggetto_cache[pid] = val
        return val

    # 1. Versamenti non rateizzati (AccettaImporto con rateo=False)
    accettazioni = AccettaImporto.objects.filter(
        rateo=False,
    ).select_related(
        'convenzione',
        'convenzione__pratica',
    ).order_by('-data_accettazione')

    for a in accettazioni:
        pratica = getattr(a.convenzione, 'pratica', None)
        prot_gen = a.prot_gen or (pratica.prot_gen if pratica else '')
        results.append({
            'prot_gen': prot_gen,
            'data_pagamento': a.data_accettazione,
            'primo_richiedente': _get_primo_richiedente(pratica),
            'importo_pagamento': a.importo,
            'iuv': a.iuv or '',
            'pratica_id': pratica.id if pratica else None,
            'tipo_versamento': 'Unico',
        })

    # 2. Versamenti rateizzati (Scadenze con pagata=True)
    scadenze = Scadenze.objects.filter(
        pagata=True,
        importo_pagamento__isnull=False,
    ).select_related(
        'convenzione',
        'convenzione__pratica',
    ).order_by('-data_pagamento')

    for s in scadenze:
        pratica = getattr(s.convenzione, 'pratica', None)
        prot_gen = pratica.prot_gen if pratica else ''
        results.append({
            'prot_gen': prot_gen,
            'data_pagamento': s.data_pagamento,
            'primo_richiedente': _get_primo_richiedente(pratica),
            'importo_pagamento': s.importo_pagamento,
            'iuv': s.iuv or '',
            'pratica_id': pratica.id if pratica else None,
            'tipo_versamento': 'Rata',
        })

    # Unisce entrambi i gruppi, ordinati per data più recente
    results.sort(
        key=lambda r: (r['data_pagamento'] or _dt.date.min),
        reverse=True,
    )

    totale_versato = sum(
        (r['importo_pagamento'] or 0) for r in results
    )

    context = {
        'versamenti': results,
        'totale_versato': totale_versato,
        'totale_versamenti': len(results),
    }
    return render(request, 'coop/versamenti_report.html', context)
