# from django.db.models import Q
from django.shortcuts import (get_object_or_404,
                              render,
                              HttpResponseRedirect,
                              redirect)
from django.db.models import Q, Count
# import simplejson
from django.http import HttpResponse, Http404
from operator import itemgetter
import datetime
from django.contrib.auth.decorators import login_required
from accounts.permissions import editor_required
from django.contrib import messages
from .forms import *
from .models import *
from protocollo.models import *
from protocollo.views import block_readonly_write, can_edit
from protocollo.utils import log_action
from num2words import num2words








@login_required
# @user_passes_test(is_editor_or_admin, login_url='home:index')
@editor_required(allow_viewers=True)


# @user_passes_test(lambda u: u.groups.filter(name='editor_settore_6').count() == 1, login_url='home')
#   aggiunge una IDONEITA legata alla pratica 

def IstruttoriaAddView(request, pk):
    print('777ggd555dr')
    is_editor = can_edit(request.user)
    
    pratica = get_object_or_404(Pratica, id=pk)
    print('jhjhADSGKADKAJKGHDKAHDKAA', pk)
    tipo=pratica.tipo_pratica_id

    anaprat = Anaprat.objects.filter(pratica_id=pk)
    richiedente = []
    for s in anaprat:
        soggetti={}
        sogg = Soggetto.objects.get(id=s.soggetto_id)
        soggetti['id_anaprat']=s.id
        soggetti['cognome']=sogg.cognome
        soggetti['nome']=sogg.nome

        richiedente.append(soggetti)
        print (richiedente)
    print (tipo,'tipo_pratica',pratica.tipo_pratica)
    if tipo == 26: # esegue se la pratica è id=26 name = idonall    
        if request.method == "POST":
            form = IstruttoriaForm(request.POST)
            if form.is_valid():
                obj = form.save(commit=False)
                if obj.ante1975 == True:
                    obj.mq = 0
                else:
                    obj.vani = 0
                obj.pratica_id = pk
                obj.user = request.user
                try:
                    obj.save()
                    log_action(request, 'CREATO', f'Istruttoria {obj.id}', {'pratica': pk})
                    print('Dati salvati correttamente')
                    return redirect('protocollo:pratica_detail_url', pk)
                except Exception as e:
                    print('Errore nel salvataggio:', e)
            else:
                print('Il form non è valido:', form.errors)
        else:
            form = IstruttoriaForm()
            context = {
                 'is_editor':is_editor,
                 'form':form,
                 'pratica':pratica,
                 'pk':pk, 
                 'richiedente':richiedente}
            return render(request,'idonall/add.html',context)
    else :
        print('non arriva nessun dato')
        pass






@login_required
@editor_required(allow_viewers=True)


def IstruttoriaEditView(request, id):
    is_editor = can_edit(request.user)
    today = datetime.date.today()
    # year = today.year
    print('gruppo',is_editor)
    richiedente=[]

    
    istruttoria = Istruttoria.objects.get(id=id)
    pratica = Pratica.objects.get(id=istruttoria.pratica_id)

    anaprat = Anaprat.objects.filter(pratica_id=istruttoria.pratica_id)
    for s in anaprat:
        soggetti={}
        sogg = Soggetto.objects.get(id=s.soggetto_id)
        soggetti['id_anaprat']=s.id
        soggetti['cognome']=sogg.cognome
        soggetti['nome']=sogg.nome

        richiedente.append(soggetti)
    print (richiedente)

    print('istruttoria',istruttoria)
    pk= istruttoria.id
    print('pk',pk)
    if request.method == 'POST':
        form = IstruttoriaForm(request.POST, instance=istruttoria)
        if form.is_valid():
                    obj=form.save(commit=False)
                    if (obj.ante1975 == True):
                        obj.mq = 0
                        obj.vani = obj.vani
                    else:
                        obj.vani = 0
                        obj.mq = obj.mq
                    obj.save()
                    log_action(request, 'MODIFICATO', f'Istruttoria {istruttoria.id}')
                    
                    # print(obj.ante1975,'hhhsyyst6sttt')
                    # obj.pratica_id = pk
                    # obj.user = request.user
                    # try:
                    #     obj.save()
                    #     print('Dati salvati correttamente')
                    #     return redirect('protocollo:pratica_detail_url', pk)
                    # except Exception as e:
                    #     print('Errore nel salvataggio:', e)
                    return redirect('protocollo:pratica_detail_url', pratica.id )
    else:
        form = IstruttoriaForm( instance=istruttoria)
        context = {
            'form': form, 
            'pk':pk,
            'istruttoria':istruttoria,
            'is_editor':is_editor, 
            'pratica':pratica,
            'richiedente':richiedente,
            'today':today,
        }

        return render(request,'idonall/edit.html',context)



@login_required
@editor_required(allow_viewers=True)



def IdonallAdd(request, pk):
    is_editor = can_edit(request.user)

    print('gruppo',is_editor)
    pratica = get_object_or_404(Pratica, id=pk)
    print('gruppo',is_editor)
    submitted = False
    istruttoria = Istruttoria.objects.get(pratica_id=pratica.id)

    today = datetime.date.today()
    year = today.year
    # Verifica se il campo pratica.data_prot_gen contiene una data
    if pratica.data_prot_gen is not None:
        # Ottieni l'anno dalla data
        data_prot_gen_year = pratica.data_prot_gen.year
    
        # Confronta l'anno corrente con l'anno della data
        if year == data_prot_gen_year:
            print('Gli anni coincidono:', data_prot_gen_year)
            # Inserisci qui le azioni da compiere

            #   verifica se l'anno corrente corrisponde all'anno del protocollo
            print('oggi',today)
            numero = Idonall.objects.filter(idonall_date__year=year).count()
            if numero>0:
                nuovo_idonall = numero+1
            else:
                nuovo_idonall = 1
        else:
            nuovo_idonall = 0
            today = data_prot_gen_year
    
    
    richiedente=[]
   
    
    
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
    if tipo == 26: # esegue se la pratica è id=26 name = idonall    
        if request.method == "POST":

            

            form = IdonallForm(request.POST)
            if form.is_valid():
                obj=form.save(commit=False)
            
            obj.istruttoria_id = istruttoria.id
            # aggiungo user
            obj.user = request.user
            obj.save()
            log_action(request, 'CREATO', f'Idonall {obj.id}', {'pratica': pk})
                    
            return redirect('protocollo:pratica_detail_url' ,pk)
        # else:
        #          print('6666dsgsdgksld8sd7')
                    
        else:
            form = IdonallForm()
            submitted = True
            print('77tdg55eddaa4dll')
            context = {
                'is_editor':is_editor,
                'form':form,
                'pratica':pratica,
                'pk':pk,
                'richiedente':richiedente,
                'istruttoria':istruttoria,
                'idonall_proposto':nuovo_idonall,
                'today':today,
                }

            return render(request,'idonall/add_idonall.html', context )
    else :
        print('non arriva nessun dato')
        pass


@login_required
@editor_required(allow_viewers=True)


def IdonEditView(request, id):
    is_editor = can_edit(request.user)

    print('gruppo',is_editor)
    idon_edit=[]
    idon = Idonall.objects.get(id=id)
    istruttoria = Istruttoria.objects.get(id=idon.istruttoria_id)
    pratica = Pratica.objects.get(id=istruttoria.pratica_id)
    print('idon',idon)
    pk= idon.id
    print('pk',pk)
    if request.method == 'POST':
       form = IdonallForm(request.POST, instance=idon)
       if form.is_valid():
           # update the existing `Pratica` in the database
           form.save()
           log_action(request, 'MODIFICATO', f'Idonall {idon.id}')
           # redirect to the detail page of the `Pratica` we just updated
           return redirect('protocollo:pratica_detail_url', pratica.id )
    else:
        form = IdonallForm(instance=idon)
        context = {
            'form': form, 
            'idon':idon, 
            'pratica':pratica,
            'is_editor':is_editor,
            'pk':pk,
            }
        return render(request,'idonall/edit_idonall.html', context)



###################################################################################

#                                   STAMPA CERTIFICATO DI IDONEITA'

###################################################################################


from django.http import HttpResponse, HttpResponseForbidden
from docx import Document
from docx import *
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_UNDERLINE
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.section import WD_ORIENT
from docx.shared import Pt, Inches, Mm
import os
from datetime import date
from collections import OrderedDict
import numpy as np

# import pandas as pd
from itertools import groupby
from io import BytesIO

def CreateIdonallView(request,id):
    idonall = Idonall.objects.get(id=id) # idon da produrre
    istruttoria = idonall.istruttoria
    pratica = istruttoria.pratica
    log_action(request, 'GENERATO DOCUMENTO', f'Idonall {idonall.id}', {'pratica_id': pratica.id, 'idonall_number': idonall.idonall_number})
    print(idonall)
    
    atto = str(pratica.tipo_pratica)+'_attestazione_'+str(idonall.idonall_number) +'_'+str(idonall.idonall_date)+'.docx'
    
    document = Document()
    # imposta A4 verticale e margini
    section = document.sections[0]
    section.page_height = Mm(297)
    section.page_width = Mm(210)
    section.left_margin = Mm(20)
    section.right_margin = Mm(20)
    section.top_margin = Mm(20)
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
    f1.add_run("Servizio 6.1  - U.O. 6.1.2  SUEP & Vigilanza abusivismo - P.za due giugno,1 54033 - Carrara (MS)", style = 'FooterStyle')

    f2=footer.add_paragraph()
    f2.paragraph_format.space_after = Pt(0)
    f2.paragraph_format.space_before = Pt(0)
    f2.add_run("geom. Maurizio Menconi - 0585 641282 - maurizio.menconi@comune.carrara.ms.it", style = 'FooterStyle')
#   IMPOSTA GLI STILI DEI SINGOLI PARAGRAFI
    # document.add_paragraph()
    font = document.styles['Normal'].font
    font.size=Pt(10)
    font.name='Times New Roman'

    obj_styles = document.styles
    obj_charstyle = obj_styles.add_style('NormalStyle', WD_STYLE_TYPE.CHARACTER)
    obj_font = obj_charstyle.font
    obj_font.size = Pt(10)
    obj_font.name = 'Times New Roman'
    
    obj_styles = document.styles
    obj_charstyle = obj_styles.add_style('SottoHeaderStyle', WD_STYLE_TYPE.CHARACTER)
    obj_font = obj_charstyle.font
    obj_font.size = Pt(8)
    obj_font.name = 'Times New Roman'

    obj_styles = document.styles
    obj_charstyle = obj_styles.add_style('HeaderStyle', WD_STYLE_TYPE.CHARACTER)
    obj_font = obj_charstyle.font
    obj_font.size = Pt(12)
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

    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    docx_title=atto
    # heading = document.add_paragraph()
   
   
    # p = document.add_paragraph()
    # r = p.add_run()
    # r.add_text('Good Morning every body,This is my ')
    
#   Definisci il percorso dell'immagine
    # image_name = 'logo_carrara.png'
    # image_path = os.path.join('image/', image_name)

    # Inserisci l'immagine nel documento
    # https://www.shibutan-bloomers.com/python_library_python-docx-2_en/7091/
#   CON ChatGpt

    # Definisci il percorso dell'immagine
    image_name = 'logo_decorato.png'
    image_path = os.path.join('static/img/', image_name)
    
    # Inserisci l'immagine nel documento
        
    run = paragraph.add_run()
    run.add_picture(image_path, width=Inches(1.6))
    # Posiziona centralmente l'immagine
    paragraph_format = paragraph.paragraph_format
    paragraph_format.alignment = 1 # 1 - allineato centrato 0 - allineato a sx
    p0_1 = document.add_paragraph()
    p0_1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p0_1.bold=True
    p0_1.add_run('Settore 6 - Governo del territorio', style = 'PianoStyle').bold = True
    # p0_1.add_run(str(idon.idonall_number)+ ' del ' +"%s" % idon.idon_date.strftime('%Y'), style='CduStyle').bold=True
         
    paragraph_format = paragraph.paragraph_format
    paragraph_format.alignment = 1 # 1 - allineato centrato 0 - allineato a sx
    p0_2 = document.add_paragraph()
    p0_2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p0_2.bold=True
    p0_2.add_run('', style = 'NormalStyle').bold = True
    
 # # recupera TUTTI i richiedenti
    
    try:
        proprietario = Anaprat.objects.get(Q(pratica_id__exact = pratica.id) & Q(tipo_id__exact = 22))
        if proprietario :
            print(proprietario,'7dt4444d5')  
    except:
        print('7asggstsyy')
        pass
    all_rich = Anaprat.objects.filter(Q(pratica_id__exact=pratica.id ) & Q(tipo_id__in=TipoSoggetto.objects.filter(name__iexact='richiedente').values_list('id', flat=True)))
    print('richiedenti', all_rich)
    for a in all_rich:
                soggetto=Soggetto.objects.get(id=a.soggetto_id)
               
                    
                '''    
                #inserisce il nominativo
                p2 = document.add_paragraph()
                p2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                p2.paragraph_format.space_after = Pt(3)
                p2.add_run('Spett.Le ' + str.upper(soggetto.cognome) + '  ' , style='NumCduStyle').bold=True  
                p2.add_run(str.title(soggetto.nome), style='NumCduStyle')

                p2_1 = document.add_paragraph()
                p2_1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                p2_1.paragraph_format.space_after = Pt(1)
                if soggetto.addr:
                    p2_1.add_run(str.title(soggetto.addr) , style='NumCduStyle')

                p2_2 = document.add_paragraph()
                p2_2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                p2_2.paragraph_format.space_after = Pt(4)
                if soggetto.comune_residenza:
                    p2_2.add_run(str.title(soggetto.comune_residenza) , style='NumCduStyle')

               
                        
                if soggetto.email:
                            p2_3 = document.add_paragraph()
                            p2_3.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                            p2_3.paragraph_format.space_after = Pt(6    )
                            p2_3.add_run('e-mail' , style='NumCduStyle').bold=True
                            p2_3.add_run(' : ' + str.lower(soggetto.email) , style='NumCduStyle')

                if soggetto.pec:
                            p2_3 = document.add_paragraph()
                            p2_3.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                            p2_3.paragraph_format.space_after = Pt(12)
                            p2_3.add_run('Pec' , style='NumCduStyle').bold=True
                            p2_3.add_run(' : ' + str.lower(soggetto.pec) , style='NumCduStyle')
                '''
# #    stampo i dati del idon

    p1 = document.add_paragraph()
    p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p1.bold=True
    p1.add_run('Attestazione di Idoneità Alloggiativa n° ', style = 'NumCduStyle').bold = True
    p1.add_run(str(idonall.idonall_number)+ ' del ' +"%s" % idonall.idonall_date.strftime('%d/%m/%Y'), style='NumCduStyle').bold=True
    
    p1_1 = document.add_paragraph()
    p1_1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if istruttoria.tipo_richiesta == 'Duplicato':
        p1_1.add_run(  pratica.oggetto )




    
    # ESTRAE le particelle interessate e le elenca
    try:
        particelle = Cataprat.objects.filter(pratica_id=istruttoria.pratica_id) 
        tot_particelle = particelle.count()
        print('to',tot_particelle)
    except:
        particelle = None
        pass

    pratica = Pratica.objects.get(id=istruttoria.pratica_id) # recupera i dati della pratica

    # recupera il primo richiedente
    rich = Anaprat.objects.filter(pratica_id=istruttoria.pratica_id, tipo_id__in=TipoSoggetto.objects.filter(name__iexact='richiedente').values_list('id', flat=True)).first()
    if not rich:
        rich = Anaprat.objects.filter(pratica_id=istruttoria.pratica_id).first()
    if not rich:
        raise Http404("No richiedente found for this certificate.")
    print('richiedenti', rich)
    soggetto = Soggetto.objects.get(id=rich.soggetto_id)


    if soggetto.comune_nascita:
        # verifico se maschio o femmina 
        
        if soggetto.codice_fiscale !=None:
            sesso_cf = soggetto.codice_fiscale[9:11]
       
            if int(sesso_cf)>=40:
                nascita =' nata a ' + soggetto.comune_nascita.title() + ' il ' + "%s" % soggetto.data_nascita.strftime('%d/%m/%Y')
            else:
                nascita =' nato a ' + soggetto.comune_nascita.title() + ' il ' + "%s" % soggetto.data_nascita.strftime('%d/%m/%Y')
            print('sesso_cf', sesso_cf)
        else:
            print('manca il codice fiscale')
    else:
        nascita = ''

    

    



    prot = pratica.prot_gen
    data = pratica.data_prot_gen
    # print(particelle)
    foglio_pre="" # imposta a blank il foglio precedente
    lista =[] # lista le particelle nella pratica
    if tot_particelle:
                    # paragraph = document.add_paragraph()
                    for p in particelle:
                            # mappali ={}
                            part = Particella.objects.get(id=p.particella_id)
                            print(part)
                            if foglio_pre==part.foglio:
                                mappali = ', ' + part.mappale 
                                if p.subalterno !='-':
                                      mappali = mappali + ' sub. '+str(p.subalterno)+', '
                            else:
                                mappali = 'Foglio ' + part.foglio + ' map ' + part.mappale
                                if p.subalterno !='-':
                                      mappali = mappali + ' sub '+str(p.subalterno)+', '
                            foglio_pre= part.foglio
                            lista.append(mappali)
                    print(lista, foglio_pre, part.foglio)
                    #document.add_paragraph(lista)
    print(lista, foglio_pre, part.foglio)
    #document.add_paragraph(lista)

    # Ricavo ISTRUTTORIA
    istruttoria = Istruttoria.objects.get(pratica_id = pratica)
    print(istruttoria.id, '6asrrsf4')
    par_0 = document.add_paragraph()
    par_0.alignment = WD_ALIGN_PARAGRAPH.CENTER
    par_0.bold=True
    par_0.add_run('IL DIRIGENTE', style = 'CduStyle').bold = True
    
    par_1 = document.add_paragraph('             Vista l\'istanza pervenuta in data ' +"%s" % data.strftime('%d/%m/%Y') +  ' prot. n. ')
    par_1.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    # par_1.add_run()
    par_1.add_run(prot).bold=True
    # par_1.add_run(' del ' )
    # par_1.add_run("%s" % data.strftime('%d/%m/%Y') +') ').bold=True
    par_1.add_run(' inoltrata da ')
    par_1.add_run(soggetto.cognome.upper() + ' ' + soggetto.nome.title()).bold=True
    if soggetto.codice_fiscale:
        par_1.add_run(nascita+', ' + '(c.f. ' + soggetto.codice_fiscale.upper() + '), residente in ' + soggetto.addr.title() + ', ' + soggetto.comune_residenza.title() )
    
    # verifica anche eventuali cointestati
    try:
        cointestati = Anaprat.objects.filter(pratica_id=istruttoria.pratica_id, tipo_id = 25)
        insieme = ' unitamente a '
        for c in cointestati:
            soggetto_C = Soggetto.objects.get(id=c.soggetto_id)

            if soggetto_C.comune_nascita:
                # verifico se maschio o femmina 
                
                if soggetto_C.codice_fiscale !=None:
                    sesso_cf_c = soggetto_C.codice_fiscale[9:11]
            
                    if int(sesso_cf_c)>=40:
                        nascita_c =' nata a ' + soggetto_C.comune_nascita.title() + ' il ' + "%s" % soggetto_C.data_nascita.strftime('%d/%m/%Y')
                    else:
                        nascita_c =' nato a ' + soggetto_C.comune_nascita.title() + ' il ' + "%s" % soggetto_C.data_nascita.strftime('%d/%m/%Y')
                    print('sesso_cf_c', sesso_cf_c)
                else:
                    print('manca il codice fiscale')
            else:
                nascita_c = ''

            par_1.add_run(insieme)
            par_1.add_run('\n' + soggetto_C.cognome.upper() + ' ' + soggetto_C.nome.title()).bold=True
            if soggetto.codice_fiscale:
                par_1.add_run(nascita_c+', ' + '(c.f. ' + soggetto_C.codice_fiscale.upper() + ') cointestatario,')
    except:
        pass
    
    # par_1.add_run(CIARI Geom. Riccardo nato a Carrara (54033) - Ms il 01/07/1966 (c.f. CRIRCR66L01B832D) residente in Carrara, Via Venezia n. 2,)
    par_1.add_run(' con la quale si richiede ')
    if pratica.sub_code is None and pratica.tipo_pratica_id == 26:
        par_1.add_run('l\' '+ pratica.oggetto.strip() + ' per l\'unità immobiliare posta in ')
    else:
        par_1.add_run('il '  + pratica.oggetto.strip() + ' per l\'unità immobiliare posta in ')
    
    if str(pratica.street) != '':
                      par_1.add_run(str(pratica.street))
    if str(pratica.housenumber) != '':
                      par_1.add_run(', ' + str(pratica.housenumber))
                  
    if tot_particelle != 0:
        par_1.add_run(', distinta catastalmente al ')

    par_1.add_run(lista)
            
    if istruttoria.catasto == True:     
        par_2 = document.add_paragraph('VISTA la documentazione allegata all\'istanza depositata e la dichiarazione di conformità dello stato attuale alla planimetria stessa, a firma del proprietario dell\'unità immobiliare;')
        par_2.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    par_2_1 = document.add_paragraph('VISTA  la Legge n. 40 del 6 marzo 1998, art. 27 c.3 lett.a);')
    par_2_1.alignement = WD_ALIGN_PARAGRAPH.DISTRIBUTE
    
    par_2_2 = document.add_paragraph('VISTA  la L.R. n. 2 del 02/01/2019 Allegato \'C\';')
    par_2_2.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    par_2_3 = document.add_paragraph('VISTA  la deliberazione di Giunta Toscana n. 700/2005;')
    par_2_3.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    par_2_4 = document.add_paragraph('VISTA  la deliberazione di Giunta Comunale n. 571 del 07/10/2010 - Accertamento dell\'idoneità abitativa per ricongiungimento familiare da parte di stranieri;')
    par_2_4.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    # verifica se rel_tecnica è riempito
    if istruttoria.nota_relazione and len(istruttoria.nota_relazione)>3:
        par_2_5 = document.add_paragraph('VISTA la dichiarazione depositata da ')
        par_2_5.add_run(str( istruttoria.nota_relazione ) + ', con la quale si certifica l\'idoneita\' igienico-sanitaria per l\'unita\' \
immobiliare e che, ad oggi, non risultano provvedimenti di inefficacia dell\'abitabilita\' dell\'immobile di cui si tratta;' )
        par_2_5.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY
    elif istruttoria.nota_abitabilita:
        par_2_5 = document.add_paragraph('VISTA la certificazione di abitabilita\'/agibilita\' ')
        par_2_5.add_run(str( istruttoria.nota_abitabilita ) + ', con la quale si certifica l\'idoneita\' igienico-sanitaria per l\'unita\' \
immobiliare e che, ad oggi, non risultano provvedimenti di inefficacia dell\'abitabilita\' dell\'immobile di cui si tratta;' )
        par_2_5.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY

    if istruttoria.ante1975 == True:
        numero_lettere = (num2words(istruttoria.num_adulti , lang='it'))
        lung = len(str(istruttoria.num_adulti))-2
        
        numero_decimali = str(istruttoria.num_adulti)[lung:]
        print(numero_lettere , lung)

        par_2_6 = document.add_paragraph()
        par_2_6.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        par_2_6.add_run('Dato atto che l\'ufficio ha constatato, dalla documentazione allegata all\'istanza, che l\'alloggio risulta edificato anteriormente alla \
data di entrata in vigore del D.M. della Sanità 5 luglio 1975, pubblicato sulla G.U. n. 190 del 18/07/1975 e risulta composto da n. ')
        par_2_6.add_run(str(istruttoria.vani) +' vani utili ')
        par_2_6.add_run(' come da tabella di cui all\'  Allegato \"C\" della L.R. n. 2/2019;' )

    else:
        
        numero_lettere = (num2words(istruttoria.num_adulti , lang='it'))
        lung = len(str(istruttoria.num_adulti))-2
        
        numero_decimali = str(istruttoria.num_adulti)[lung:]
        print(numero_lettere , lung)

        par_2_6 = document.add_paragraph()
        par_2_6.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        par_2_6.add_run('Dato atto che l\'ufficio ha constatato, dalla documentazione allegata all\'istanza, che l\'alloggio risulta edificato successivamente alla \
data di entrata in vigore del D.M. della Sanità 5 luglio 1975, pubblicato sulla G.U. n. 190 del 18/07/1975 e che l\'unita\' immobiliare oggetto della richiesta misura ')
        par_2_6.add_run(str(istruttoria.mq) +' mq; ')
         
    
    par_3 = document.add_paragraph()
    par_3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    runner = par_3.add_run('CERTIFICA', style ='CduStyle').bold=True  

    par_3_1 = document.add_paragraph()
    par_3_1.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY
    par_3_1.add_run('Che l\'unità immobiliare con destinazione d\'uso residenziale, sita in Carrara ' + str(pratica.street) +', '+str(pratica.housenumber)+'\
 risulta essere adeguata per n. ' + str(istruttoria.num_adulti) )
    par_3_1.add_run(' ( diconsi ' + numero_lettere +' )' )
    # par_3_1.add_run(numero_decimali + ' )')
    par_3_1.add_run(' persone adulte')

    if istruttoria.num_minori is not None:
        par_3_1.add_run(' e numero ' + str(istruttoria.num_minori) )
        if istruttoria.num_minori == 1:
             par_3_1.add_run(' minore')
        if istruttoria.num_minori > 1:
             par_3_1.add_run(' minori')
    par_3_1.add_run(', ed allo stato attuale risulta igienicamente abitabile.-')
    today = datetime.date.today()
    
    

    par_8_3 = document.add_paragraph()
    # par_8_3.paragraph_format.first_line_indent = Inches(0.3)
    par_8_3.paragraph_format.space_before = Pt(1)
    par_8_3.paragraph_format.space_after = Pt(1)
    par_8_3.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
    par_8_3.add_run('Carrara, '+ "%s" % today.strftime('%d/%m/%Y'))

    par_8_4 = document.add_paragraph()
    par_8_4.paragraph_format.space_before = Pt(1)
    par_8_4.paragraph_format.space_after = Pt(1)
    par_8_4.alignement = WD_ALIGN_PARAGRAPH.CENTER
    par_8_4.paragraph_format.first_line_indent = Inches(4.2)
    par_8_4.add_run('Il Dirigente', style='NormalStyle' )

    par_8_5 = document.add_paragraph()
    par_8_5.paragraph_format.space_before = Pt(1)
    par_8_5.paragraph_format.space_after = Pt(1)
    par_8_5.alignement = WD_ALIGN_PARAGRAPH.CENTER
    par_8_5.paragraph_format.first_line_indent = Inches(4.2)
    par_8_5.add_run('Ing. Luca Amadei', style='NormalStyle' )

    

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
