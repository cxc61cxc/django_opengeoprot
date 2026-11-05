# from django.db.models import Q
from django.shortcuts import (get_object_or_404,
                              render,
                              HttpResponseRedirect,
                              redirect)
from django.db.models import Q, Count
# import simplejson
from django.http import HttpResponse
from operator import itemgetter
import datetime
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import *
from .models import Pau
from protocollo.models import *
from protocollo.utils import log_action



######################################################################
#   PAU
######################################################################


#   elenca i Provvedimenti Autorizzativi Unici

def PauListView(request):
    pk = request.session.get('pk')
    pau = Pau.objects.all().order_by('pau_date','pau_number')
    print('pau',pau)
    numero = pau.count()
    print('numero',numero)
    context = {
        'vedi':"vedi",
        'pau': pau,
        'numero':numero,
    }
    return render(request,'suap/pau_list_view.html', context)

@login_required
# @user_passes_test(lambda u: u.groups.filter(name='editor_settore_6').count() == 1, login_url='home')
#   aggiunge un PAU legato alla pratica 

def PauAddView(request):
    submitted = False
    pk = request.session.get('pk')

    # provo a impostare il numero di PAU
    # cerco i pau per l'anno in corso
    today = datetime.date.today()
    year = today.year

#   propone il
    print('anno',year)
    numero = Pau.objects.filter(pau_date__icontains=year).count()
    if numero>0:
        nuovo_pau = numero+1
    else:
        nuovo_pau = 1
    print ('pau',nuovo_pau) # stampa il numeroo dei pau nell'anno

    # ora il numero di pau proposto dovrebbe risultare 1 per il primo pau dell'anno e proporre il nuovo numero se già presenti altri (nuovo_pau)

    print('aggiunge pau a pratica id',pk)
    # pratica = Pau.objects.filter(pratica = pk)
    pratica= Pratica.objects.get(id=pk)
    tipo=pratica.tipo_pratica_id
    num_pau=nuovo_pau
    print (tipo,'tipo_pratica',pratica.tipo_pratica)
    if tipo == 11 or tipo==12 or tipo==19: # esegue se la pratica è id=3 name = pau    
        if request.method == "POST":

            print(num_pau,'zero pau',tipo)

            form = PauForm(request.POST)
            if form.is_valid():
                    obj=form.save(commit=False)
                    obj.pratica_id = pk
                    obj.save()
                    log_action(request, 'CREATO', f'Pau {obj.id}', {'pratica': pk})
                    id = Pau.objects.latest('id').id # ricava l'ID dell'ultimo soggetto
                    print('id',id)
                    return redirect('suap:pau_detail_url' ,id)
        else:
            form = PauForm()
            if 'submitted' in request.GET:
                submitted = True
                print('id_add',id)

            return render(request,'suap/pau_add_view.html',{'form':form,'pratica':pratica,'pk':pk, 'pau_proposto':nuovo_pau})
    else :
        print('non arriva nessun dato')
        pass

    # return redirect('protocollo:pratica_detail_url' ,pk)

@login_required
def PauEditView(request, id):
    pau_edit=[]
    pau = Pau.objects.get(id=id)
    pratica = Pratica.objects.get(id=pau.pratica_id)
    print('pau',pau)
    pk= pau.id
    print('pk',pk)
    if request.method == 'POST':
       form = PauForm(request.POST, instance=pau)
       if form.is_valid():
           # update the existing `Pratica` in the database
           form.save()
           log_action(request, 'MODIFICATO', f'Pau {pau.id}')
           # redirect to the detail page of the `Pratica` we just updated
           return redirect('suap:pau_detail_url', pk )
    else:
        form = PauForm(instance=pau)

    return render(request,
                'suap/pau_edit_view.html',
                {'form': form, 'pau':pau, 'pratica':pratica})

# dettaglio PAU e particelle

def PauDetailView(request, id):

    pk = request.session.get('pk')
    pratica=Pratica.objects.get(id=pk)
    print('pratica',pratica)
#   recupero il pau
    pau = get_object_or_404(Pau, id=id)
    log_action(request, 'VISUALIZZATO', f'Pau {pau.id}')
    print(pau.pratica.id)
    # imposto la lista delle particelle
    particelle=[]
    richiedente=[]

    # lista le particelle del PAU
    cataprat = Cataprat.objects.filter(pratica_id=pk)

    for p in cataprat:
        mappali ={} # imposto il dizionario

        part = Particella.objects.get(id=p.particella_id)

        mappali['id_cataprat']=p.id
        print(p.id)
        mappali['foglio']=part.foglio
        mappali['mappale']=part.mappale
        # dest = Istruttoria.objects.filter(cataprat=p.id)
        # mappali['tot']=dest.count()

        particelle.append(mappali)
        print('part',particelle)

    anaprat = Anaprat.objects.filter(pratica_id=pk)
    for s in anaprat:
        soggetti={}
        sogg = Soggetto.objects.get(id=s.soggetto_id)
        soggetti['id_anaprat']=s.id
        soggetti['cognome']=sogg.cognome
        soggetti['nome']=sogg.nome

        richiedente.append(soggetti)
        print (richiedente)

    context = {'pk':pk,
               'pratica':pratica,
               'pau': pau, 
               'particelle':particelle,
               'richiedente':richiedente}



    return render(request, 'suap/pau_detail_view.html', context)





###################################################################################

#                                   STAMPA PAU

###################################################################################


from django.http import HttpResponse
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

def CreatePauView(request,id):
    pau = Pau.objects.get(id=id) # pau da produrre
    pratica = Pratica.objects.get(id=pau.pratica_id)
    log_action(request, 'GENERATO DOCUMENTO', f'PAU {pau.id}', {'pratica_id': pratica.id, 'pau_number': pau.pau_number})
    print(pau)
    
    atto = str(pratica.tipo_pratica)+'_'+'PAU'+'_'+str(pau.pau_number) +'_'+str(pau.pau_date)+'.docx'
    
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
    obj_font.name = 'Arial'

    #   IMPOSTA IL FOOTER
    '''
        footer=section.footer

        f1=footer.add_paragraph()
        f1.paragraph_format.space_after = Pt(0)
        f1.paragraph_format.space_before = Pt(0)
        f1.add_run("Settore 7 Governo del territorio - U.O. 7.2 Pianificazione urbanistica - P.zza due giugno,1 54033 - Carrara (MS)", style = 'FooterStyle')

        f2=footer.add_paragraph()
        f2.paragraph_format.space_after = Pt(0)
        f2.paragraph_format.space_before = Pt(0)
        f2.add_run("geom. Sergio Torri - 0585 641432 - sergio.torri@comune.carrara.ms.it", style = 'FooterStyle')

        f3=footer.add_paragraph()
        f3.paragraph_format.space_after = Pt(0)
        f3.paragraph_format.space_before = Pt(0)
        f3.add_run("geom. Carlo Alberto Nicolini - 0585 641252 - carloalberto.nicolini@comune.carrara.ms.it", style = 'FooterStyle')
        
        f4=footer.add_paragraph()
        f4.paragraph_format.space_after = Pt(0)
        f4.paragraph_format.space_before = Pt(0)
        f4.add_run(str(request.user.username), style = 'FooterStyle')
        
        
    '''
    
#   IMPOSTA GLI STILI DEI SINGOLI PARAGRAFI
    # document.add_paragraph()
    font = document.styles['Normal'].font
    font.size=Pt(11)
    font.name='Arial'

    obj_styles = document.styles
    obj_charstyle = obj_styles.add_style('NormalStyle', WD_STYLE_TYPE.CHARACTER)
    obj_font = obj_charstyle.font
    obj_font.size = Pt(10)
    obj_font.name = 'Arial'
    
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
    obj_font.name = 'Arial'

    obj_styles = document.styles
    obj_charstyle = obj_styles.add_style('NumCduStyle', WD_STYLE_TYPE.CHARACTER)
    obj_font = obj_charstyle.font
    obj_font.size = Pt(11)
    obj_font.name = 'Arial'

    obj_styles = document.styles
    obj_charstyle = obj_styles.add_style('DprStyle', WD_STYLE_TYPE.CHARACTER)
    obj_font = obj_charstyle.font
    obj_font.italic = True
    obj_font.size = Pt(8)
    obj_font.name = 'Arial'

    obj_styles = document.styles
    obj_charstyle = obj_styles.add_style('ParticellaStyle', WD_STYLE_TYPE.CHARACTER)
    
    obj_font = obj_charstyle.font
    obj_font.italic = False
    obj_font.underline = WD_UNDERLINE.SINGLE
    obj_font.bold=True
    obj_font.size = Pt(11)
    obj_font.name = 'Arial'

    obj_styles = document.styles
    obj_charstyle = obj_styles.add_style('PianoStyle', WD_STYLE_TYPE.CHARACTER)
    obj_font = obj_charstyle.font
    obj_font.italic = True
    obj_font.size = Pt(10)
    obj_font.bold=False
    obj_font.name = 'Arial'

    obj_styles = document.styles
    obj_charstyle = obj_styles.add_style('DestinazioneStyle', WD_STYLE_TYPE.CHARACTER)
    obj_font = obj_charstyle.font
    obj_font.italic = False
    obj_font.size = Pt(9)
    obj_font.name = 'Arial'

    obj_styles = document.styles
    obj_charstyle = obj_styles.add_style('CertificaStyle', WD_STYLE_TYPE.CHARACTER)
    obj_font = obj_charstyle.font
    obj_font.italic = False
    obj_font.bold=True
    obj_font.size = Pt(14)
    obj_font.name = 'Arial'
    

    
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
    p0_1.add_run('Settore 7 - Governo del territorio', style = 'NormalStyle').bold = True
    # p0_1.add_run(str(pau.pau_number)+ ' del ' +"%s" % pau.pau_date.strftime('%Y'), style='CduStyle').bold=True
         
    paragraph_format = paragraph.paragraph_format
    paragraph_format.alignment = 1 # 1 - allineato centrato 0 - allineato a sx
    p0_2 = document.add_paragraph()
    p0_2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p0_2.bold=True
    p0_2.add_run('U.O. 7.4 S.U.A.P.', style = 'NormalStyle').bold = True
    
    
# #    stampo i dati del pau

    p1 = document.add_paragraph()
    p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p1.bold=True
    p1.add_run('PROVVEDIMENTO UNICO AUTORIZZATIVO N° ', style = 'CduStyle').bold = True
    p1.add_run(str(pau.pau_number)+ ' del ' +"%s" % pau.pau_date.strftime('%Y'), style='CduStyle').bold=True
    


    
    # ESTRAE le particelle interessate e le elenca
    particelle = Cataprat.objects.filter(pratica_id=pau.pratica_id) 
    tot_particelle = particelle.count()
    print('to',tot_particelle)
    pratica = Pratica.objects.get(id=pau.pratica_id) # recupera i dati della pratica
    # recupera il primo richiedente
    rich = Anaprat.objects.filter(pratica_id=pau.pratica_id)[0]
    print('richiedenti', rich)
    soggetto = Soggetto.objects.get(id=rich.soggetto_id)

    if soggetto.comune_nascita:
        # verifico se maschio o femmina 
        sesso_cf = soggetto.codice_fiscale[9:11]
        if int(sesso_cf)>=40:
            nascita =' nata a ' + soggetto.comune_nascita.title() + ' il ' + "%s" % soggetto.data_nascita.strftime('%d/%m/%Y')
        else:
            nascita =' nato a ' + soggetto.comune_nascita.title() + ' il ' + "%s" % soggetto.data_nascita.strftime('%d/%m/%Y')
        print('sesso_cf', sesso_cf)
    else:
        nascita = ''

    prot = pratica.prot_gen
    data = pratica.data_prot_gen
    # print(particelle)
    foglio_pre="" # imposta a blank il foglio precedente
    lista =[]
    # paragraph = document.add_paragraph()
    for p in particelle:
            # mappali ={}
            part = Particella.objects.get(id=p.particella_id)
            # print(part)
            if foglio_pre==part.foglio:
                mappali = 'map ' + part.mappale + '; '
            else:
                mappali = 'Foglio ' + part.foglio + ' map ' + part.mappale + '; '
            foglio_pre= part.foglio
            lista.append(mappali)
    print(lista, foglio_pre, part.foglio)
    #document.add_paragraph(lista)
    par_0 = document.add_paragraph()
    par_0.alignment = WD_ALIGN_PARAGRAPH.CENTER
    par_0.bold=True
    par_0.add_run('IL DIRIGENTE', style = 'CduStyle').bold = True
    
    par_1 = document.add_paragraph('             Vista la richiesta (prot. n. ')
    par_1.alignement = WD_ALIGN_PARAGRAPH.DISTRIBUTE
    
    # par_1.add_run()
    par_1.add_run(prot).bold=True
    par_1.add_run(' del ' )
    par_1.add_run("%s" % data.strftime('%d/%m/%Y') +') ').bold=True
    par_1.add_run('presentata da ')
    par_1.add_run(soggetto.cognome.upper() + ' ' + soggetto.nome.title())
    par_1.add_run(nascita+', ' + '(c.f. ' + soggetto.codice_fiscale.upper() + ') residente in ' + soggetto.comune_residenza.title() + ' ' + soggetto.addr.title())
    # par_1.add_run(CIARI Geom. Riccardo nato a Carrara (54033) - Ms il 01/07/1966 (c.f. CRIRCR66L01B832D) residente in Carrara, Via Venezia n. 2,)
    par_1.add_run(' con la quale si richiede il Certificato di Destinazione Urbanistica di cui all\' art. 30 del D.P.R. 06.06.2001 n. 380, relativo ')
    if tot_particelle == 1:
        par_1.add_run('alla particella evidenziata nell\' allegata planimetria, censita al NCTR del Comune di Carrara al: ')
    else:
        par_1.add_run('alle particelle evidenziate nell\' allegata planimetria, censite al NCTR del Comune di Carrara al: ')

    par_1.add_run(lista)
            
            
    par_2 = document.add_paragraph('Visti gli strumenti urbanistici di questo Comune')
    par_2.alignement = WD_ALIGN_PARAGRAPH.DISTRIBUTE

    par_3 = document.add_paragraph()
    par_3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    
    runner = par_3.add_run('SI CERTIFICA', style ='CertificaStyle')


    

    par_4 = document.add_paragraph('che le prescrizioni urbanistiche riguardanti le aree sopra descritte ed individuate nella ')
    par_4.alignment = WD_ALIGN_PARAGRAPH.LEFT
    par_4.add_run('planimetria allegata alla presente, sono le seguenti :')

#   DEFINISCE I PIANI E DESTINAZIONI PER PARTICELLLA
    particelle = Cataprat.objects.filter(pratica_id=pau.pratica_id) #estrae tutte le particelle presenti nella pratica
    
    print('particelle',particelle)
    for c in particelle:
        particella_pau = Particella.objects.get(id=c.particella_id)
        print('particella_pau.id',particella_pau.id)

#   stampa la particella corrente
        par_01 = document.add_paragraph()
        par_01.alignment = WD_ALIGN_PARAGRAPH.LEFT
        par_01.paragraph_format.space_before = Pt(10)
        par_01.paragraph_format.space_after = Pt(10)
        runner = paragraph.add_run()
        runner.underline = WD_UNDERLINE.SINGLE
        runner = par_01.add_run('Fg. ' + particella_pau.foglio + ' map. ' + particella_pau.mappale, style = 'ParticellaStyle')
        
        print(c.id)
        # #   estrae i piani per singola istruttoria
        # particelle_istruttoria = Istruttoria.objects.filter(cataprat_id=c.id).order_by('destinazione_id')
        
        # piano_ex=0
        # piani_pau=[]
        # for p in particelle_istruttoria:
        #     print(p.id)
        #     pp={}
        #     # print('istruttoria',p.destinazione_id, p.parte)
        #     piano = Destinazione.objects.get(id=p.destinazione_id)
        #     order = Piano.objects.get(id=piano.piano_id)
        #     pp['id_piano'] = piano.piano_id
            
        #     pp['ordine'] = order.ordine
            
        #     piani_pau.append(pp)
        # print(piani_pau)
        # piani_pau = sorted(piani_pau, key=lambda x: x['ordine'])
        # print('lista',piani_pau)
        # piani_raggruppati = []
        # for key, group in groupby(piani_pau, lambda x: x['id_piano']):
        #         piani_raggruppati.append({'id_piano': key, 'count': len(list(group))})
        #         # piani_raggruppati.sort(key=ordine)
        # # piani_raggruppati=sorted(piani_raggruppati)
        # print(piani_raggruppati)
        #                         # print(piano.piano_id)
        #             ###########################################
        #             ####    STAMPA L'ELENCO DEI PIANI       ###
        #             ###########################################
        # for pd in piani_raggruppati:
        #                 pd = Piano.objects.get(id=pd['id_piano'])
        #                 par_01 = document.add_paragraph(style='List Bullet')
        #                 par_01.paragraph_format.line_spacing = Pt(11)

        #                 par_01.paragraph_format.space_before = Pt(6)
        #                 par_01.paragraph_format.space_after = Pt(6)
        #                 par_01.alignment = WD_ALIGN_PARAGRAPH.LEFT
        #                 # par_01.paragraph_format.space_after = Pt(5)
        #                 # par_01.bold=True
        #                 runner = par_01.add_run(pd.description, style='PianoStyle').italic=True
        #                 # print(pd.description)
        #                 ######################################################################
        #                 ####    STAMPA L'ELENCO DELLE DESTINAZIONI PER SINGOLO PIANO       ###
        #                 ######################################################################
        #                 for p in particelle_istruttoria:
        #                     dest_piano=[]
        #                     # print('istruttoria',p.destinazione_id, p.parte)
        #                     dd = Destinazione.objects.filter(Q(id=p.destinazione_id) & Q(piano_id=pd.id))
        #                     for x in dd:
        #                         pp={}
                                
        #                         if p.parte == False:
        #                             pp['descrizione']= ' - ' + x.description + ', intera particella;'
        #                         else:
        #                             pp['descrizione']= ' - ' + x.description + ', in parte;'
        #                         dest_piano.append(pp)
        #                         for ds in dest_piano:
        #                             par_101 = document.add_paragraph()
        #                             paragraph_format = par_101.paragraph_format
        #                             paragraph_format.left_indent = Inches(0.4)
        #                             paragraph_format.line_spacing = Pt(11)
        #                             paragraph_format.space_after = Pt(2)
        #                             par_101.alignment = WD_ALIGN_PARAGRAPH.LEFT
        #                             # par_101.font.size = Pt(9)
        #                             # par_01.bold=True
        #                             runner = par_101.add_run(ds['descrizione'], style ='DestinazioneStyle')
        #                             # print(dest_piano)
        #                             # print('destinazione')


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