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
from .models import *
from protocollo.models import *
from protocollo.views import block_readonly_write, can_edit


# Create your views here.
@login_required
# @user_passes_test(lambda u: u.groups.filter(name='editor_settore_6').count() == 1, login_url='home')
#   aggiunge una IDONEITA legata alla pratica 
############################################################
#           MATRICOLA
############################################################

### lista matricole

def MatricolaListView(request):
    matricole = Matricola.objects.all().order_by('-matricola_date','-num_impianto_id')
    print('matricole',matricole)
    context = {
          'matricole':matricole,
    }
    return render (request, 'ascensori/matricola_list.html', context)

###     AGGIUNGI

def MatricolaAddView(request, pk):

    submitted = False
    pratica = get_object_or_404(Pratica, id=pk)
    impianto = Impianto.objects.get(pratica_id=pk)
    print('impiantooooo',impianto.id)
    
    
    tipo=pratica.tipo_pratica_id
    print ('tipo----',tipo,'tipo_pratica',pratica.tipo_pratica)
    if tipo == 38: # esegue se la pratica è id=38  ascensori
        
        # conto le matricole nell'anno
        today = datetime.date.today()
        year = today.year
        numero = Matricola.objects.filter(matricola_date__icontains=year).count()
        if numero>0:
            matricole_numero = numero+1
        else:
            matricole_numero = 1
        print('ultimo numero',matricole_numero)
        # tot_matricole= matricole.count()
        
        if request.method == "POST":

            

            form = MatricolaForm(request.POST)
            if form.is_valid():
                    obj=form.save(commit=False)
                    obj.pratica_id = pk
                    obj.num_impianto_id = impianto.id
                    obj.save()
                    id = Impianto.objects.latest('id').id # ricava l'ID dell'ultimo soggetto
                    print('id',id)
                    return redirect('protocollo:pratica_detail_url' ,pk)
            else:
                 print('khjljlad25a8adfj')
        else:
            form = MatricolaForm()
            if 'submitted' in request.GET:
                submitted = True
                print('id_add',id)

            return render(request,'ascensori/matricola_add_view.html',{'form':form,'pratica':pratica,'impianto':impianto,'pk':pk, 'numero_proposto':matricole_numero})
    else :
        print('non arriva nessun dato')
        pass



@login_required
@user_passes_test(lambda u: u.groups.filter(name__in=['editor_settore_6',  'editor_settore_1']).exists(), login_url='home:index')
def MatricolaEditView(request, id):
    is_editor = can_edit(request.user)
    matricola = Matricola.objects.get(id=id)
    impianto = Impianto.objects.get(id=matricola.num_impianto_id)
    pk = impianto.pratica_id
    pratica = get_object_or_404(Pratica, id=pk)

    if request.method == 'POST':
        form = MatricolaForm(request.POST, instance=matricola)
        if form.is_valid():
            form.save()
            return redirect('protocollo:pratica_detail_url', pk)
        # Se il form non è valido, renderizza di nuovo la pagina con errori
    else:
        form = MatricolaForm(instance=matricola)

    # Render in tutti i casi tranne il redirect del form valido
    return render(request, 'ascensori/matricola_edit.html', {
        'is_editor': is_editor,
        'form': form,
        'pratica': pratica,
        'impianto': impianto,
        'matricola':matricola,
    })



###     VISUALIZZA

@login_required
def MatricolaDetailView(request, id):
   
    matricola = Matricola.objects.get(id=id)
    impianto = Impianto.objects.get(id=matricola.num_impianto_id)
    # dr=impianto.data_rival
    print('impianto....',impianto)
    pk= impianto.pratica_id
    pratica = get_object_or_404(Pratica, id=pk)
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
               'impianto': impianto, 
               'matricola':matricola,
               'particelle':particelle,
               'richiedente':richiedente}



    return render(request, 'ascensori/matricola_detail.html', context)


############################################################
#           IMPIANTO
############################################################


#       CREA
@user_passes_test(lambda u: u.groups.filter(name__in=['editor_settore_6',  'user_settore_6', 'user_settore_1']).exists(), login_url='home:index')


def ImpiantoAddView(request, pk):

    submitted = False
    pratica = get_object_or_404(Pratica, id=pk)
    tipo=pratica.tipo_pratica_id
    # num_num_impianto=nuovo_numero
    print (tipo,'ijdrtrdjlhd',pratica.tipo_pratica_id)
    if tipo == 38: # esegue se la pratica è id=38  ascensori

        if request.method == "POST":
            form = ImpiantoForm(request.POST)
            if form.is_valid():
                    obj=form.save(commit=False)
                    obj.pratica_id = pk
                    obj.save()
                    id = Impianto.objects.latest('id').id # ricava l'ID dell'ultimo soggetto
                    print('kadkhdydjjasg',id)
                    return redirect('protocollo:pratica_detail_url' ,pk)
            else:
                 print('Verificare presenza duplicati!')
                 return render(request,'ascensori/impianto_add.html',{'form':form,'pratica':pratica,'pk':pk})
        else:
            form = ImpiantoForm()
            if 'submitted' in request.GET:
                submitted = True
                print('id_add',id)

            return render(request,'ascensori/impianto_add.html',{'form':form,'pratica':pratica,'pk':pk})
    else :
        print('non arriva nessun dato')
        pass


##########  EDITA 
@login_required
# @user_passes_test(lambda u: u.groups.filter(name='editor_settore_6').count() == 1, login_url='home:index')
@user_passes_test(lambda u: u.groups.filter(name__in=['editor_settore_6', 'user_settore_6', 'user_settore_1']).exists(), login_url='home:index')


def ImpiantoEditView(request, id):
    is_editor = can_edit(request.user)
    print('gruppo',is_editor)
    # richiedente=[]
    impianto = Impianto.objects.get(id=id)
    try:
        matricola = Matricola.objects.get(num_impianto_id=impianto.id)
        print('8789879 impianto', impianto)
    except:
        print('ouaoduooaduoaudoad nessuna matricola')
        matricola = None
        pass

    # dr=impianto.data_rival
    print('impianto....',impianto)
    pk= impianto.pratica_id
    pratica = get_object_or_404(Pratica, id=pk)
    # anaprat = Anaprat.objects.filter(pratica_id=pk)
    # for s in anaprat:
    #     soggetti={}
    #     sogg = Soggetto.objects.get(id=s.soggetto_id)
    #     soggetti['id_anaprat']=s.id
    #     soggetti['cognome']=sogg.cognome
    #     soggetti['nome']=sogg.nome

    #     richiedente.append(soggetti)
    print('pk',pk)
    if request.method == 'POST':
       form = ImpiantoForm(request.POST, instance=impianto)
       if form.is_valid():
            # update the existing `Pratica` in the database
            form.save()
            # obj=form.savecommit=False)
            # obj.delta_years = impianto.delta_years
            # obj.save()
            # redirect to the detail page of the `Pratica` we just updated
            
            
            return redirect('protocollo:pratica_detail_url', pk )
    else:
        form = ImpiantoForm(instance=impianto)
        return render(request,'ascensori/impianto_edit.html',{'is_editor':is_editor,'form': form, 'pratica':pratica, 'matricola':matricola})



#############################################################
#   moduli per stampe
#############################################################
from django.http import HttpResponse
from docx import Document
from docx import *
from docx.shared import Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_UNDERLINE
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.section import WD_ORIENT
from docx.enum.dml import MSO_THEME_COLOR
from docx.shared import Pt, Inches, Mm
import os
from datetime import date
from collections import OrderedDict
import numpy as np

# import pandas as pd
from itertools import groupby
from io import BytesIO

# nomi dei TipoSoggetto che identificano lo stesso ruolo: in tabella esistono duplicati
# dello stesso tipo con nomi diversi per maiuscolo/minuscolo (es. id 1 'Richiedente' e id 29 'richiedente')
TIPI_SOGGETTO = {
    'richiedente': ['richiedente'],
    'titolare': ['titolare impianto'],
    'amministratore': ['amministratore di condominio'],
    'verifiche_periodiche': ['ditta verifiche periodiche'],
    'manutentrice': ['ditta manutentrice'],
    'produttrice': ['ditta produttrice'],
    'installatrice': ['ditta installatrice'],
    'istruttore': ['tecnico istruttore', 'istruttore'],
}


def anaprat_per_tipo(pratica_id, tipi):
    """Restituisce gli Anaprat della pratica che hanno uno dei tipi soggetto indicati.

    tipi: chiave di TIPI_SOGGETTO, nome di TipoSoggetto, oppure lista misto di chiavi e nomi.
    Il match avviene sul nome del tipo (case-insensitive) e non sull'id, perche' in tabella
    esistono duplicati dello stesso tipo con nomi diversi per maiuscolo/minuscolo.
    """
    if isinstance(tipi, str):
        tipi = [tipi]
    nomi = []
    for t in tipi:
        nomi.extend(TIPI_SOGGETTO.get(str(t).lower(), [t]))
    q_tipi = Q()
    for nome_tipo in nomi:
        q_tipi |= Q(tipo__name__iexact=nome_tipo)
    return Anaprat.objects.filter(Q(pratica_id=pratica_id) & q_tipi).select_related('tipo').order_by('id')

#############################################################
#       STAMPA MATRICOLA ASCENSORE
#############################################################


def CreateMatricolaRtf(request,id):
    pratica = Pratica.objects.get(id=id)
    impianto = Impianto.objects.get(pratica_id=pratica.id) # impianto da produrre
    try:
        matricola = Matricola.objects.get(num_impianto_id=impianto.id)
    except:
         matricola = 'None'
    print(impianto, matricola)
    
    atto = str(pratica.tipo_pratica)+'_'+'matricola'+'_'+str(matricola.numero) +'_'+str(matricola.matricola_date.year)+'.docx'
    
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
    section.footer_distance = Mm(5)
    
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

    f2=footer.add_paragraph()
    f2.paragraph_format.space_after = Pt(0)
    f2.paragraph_format.space_before = Pt(0)
    f2.add_run("geom. Carlo Alberto Nicolini - 0585 641252 - carloalberto.nicolini@comune.carrara.ms.it", style = 'FooterStyle')

    #   IMPOSTA IL FOOTER
    
    
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
    p0_1.add_run('Settore 6 - Governo del territorio', style = 'SottoHeaderStyle').bold = True

    p0_1_1 = document.add_paragraph()
    p0_1_1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p0_1_1.add_run('Servizio 6.1 - Urbanistica e edilizia privata - U.O. 6.1.1 Pianificazione urbanistica', style = 'SottoHeaderStyle')
    # p0_1.add_run(str(impianto.impianto_number)+ ' del ' +"%s" % impianto.impianto_date.strftime('%Y'), style='CduStyle').bold=True
         
    paragraph_format = paragraph.paragraph_format
    paragraph_format.alignment = 1 # 1 - allineato centrato 0 - allineato a sx
    p0_2 = document.add_paragraph()
    p0_2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p0_2.bold=True
    p0_2.add_run('', style = 'NormalStyle').bold = True
    
    matricola = Matricola.objects.get(num_impianto_id=impianto.id)
    # print('matricola',matricola)
    impianto = Impianto.objects.get(pratica_id=id)
    # print('impianto',impianto)
    pratica = Pratica.objects.get(id=impianto.pratica_id)
    print('pratica',pratica)

            
    all_rich = Anaprat.objects.filter(pratica_id=pratica.id)
    print('richiedenti', all_rich)
             



    
    # ESTRAE le particelle interessate e le elenca
    particelle = Cataprat.objects.filter(pratica_id=impianto.pratica_id) 
    tot_particelle = particelle.count()
    print('to',tot_particelle)
    pratica = Pratica.objects.get(id=impianto.pratica_id) # recupera i dati della pratica
    # recupera il primo richiedente
    # estrae i soggetti della pratica
    sog = Anaprat.objects.filter(pratica_id = impianto.pratica_id).select_related('tipo')
    print('soggetti',sog)
    richiedente = None
    ditta_man = None
    for s in sog :
        tipo = (s.tipo.name if s.tipo else '').strip().lower()
        if tipo in TIPI_SOGGETTO['richiedente'] or tipo in TIPI_SOGGETTO['titolare']:
            richiedente = s.soggetto_id
            print('rich',richiedente)
        elif tipo in TIPI_SOGGETTO['amministratore']:
            richiedente = s.soggetto_id
            print('rich',richiedente)
        elif tipo in TIPI_SOGGETTO['manutentrice']:
            ditta_man = s.soggetto_id            
            print('ditta_man',ditta_man)
        else:
             pass

    # se nessun soggetto ha uno dei tipi attesi, uso il primo soggetto della pratica
    if richiedente is None:
        primo = sog.first()
        if primo is not None:
            richiedente = primo.soggetto_id
            print('rich_fallback',richiedente)

    print('richiedente', richiedente)
    soggetto = get_object_or_404(Soggetto, id=richiedente)

    if soggetto.comune_nascita:
        # verifico se maschio o femmina 
        
        if soggetto.codice_fiscale !='':
            sesso_cf = soggetto.codice_fiscale[9:11]
            print('manca il codice fiscale')
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
    else:
        pass
    #document.add_paragraph(lista)
    par_0 = document.add_paragraph()
    par_0.alignment = WD_ALIGN_PARAGRAPH.CENTER
    par_0.bold=True
    par_0.add_run('IL DIRIGENTE', style = 'CduStyle').bold = True
    
    par_1 = document.add_paragraph()
    par_1.add_run('''     Vista''', style = 'NormalStyle').bold = True
    par_1.add_run(''' l\'istanza pervenuta in data ''' +"%s" % pratica.data_prot_gen.strftime('%d/%m/%Y') +  ''' prot. n. ''' , style = 'NormalStyle')
    
    par_1.alignement = WD_ALIGN_PARAGRAPH.DISTRIBUTE
    
    # par_1.add_run()
    par_1.add_run(pratica.prot_gen).bold=True
    # par_1.add_run(' del ' )
    # par_1.add_run("%s" % data.strftime('%d/%m/%Y') +') ').bold=True
    par_1.add_run(''' inoltrata da ''', style = 'NormalStyle')
    if soggetto.cognome :
          cognome=soggetto.cognome
    if soggetto.nome:
          nome =soggetto.nome
    else:
          nome=''

    richiedente = str(cognome)+ ' ' + str(nome)
    cf = soggetto.codice_fiscale
    lungh = len(cf)
    # definisce la dicitura "residente in" o "con sede in" se il codice fiscale ha 16 caratteri o meno
    if lungh==16 and soggetto.addr_sede is None or soggetto.addr_sede =='':
        dove = ' residente in '
        par_1.add_run(richiedente.upper() )
        par_1.add_run(nascita+', ' + '(c.f. ' + str(soggetto.codice_fiscale.upper()) + ')'+ dove + str(soggetto.comune_residenza.title()) + ' ' + str(soggetto.addr.title()) , style = 'NormalStyle')
 
    else :
        dove = ' con sede in '
        par_1.add_run(richiedente.upper() )
        par_1.add_run( ' ' + str(soggetto.addr_sede.title()), style = 'NormalStyle')

   
    par_1.add_run(''', tendente ad ottenere l\'assegnazione del numero di matricola per la messa in esercizio dell\'impianto elevatore installato nell\'immobile posto in Carrara ''', style = 'NormalStyle') 
    if str(pratica.street) != '':
                      par_1.add_run(str(pratica.street), style = 'NormalStyle')
    if str(pratica.housenumber) != '':
                      par_1.add_run(' n. ' + str(pratica.housenumber), style = 'NormalStyle')
    par_1.add_run(' ( art.12 DPR 162/99 e s.m.i.);', style = 'NormalStyle')
                  
    if tot_particelle != 0:
        par_1.add_run(' distinto catastalmente al ', style = 'NormalStyle')

        par_1.add_run(lista, style = 'NormalStyle')
            
    
    par_2 = document.add_paragraph()
    par_2.add_run('     Visto ').bold = True
    par_2.add_run('il D.P.R. 30 aprile 1999, n. 162, ', style = 'NormalStyle')
    par_2.add_run('“Regolamento recante norme per l\'attuazione della direttiva 2014/33/UE, relativa agli ascensori \
ed ai componenti di sicurezza degli ascensori, nonché per l\'esercizio degli ascensori” ; ', style = 'NormalStyle').italic=True
    par_2.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
    
    
    
    par_2_2 = document.add_paragraph()
    par_2_2.add_run('     Vista').bold = True
    par_2_2.add_run(' la documentazione agli atti ;', style = 'NormalStyle')
    par_2_2.alignement = WD_ALIGN_PARAGRAPH.DISTRIBUTE
    
    # par_2_3 = document.add_paragraph('VISTA  la deliberazione di Giunta Toscana n. 700/2005;')
    # par_2_3.alignement = WD_ALIGN_PARAGRAPH.DISTRIBUTE
    
    # par_2_4 = document.add_paragraph('VISTA  la deliberazione di Giunta Comunale n. 571 del 07/10/2010 - Accertamento dell\'idoneità abitativa per ricongiungimento familiare da parte di stranieri;')
    # par_2_4.alignement = WD_ALIGN_PARAGRAPH.DISTRIBUTE
    
    par_2_5 = document.add_paragraph()
    par_2_5.alignement = WD_ALIGN_PARAGRAPH.DISTRIBUTE
    par_2_5.add_run('      Tutto ciò premesso e considerato assegna la Matricola n. ', style = 'NormalStyle')

    # crea la matricola
    today = datetime.date.today()
    year = today.year
    s = matricola.numero
    padding = '0'
    l=3
    matricola_number = f'{s:{padding}>{l}}'

    par_3 = document.add_paragraph()
    par_3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    print(pratica.street_id)
    via = Civici.objects.get(id=pratica.street_id)
    
    par_3.add_run('MS-'+str(year) +'-'+str(matricola_number), style ='CertificaStyle')
    
    par_3_1 = document.add_paragraph()
    par_3_1.alignement = WD_ALIGN_PARAGRAPH.DISTRIBUTE
    if impianto:
        numero = impianto.num_impianto
        par_3_1.add_run('all’impianto elevatore  num. ' , style = 'NormalStyle')
        par_3_1.add_run(str(numero) , style = 'NormalStyle').bold=True
        par_3_1.add_run(', installato nell’immobile sito in ',style = 'NormalStyle')
        par_3_1.add_run(str(via) +', '+ pratica.housenumber, style = 'NormalStyle')

    
    
    par_3_2 = document.add_paragraph()
    par_3_2.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY
    par_3_2.add_run('''Il proprietario dell’impianto, o il suo legale rappresentante, sono tenuti ad effettuare regolari \
manutenzioni, nonché a sottoporre lo stesso a verifica periodica ogni due anni (Art.13 comma 1 DPR 162/99 e s.m.i.).
Il soggetto che eseguirà la verifica periodica dovrà rilasciare al proprietario, nonché alla ditta \
incaricata della manutenzione, il verbale relativo e, ove negativo, ne comunicherà l'esito a questo \
settore comunale per i provvedimenti di competenza (Art.13 comma 2 DPR 162/99 e s.m.i.).''', style = 'NormalStyle')
    par_3_3 = document.add_paragraph()
    par_3_3.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY
    par_3_3.add_run('Il presente provvedimento verrà trasmesso a :', style = 'NormalStyle')

    # titolare impianto (richiedente-titolare impianto-amministratore di condominio)
    titolare = anaprat_per_tipo(pratica.id, ['richiedente', 'titolare', 'amministratore']).first()
    if titolare is None:
        titolare = sog.first()
    print('titolare', titolare.tipo.name if titolare and titolare.tipo else None)
    soggetto_titolare = get_object_or_404(Soggetto, id=titolare.soggetto_id)
    print('soggetto_titolare', soggetto_titolare)

    if soggetto_titolare != '':
      
    
        
        par_4 = document.add_paragraph()
        par_4.alignement = WD_ALIGN_PARAGRAPH.DISTRIBUTE
        par_4.paragraph_format.first_line_indent = Inches(0.3)
        par_4.add_run('- ')
        par_4.add_run(str(soggetto_titolare).upper() +' ', style = 'NormalStyle').bold=True
        if soggetto_titolare.addr and soggetto_titolare.addr_sede is None or soggetto_titolare.addr_sede =='':
            addr = soggetto_titolare.addr.title()
            
            par_4.add_run(str(soggetto_titolare.addr.title())+', ', style = 'NormalStyle')
        else:
            if soggetto_titolare.addr_sede:
                addr = soggetto.addr_sede.title()
                par_4.add_run(str(addr.title())+', ', style = 'NormalStyle')
        
        par_4.add_run( str(soggetto_titolare.comune_residenza.title()), style = 'NormalStyle')
        # stabilisce il titolare dell'impianto
        tipo_titolare = (titolare.tipo.name if titolare.tipo else '').strip()
        if tipo_titolare.lower() in ('richiedente', 'titolare impianto'):

            tipo_titolare = 'titolare dell\'impianto'
        
        par_4.add_run(', in qualità di ' + tipo_titolare + ';', style = 'NormalStyle')

        if soggetto.pec:
            addr = soggetto.addr.upper()
            par_4.add_run(' PEC : ' + str(soggetto.pec), style = 'NormalStyle')
        else:
            if soggetto.email:
                addr = soggetto.addr.title()
                par_4.add_run(' Email : ' +str(soggetto.email), style = 'NormalStyle')

    else :
         print('non trovato amministratore di condominio')




    # ditta incaricata visite periodiche
    richiedente1 = anaprat_per_tipo(pratica.id, 'verifiche_periodiche').first()
    soggetto1 = get_object_or_404(Soggetto, id=richiedente1.soggetto_id)

    par_5 = document.add_paragraph()
    par_5.alignement = WD_ALIGN_PARAGRAPH.DISTRIBUTE
    par_5.paragraph_format.first_line_indent = Inches(0.3)
    par_5.add_run('- ')
    par_5.add_run(str(soggetto1).upper() +' ', style = 'NormalStyle').bold=True
    if soggetto1.addr:
        addr = soggetto1.addr.title()
        par_5.add_run(str(addr)+', ', style = 'NormalStyle')
    else:
         if soggetto1.addr_sede:
            addr = soggetto1.addr_sede.title()
            par_5.add_run(str(addr)+', ', style = 'NormalStyle')
    par_5.add_run( str(soggetto1.comune_residenza), style = 'NormalStyle')
   
    par_5.add_run(', ente competente di cui al comma 2 lett. e del dpr 162/99 e s.m.i. incaricato per le visite periodiche;         ', style = 'NormalStyle')
    if soggetto1.pec:
        addr = soggetto1.addr.upper()
        par_5.add_run(' PEC : ' + str(soggetto1.pec), style = 'NormalStyle')
    else:
        if soggetto1.email:
            addr = soggetto1.addr.title()
            par_5.add_run(' Email : ' +str(soggetto1.email), style = 'NormalStyle')
    

    # ditta incaricata visite periodiche
    richiedente1 = anaprat_per_tipo(pratica.id, 'manutentrice').first()
    soggetto2 = get_object_or_404(Soggetto, id=richiedente1.soggetto_id)
    cognome = soggetto2.cognome.title()
    nome = soggetto2.nome.title() 

    print(cognome+ ' '+nome)   
    par_5_1 = document.add_paragraph()
    par_5_1.alignement = WD_ALIGN_PARAGRAPH.DISTRIBUTE
    par_5_1.paragraph_format.first_line_indent = Inches(0.3)
    par_5_1.add_run('- ', style = 'NormalStyle')
    par_5_1.add_run(str(cognome).upper() +' ' + str(nome).upper(), style = 'NormalStyle').bold=True
    if soggetto2.addr:
        addr = soggetto2.addr.title()
        par_5_1.add_run(str(addr)+', ', style = 'NormalStyle')
    else:
         if soggetto2.addr_sede:
            addr = soggetto2.addr_sede.title()
            par_5_1.add_run(str(addr)+', ', style = 'NormalStyle')
    par_5_1.add_run( str(soggetto2.comune_residenza), style = 'NormalStyle')
   
    par_5_1.add_run(', ditta incaricata della manutenzione;                     ', style = 'NormalStyle')
    
    

    
    if soggetto2.pec:
        addr = soggetto2.addr.title()
        par_5_1.add_run(' PEC : ' + str(soggetto2.pec), style = 'NormalStyle')
    else:
        if soggetto2.email:
            addr = soggetto2.addr.title()
            par_5_1.add_run(' Email : ' +str(soggetto2.email), style = 'NormalStyle')



    par_5_2 = document.add_paragraph()
    par_5_2.alignement = WD_ALIGN_PARAGRAPH.LEFT
    par_5_2.add_run('''Avverso il presente provvedimento è ammesso ricorso giurisdizionale al \
TAR Toscana entro il termine di 60 giorni dalla notifica, ovvero ricorso straordinario al \
Presidente della Repubblica entro il termine di 120 giorni dalla notifica medesima.''', style = 'NormalStyle')

    


    par_8_3 = document.add_paragraph()
    # par_8_3.paragraph_format.first_line_indent = Inches(0.3)
    par_8_3.paragraph_format.space_before = Pt(1)
    par_8_3.paragraph_format.space_after = Pt(1)
    par_8_3.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
    par_8_3.add_run('Carrara, data della sottoscrizione digitale', style='NormalStyle' )

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

    p09 = document.add_paragraph()
    p09.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p09.paragraph_format.space_before = Pt(10)
    p09.add_run('Documento firmato digitalmente ai sensi e per gli effetti di cui agli artt.21, 23, 23bis e 23ter del D.LGS. 82 del 7 marzo 2005 e s.m.i. - Codice dell\'Amministrazione Digitale', style='NormalStyle').italic=True


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





#############################################################
#   moduli per stampe
#############################################################
from django.http import HttpResponse
from docx import Document
from docx import *
from docx.shared import Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_UNDERLINE
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.section import WD_ORIENT
from docx.enum.dml import MSO_THEME_COLOR
from docx.shared import Pt, Inches, Mm
import os
from datetime import date
from collections import OrderedDict
import numpy as np

# import pandas as pd
from itertools import groupby
from io import BytesIO


#######################################################
##### RISPOSTA VVFF ########
########################################################
def Risposta_vvff(request, pk):
    pratica = get_object_or_404(Pratica, id=pk)
    print (pratica)
    print('tipo',pratica.tipo_pratica)

    if pratica.tipo_pratica_id == 38: # per ASCENSORI
            
            atto = 'risposta_vvff_' +str(pratica.tipo_pratica) + '_' +  str(pratica.prot_gen) +'_' + "%s" % pratica.data_prot_gen.strftime('%Y%m%d') +'.docx'
            
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
            obj_font.name = 'Arial'

        #   IMPOSTA IL FOOTER
            footer=section.footer

            f1=footer.add_paragraph()
            f1.paragraph_format.space_after = Pt(0)
            f1.paragraph_format.space_before = Pt(0)
            f1.add_run("P.za due giugno,1 54033 - Carrara (MS) PEC : comune.carrara@postecert.it", style = 'FooterStyle')

            f2=footer.add_paragraph()
            f2.paragraph_format.space_after = Pt(0)
            f2.paragraph_format.space_before = Pt(0)
            f2.add_run("geom. Carlo Alberto Nicolini - 0585 641252 - carloalberto.nicolini@comune.carrara.ms.it", style = 'FooterStyle')

        
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
            obj_charstyle = obj_styles.add_style('NormalStyleItalic', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = True

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
            obj_font.size = Pt(8)
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
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('DestinazioneStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(9)
            obj_font.name = 'Times New Roman'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('CertificaStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.bold=True
            obj_font.size = Pt(14)
            obj_font.name = 'Times New Roman'
           

            
            # Changing the orientation to landscape
            section.orientation = WD_ORIENT.LANDSCAPE

            # paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

            docx_title=atto
            
            # Inserisci l'immagine nel documento
            # https://www.shibutan-bloomers.com/python_library_python-docx-2_en/7091/
            # CON ChatGpt

            # Definisci il percorso dell'immagine
            image_name = 'logo_decorato.png'
            image_path = os.path.join('static/img/', image_name)

            # Inserisci l'immagine nel documento
        
            run = paragraph.add_run()
            run.add_picture(image_path, width=Inches(1.6))
            # Posiziona centralmente l'immagine
            paragraph_format = paragraph.paragraph_format
            paragraph_format.alignment = 1 # 1 - allineato centrato 0 - allineato a sx
            

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
            
            #

        # #    stampo i dati della U.O.

            # p1 = document.add_paragraph()
            # p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
            # p1.add_run('Servizio 7.2 SUAP, demanio e paesaggio - U.O. 7.4 S.U.A.P.',style = 'FooterStyle')

            


            
            # recupera i dati della pratica
            pratica = Pratica.objects.get(id=pratica.id) 
            
            

            # # recupera TUTTI i richiedenti
            
            all_rich = Anaprat.objects.filter(pratica_id=pratica.id)
            print('richiedenti----', all_rich)
            for a in all_rich:
                soggetto=Soggetto.objects.get(id=a.soggetto_id)
               

                
                p2_01 = document.add_paragraph()
                p2_01.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                p2_01.paragraph_format.space_after = Pt(9)
                p2_01.add_run('' , style='NumCduStyle').bold=True 
                    
                #inserisce il nominativo
                p2 = document.add_paragraph()
                p2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                p2.paragraph_format.space_after = Pt(3)
                p2.add_run('Spett.Le ' + str.upper(soggetto.cognome) + '  ' , style='NumCduStyle').bold=True  
                p2.add_run(str.title(soggetto.nome), style='NumCduStyle')
                
                p2_1 = document.add_paragraph()
                p2_1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                p2_1.paragraph_format.space_after = Pt(1)
                if soggetto.addr and soggetto.addr_sede == '':
                    p2_1.add_run(str.title(soggetto.addr) , style='NumCduStyle')
                else:
                    p2_1.add_run(str.title(soggetto.addr_sede) , style='NumCduStyle')
                p2_2 = document.add_paragraph()
                p2_2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                p2_2.paragraph_format.space_after = Pt(4)
                if soggetto.comune_residenza:
                    p2_2.add_run(str.title(soggetto.comune_residenza) , style='NumCduStyle')

               
                        
                if soggetto.email and soggetto.pec == '':
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
                    
            # ESTRAE le particelle interessate e le conta
            particelle = Cataprat.objects.filter(pratica_id=pratica.id) 
            tot_particelle = particelle.count()
                
            print('to',tot_particelle)
                

            # print(particelle)
            
            foglio_pre="" # imposta a blank il foglio precedente
            lista =[] # lista le particelle nella pratica, compresi eventuali subalterni
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
                                mappali = ' fg ' + part.foglio + ' map ' + part.mappale
                                if p.subalterno !='-':
                                      mappali = mappali + ' sub '+str(p.subalterno)
                            foglio_pre= part.foglio
                            lista.append(mappali)
                    print(lista, foglio_pre, part.foglio)
                    #document.add_paragraph(lista)
            else:
                    prot = pratica.prot_gen
                    data = pratica.data_prot_gen
            
            
            ####################################
            #      DITTA
            ###################################
            # recupera il primo richiedente (Q(status='on-sale') | Q(status='paused'))
            rich = anaprat_per_tipo(pratica.id, 'richiedente').first() or Anaprat.objects.filter(pratica_id=pratica.id).order_by('id').first()
            # recuperea il tecnico istruttore
            '''
            istr_tec = anaprat_per_tipo(pratica.id, 'istruttore').first()
            '''
            '''   
            s_istr_tec = Soggetto.objects.get(id=istr_tec.soggetto_id)
            '''
            print('richiedenti', rich)
            soggetto = Soggetto.objects.get(id=rich.soggetto_id)
            # verifico che esista il codice fiscale
            # verifico se maschio o femmina 
            sesso_cf = soggetto.codice_fiscale[6:8]
            if type(sesso_cf) is int:
                if int(sesso_cf)>40:
                    nascita =' nata a ' + soggetto.comune_nascita.title() + ' il ' + str(soggetto.data_nascita)
                else:
                    nascita =' nato a ' + soggetto.comune_nascita.title() + ' il ' + str(soggetto.data_nascita)
                    print('sesso_cf', sesso_cf)
            prot = pratica.prot_gen
            data = pratica.data_prot_gen

            if pratica.housenumber :
                ubicazione=str(pratica.street) + ' ' + str(pratica.housenumber)
            else:
                ubicazione =  str(pratica.street).title()

            
            ####################################
            #      OGGETTO
            ###################################
            
            if ubicazione == '':
                preambolo='Comunicazione del Comando VV.FF. del ' + "%s" % pratica.data_prot_gen.strftime('%d') +'/'+ "%s" % pratica.data_prot_gen.strftime('%m')+'/'+"%s" % pratica.data_prot_gen.strftime('%Y') +  ' Prot. Gen ' + str(pratica.prot_gen)+ ' - '
                pre_oggetto = str(pratica.oggetto) + ' ' + str(ubicazione)
            else:
                print('esticazzi')
                pass
#soggetto.cognome + ' ' + soggetto.nome + ' Prot. Gen. n. ' + pratica.prot_gen + ' del ' + "%s" % pratica.data_prot_gen.strftime('%d') +'/'+ "%s" % pratica.data_prot_gen.strftime('%m')+'/'+"%s" % pratica.data_prot_gen.strftime('%Y')

            
            oggetto_lettera = preambolo 
            
            

            p2_4 = document.add_paragraph()
            p2_4.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p2_4.paragraph_format.space_before = Pt(50)
            p2_4.add_run(str('Oggetto : ') , style='NumCduStyleItalic').bold=True
            # p2_4 = document.add_paragraph()
            # p2_4.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p2_4.paragraph_format.space_after = Pt(4)
            p2_4.add_run(str(oggetto_lettera), style='NumCduStyleItalic').bold=True
            p2_4.add_run(' ', style='NumCduStyleItalic').bold=True
            p2_4.add_run( (lista), style='NumCduStyleItalic').bold=True
            
            p2_4_1 = document.add_paragraph()
            p2_4_1.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p2_4_1.paragraph_format.left_indent = Inches(0.5)
            p2_4_1.add_run(str(pre_oggetto), style='HeaderStyle')


            ####################################
            #      DITTA
            ###################################
            # recupera il primo richiedente (Q(status='on-sale') | Q(status='paused'))
            rich = anaprat_per_tipo(pratica.id, 'richiedente').first() or Anaprat.objects.filter(pratica_id=pratica.id).order_by('id').first()
            print('richiedenti', rich)
            soggetto = get_object_or_404(Soggetto, id=rich.soggetto_id)
            # verifico che esista il codice fiscale
            
            # verifico se maschio o femmina 
            sesso_cf = soggetto.codice_fiscale[6:8]
            if type(sesso_cf) is int:
                if int(sesso_cf)>40:
                    nascita =' nata a ' + soggetto.comune_nascita.title() + ' il ' + str(soggetto.data_nascita)
                else:
                    nascita =' nato a ' + soggetto.comune_nascita.title() + ' il ' + str(soggetto.data_nascita)
                    print('sesso_cf', sesso_cf)
            prot = pratica.prot_gen
            data = pratica.data_prot_gen

            
            p2_5 = document.add_paragraph()
            p2_5.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY
            p2_5.paragraph_format.first_line_indent = Inches(0.5)
            p2_5.paragraph_format.space_before = Pt(1)
            p2_5.paragraph_format.space_after = Pt(4)
            p2_5.add_run(str('''Con riferimento a quanto in oggetto, come già segnalato con precedenti note relativamente \
alle Vs comunicazioni inerenti gli impianti Fuori Servizio, si rappresenta che per l'adozione dei provvedimenti di competenza \
è necessario che codesto comando indichi, nelle comunicazioni di segnalazione, oltre all'indirizzo dell\'immobile oggetto di intervento \
anche i dati necessari ad individuare il proprietario/titolare/amministratore gestore dell'impianto.'''))
            
            par_3 = document.add_paragraph()
            par_3.paragraph_format.first_line_indent = Inches(0.3)
            # par_1 = paragraph_format.left_indent = Inches(0.5)
            par_3.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY
            par_3.paragraph_format.space_before = Pt(1)
            par_3.paragraph_format.space_after = Pt(4)
            par_3.add_run()
            par_3.add_run(('Distinti saluti'))
            
            par_8_3 = document.add_paragraph()
            # par_8_3.paragraph_format.first_line_indent = Inches(0.3)
            par_8_3.paragraph_format.space_before = Pt(1)
            par_8_3.paragraph_format.space_after = Pt(1)
            par_8_3.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY
            par_8_3.add_run('Carrara, data della sottoscrizione digitale' )

            par_8_4 = document.add_paragraph()
            par_8_4.paragraph_format.space_before = Pt(1)
            par_8_4.paragraph_format.space_after = Pt(1)
            par_8_4.alignement = WD_ALIGN_PARAGRAPH.CENTER
            par_8_4.paragraph_format.first_line_indent = Inches(4.2)
            par_8_4.add_run('Il Dirigente' )

            par_8_5 = document.add_paragraph()
            par_8_5.paragraph_format.space_before = Pt(1)
            par_8_5.paragraph_format.space_after = Pt(1)
            par_8_5.alignement = WD_ALIGN_PARAGRAPH.CENTER
            par_8_5.paragraph_format.first_line_indent = Inches(4.2)
            par_8_5.add_run('Ing. Luca Amadei' )

            p09 = document.add_paragraph()
            p09.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p09.paragraph_format.space_before = Pt(10)
            p09.add_run('Documento firmato digitalmente ai sensi e per gli effetti di cui agli artt.21, 23, 23bis e 23ter del D.LGS. 82 del 7 marzo 2005 e s.m.i. - Codice dell\'Amministrazione Digitale', style='NormalStyle').italic=True


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
        



#############################################################
#       STAMPA ORDINANZA DI FERMO ASCENSORE VVFF
#############################################################


def CreateOrdinanzaRtf(request,id):
    pratica = Pratica.objects.get(id=id)
    try:
        impianto = Impianto.objects.get(pratica_id=pratica.id) # impianto da produrre
    except:
        impianto = ''
    try:
        matricola = Matricola.objects.get(num_impianto_id=impianto.id)
    except:
        matricola = ''
    print(impianto, matricola)
    
    atto = str(pratica.tipo_pratica)+'_'+'ordinanza'+'_'+str(pratica.prot_gen) +'_'+str(pratica.data_prot_gen.year)+'.docx'
    
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
    f1.add_run(" PEC : comune.carrara@postecert.it", style = 'FooterStyle')

    f2=footer.add_paragraph()
    f2.paragraph_format.space_after = Pt(0)
    f2.paragraph_format.space_before = Pt(0)
    f2.add_run("geom. Carlo Alberto Nicolini - 0585 641252 - carloalberto.nicolini@comune.carrara.ms.it", style = 'FooterStyle')

    #   IMPOSTA IL FOOTER
    
    
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
    p0_1.add_run('Settore 6 - Governo del territorio', style = 'SottoHeaderStyle').bold = True

    p0_1_1 = document.add_paragraph()
    p0_1_1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p0_1_1.add_run('Servizio 6.1 - Urbanistica e edilizia privata - U.O. 6.1.1 Pianificazione urbanistica', style = 'SottoHeaderStyle')
    # p0_1.add_run(str(impianto.impianto_number)+ ' del ' +"%s" % impianto.impianto_date.strftime('%Y'), style='CduStyle').bold=True
         
    paragraph_format = paragraph.paragraph_format
    paragraph_format.alignment = 1 # 1 - allineato centrato 0 - allineato a sx
    p0_2 = document.add_paragraph()
    p0_2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p0_2.bold=True
    p0_2.add_run('', style = 'NormalStyle').bold = True
    
    try:
        matricola = Matricola.objects.get(num_impianto_id=impianto.id)
    except:
        matricola = ''
    # print('matricola',matricola)
    impianto = Impianto.objects.get(pratica_id=id)
    # print('impianto',impianto)
    pratica = Pratica.objects.get(id=impianto.pratica_id)
    print('pratica',pratica)
########        DEFINISCE I DATI CORRENTI PER IMPIANTO E MATRICOLA
    # impianto = Impianto.object.get(id=id)
    # matricola = Matricola.objects.get
 # # recupera TUTTI i richiedenti
            
    all_rich = Anaprat.objects.filter(pratica_id=pratica.id)
    print('richiedenti', all_rich)
    for a in all_rich:
                soggetto=Soggetto.objects.get(id=a.soggetto_id)
               
                    
     


    
    # ESTRAE le particelle interessate e le elenca
    particelle = Cataprat.objects.filter(pratica_id=impianto.pratica_id) 
    tot_particelle = particelle.count()
    print('to',tot_particelle)
    pratica = Pratica.objects.get(id=impianto.pratica_id) # recupera i dati della pratica
    # recupera il primo richiedente
    rich = anaprat_per_tipo(impianto.pratica_id, 'richiedente').first() or Anaprat.objects.filter(pratica_id=impianto.pratica_id).order_by('tipo_id').first()
    # (Q(pratica_id=pratica.id)&
    #                                          Q(matricola_date__icontains=year))
    print(rich)
    print('richiedenti', rich)
    soggetto = Soggetto.objects.get(id=rich.soggetto_id)

    if soggetto.comune_nascita:
        # verifico se maschio o femmina 
        
        if soggetto.codice_fiscale !='':
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
    else:
        pass
    #document.add_paragraph(lista)
    par_0 = document.add_paragraph()
    par_0.alignment = WD_ALIGN_PARAGRAPH.CENTER
    par_0.bold=True
    par_0.add_run('ORDINANZA FERMO IMPIANTO ( ai sensi dell\'art. 14 e segg. del DPR 162/99)', style = 'CduStyle').bold = True
    

    par_0_1 = document.add_paragraph()
    par_0_1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    par_0_1.bold=True
    par_0_1.add_run('Il Dirigente del Settore', style = 'HeaderStyle').bold = True

    par_0_1 = document.add_paragraph()
    par_0_1.paragraph_format.first_line_indent = Inches(0.5)
    par_0_1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    par_0_1.add_run('''Vista la comunicazione del Comando VV.FF. assunta al prot.gen. n. ''' + str(pratica.prot_gen) + ''' del ''' + "%s" % data.strftime('%d/%m/%Y') +''' relativa ad intervento presso l'edificio posto in ''' )
    par_0_1.add_run( str(pratica.street) + ''', ''' + pratica.housenumber + ''', per ''' + str(pratica.oggetto) + ''';''')

    par_0_2 = document.add_paragraph()
    par_0_2.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    par_0_2.add_run('''Considerato che nella suddetta comunicazione si dichiara che, a tutela della privata incolumità e in attesa del ripristino delle condizioni di sicurezza e delle necessarie verifiche, l\' impianto è da ritenersi Fuori Servizio;''' )

    par_0_3 = document.add_paragraph()
    par_0_3.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    par_0_3.add_run('''Ritenuto dunque necessario procedere alla emissione di ordinanza di fermo impianto fino alla data di avvenuta verifica\
 straordinaria con esito favorevole, in ottemperanza alle disposizioni previste dal DPR n. 162/99 e s.m.i. e in particolare le disposizioni di cui all'\
 art. 14;''' )
    
    par_0_4 = document.add_paragraph()
    par_0_4.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    par_0_4.add_run('''Visto l\' art 107 del D.Lgs 267/2000;''' )

    ordina = document.add_paragraph()
    ordina.alignment = WD_ALIGN_PARAGRAPH.CENTER
    ordina.add_run('''ORDINA''',style = 'CduStyle')
    
    titolare_impianto = anaprat_per_tipo(pratica.id, ['titolare', 'amministratore']).first() # titolare impianto
    if titolare_impianto is None:
        titolare_impianto = anaprat_per_tipo(pratica.id, 'richiedente').first() # richiedente
    if titolare_impianto is None:
        titolare_impianto = Anaprat.objects.filter(pratica_id=pratica.id).order_by('id').first()
    qual_tit = ' titolare '# TipoSoggetto.objects.get(id=titolare_impianto.tipo_id)
    soggetto=get_object_or_404(Soggetto, id=titolare_impianto.soggetto_id)


    p01_1 = document.add_paragraph()
    p01_1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p01_1.add_run('''a ''' )
    p01_1.add_run( str(soggetto.cognome.upper())).bold=True
    if soggetto.nome:
         p01_1.add_run(' ' + str(soggetto.nome.title())).bold=True
    if soggetto.codice_fiscale:
         p01_1.add_run(' (CF: ' + str(soggetto.codice_fiscale + ')'))
    p01_1.add_run(''' in qualità di gestore dell'impianto ubicato in Carrara ''')
    if str(pratica.street) != '':
        p01_1.add_run(str(pratica.street))
    if str(pratica.housenumber) != '':
        p01_1.add_run(' n. ' + str(pratica.housenumber))
    
    
    p01_1.add_run(''', il FERMO ''' ).bold=True
    p01_1.add_run('''dell\'impianto avente matricola n. ''')

    if matricola:
         p01_1.add_run(str(matricola.numero) + ', ' ).bold=True
    else:
         p01_1.add_run(''' NESSUNA MATRICOLA''').bold=True
    
    if impianto.num_impianto:
         p01_1.add_run('''Codice di fabbricazione ''')
         p01_1.add_run(str(impianto.num_impianto.upper())).bold=True
    else:
         p01_1.add_run('''NESSUN CODICE DI FABBRICAZIONE ''').bold=True

    # ditta manutentrice
    try:
        ditta_manutentrice = anaprat_per_tipo(pratica.id, 'manutentrice').first() # ditta_manutentrice
    
        qual_man = TipoSoggetto.objects.get(id=ditta_manutentrice.tipo_id)
        dm=Soggetto.objects.get(id=ditta_manutentrice.soggetto_id) # dm = ditta_manutentrice
        print('dm',dm.pec)
        if dm :
            p01_1.add_run(''' e manuntenuto da ''')
            p01_1.add_run(str(dm) + ''' fino alla data di avvenuta VERIFICA straordinaria con esito favorevole, ''').bold=True
            p01_1.add_run('''in ottemperanza alle disposizioni previste dal D.P.R. n.162/1999 e s.m.i.,\
    con divieto di porlo in esercizio pena l\'applicazione delle sanzioni previste per legge; ''')
    except:
        dm = None

    dispone = document.add_paragraph()
    dispone.alignment = WD_ALIGN_PARAGRAPH.CENTER
    dispone.add_run('''DISPONE''',style = 'CduStyle')

    p02 = document.add_paragraph()
    p02.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p02.add_run('''- ''').bold=True
    p02.add_run('''Sin d\'ora la messa in esercizio dell'ascensore, a seguito dell'avvenuta comunicazione del verbale di Verifica Straordinaria con esito favorevole\
 in ottemperanza alle disposizioni del D.P.R. n. 162/1999;''')
    
    p02_1 = document.add_paragraph()
    p02_1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p02_1.add_run('''- ''').bold=True
    p02_1.add_run('''La notifica della presente ordinanza a : ''')
    p02_1.add_run(str(soggetto)+''' in qualità di ''')
    p02_1.add_run(str(qual_tit)) # qualità del titolare dell'impianto
    p02_1.add_run(''' di impianto ubicato in Carrara ''' +  str(pratica.street) + ''', ''' + str(pratica.housenumber))
    p02_1.add_run(''' da effettuarsi a mezzo ''')

    if soggetto.pec != '':
         p02_1.add_run(''' Posta Elettronica Certificata all\'indirizzo  ''' + str(soggetto.pec)).bold=True
    else:
        if soggetto.addr_sede :
            p02_1.add_run(''' Raccomandata A.R. all'indirizzo  '''  + str(soggetto.addr_sede)+' - ' + str(soggetto.comune_residenza)).bold=True
        else:
            if soggetto.addr:
                p02_1.add_run(''' Raccomandata A.R. all'indirizzo  '''+ str(soggetto.addr) + ' - ' + str(soggetto.comune_residenza)).bold=True
            else:
                p02_1.add_run(''' MANCA INDIRIZZO ''')

    p03_1 = document.add_paragraph()
    p03_1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p03_1.add_run('''- ''').bold=True
    p03_1.add_run('''e l\'invio della stessa : ''')

    p03_2 = document.add_paragraph()
    p03_2.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p03_2.paragraph_format.left_indent = Inches(0.5)

    p03_2.add_run('''- ''').bold=True
    p03_2.add_run('''al locale Comando di Polizia Municipale, al quale è fatto obbligo di sorvegliare e\
 verificare l\'osservanza delle disposizioni del presente atto e di dar corso agli adempimenti di propria competenza;''')
    
    if dm:
        p03_3 = document.add_paragraph()
        p03_3.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p03_3.add_run('''- ''').bold=True
        p03_3.add_run('''alla ditta ''')
        p03_3.add_run(str(dm)+''' in qualità di ''')
        p03_3.add_run(str(qual_man)) # qualità del titolare dell'impianto
        p03_3.add_run(''' - ''')

        if dm.pec:
            print('pec',soggetto.pec)
            p03_3.add_run(''' Posta Elettronica Certificata all\'indirizzo  ''' + str(dm.pec)).bold=True
        else:
            if soggetto.addr_sede :
                p03_3.add_run(''' Raccomandata A.R. all'indirizzo  '''  + str(dm.addr_sede)+' - ' + str(dm.comune_residenza)).bold=True
            else:
                if soggetto.addr:
                    p03_3.add_run(''' Raccomandata A.R. all'indirizzo  '''+ str(dm.addr) + ' - ' + str(dm.comune_residenza)).bold=True
                else:
                    p03_3.add_run(''' MANCA INDIRIZZO ''')

    avverte = document.add_paragraph()
    avverte.alignment = WD_ALIGN_PARAGRAPH.CENTER
    avverte.add_run('''AVVERTE''',style = 'CduStyle')

    p02 = document.add_paragraph()
    p02.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p02.add_run('''- ''').bold=True
    p02.add_run('''che contro il presente provvedimento è ammesso ricorso giurisdizionale avanti al\
 T.A.R. per la Toscana -  Sede di Firenze, da notificarsi a questo Comune ed a eventuali controinteressati,\
 nel termine di 60 giorni dalla data di notificazione del presente provvedimento e da depositarsi presso la Segreteria del Tribunale\
 medesimo entro i successivi 30 giorni con l'atto impugnato e la prova dell\'avvenuta notifica, ai sensi dell\'art. 21 della Legge n. 1034/1971;''')
        
    p03 = document.add_paragraph()
    p03.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p03.add_run('''- ''').bold=True
    
    p03.add_run('''che è ammesso, in alternativa, ricorso straordinario al Presidente della Repubblica entro 120 giorni\
 dalla data della notifica di questo provvedimento, ai sensi e nei modi di cui agli artt. 8 e 9 del D.P.R. n. 1199/1971.''')
    
    par_8_3 = document.add_paragraph()
    par_8_3.paragraph_format.first_line_indent = Inches(0.3)
    par_8_3.paragraph_format.space_before = Pt(1)
    par_8_3.paragraph_format.space_after = Pt(1)
    par_8_3.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
    par_8_3.add_run('Carrara, data della sottoscrizione digitale' )

    par_8_4 = document.add_paragraph()
    par_8_4.paragraph_format.space_before = Pt(1)
    par_8_4.paragraph_format.space_after = Pt(1)
    par_8_4.alignement = WD_ALIGN_PARAGRAPH.CENTER
    par_8_4.paragraph_format.first_line_indent = Inches(4.2)
    par_8_4.add_run('Il Dirigente' )

    par_8_5 = document.add_paragraph()
    par_8_5.paragraph_format.space_before = Pt(1)
    par_8_5.paragraph_format.space_after = Pt(1)
    par_8_5.alignement = WD_ALIGN_PARAGRAPH.CENTER
    par_8_5.paragraph_format.first_line_indent = Inches(4.2)
    par_8_5.add_run('Ing. Luca Amadei' )


    p09 = document.add_paragraph()
    p09.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p09.paragraph_format.space_before = Pt(10)
    p09.add_run('Documento firmato digitalmente ai sensi e per gli effetti di cui agli artt.21, 23, 23bis e 23ter del D.LGS. 82 del 7 marzo 2005 e s.m.i. - Codice dell\'Amministrazione Digitale', style='NormalStyle').italic=True



    


#     

    

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




#######################################################################
### ORDINANZA A SEGUITO DI VERIFICA CON ESITO NEGATIVO ################


def CreateOrdinanzaVerificaNegativa(request,id):
    pratica = Pratica.objects.get(id=id)
    try:
        impianto = Impianto.objects.get(pratica_id=pratica.id) # impianto da produrre
    except:
        impianto = ''
    try:
        matricola = Matricola.objects.get(num_impianto_id=impianto.id)
    except:
        matricola = ''
    print(impianto, matricola)
    
    atto = str(pratica.tipo_pratica)+'_'+'ordinanza'+'_'+str(pratica.prot_gen) +'_'+str(pratica.data_prot_gen.year)+'.docx'
    
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
    f1.add_run(" PEC : comune.carrara@postecert.it", style = 'FooterStyle')

    f2=footer.add_paragraph()
    f2.paragraph_format.space_after = Pt(0)
    f2.paragraph_format.space_before = Pt(0)
    f2.add_run("geom. Carlo Alberto Nicolini - 0585 641252 - carloalberto.nicolini@comune.carrara.ms.it", style = 'FooterStyle')

    #   IMPOSTA IL FOOTER
    
    
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
    p0_1.add_run('Settore 6 - Governo del territorio', style = 'SottoHeaderStyle').bold = True

    p0_1_1 = document.add_paragraph()
    p0_1_1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p0_1_1.add_run('Servizio 6.1 - Urbanistica e edilizia privata - U.O. 6.1.1 Pianificazione urbanistica', style = 'SottoHeaderStyle')
    # p0_1.add_run(str(impianto.impianto_number)+ ' del ' +"%s" % impianto.impianto_date.strftime('%Y'), style='CduStyle').bold=True
         
    paragraph_format = paragraph.paragraph_format
    paragraph_format.alignment = 1 # 1 - allineato centrato 0 - allineato a sx
    p0_2 = document.add_paragraph()
    p0_2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p0_2.bold=True
    p0_2.add_run('', style = 'NormalStyle').bold = True
    
    try:
        matricola = Matricola.objects.get(num_impianto_id=impianto.id)
    except:
        matricola = ''
    # print('matricola',matricola)
    impianto = Impianto.objects.get(pratica_id=id)
    # print('impianto',impianto)
    pratica = Pratica.objects.get(id=impianto.pratica_id)
    print('pratica',pratica)
########        DEFINISCE I DATI CORRENTI PER IMPIANTO E MATRICOLA
    # impianto = Impianto.object.get(id=id)
    # matricola = Matricola.objects.get
 # # recupera TUTTI i richiedenti
            
    all_rich = Anaprat.objects.filter(pratica_id=pratica.id)
    print('richiedenti', all_rich)
    for a in all_rich:
                soggetto=Soggetto.objects.get(id=a.soggetto_id)
               
                    
    


    
    # ESTRAE le particelle interessate e le elenca
    particelle = Cataprat.objects.filter(pratica_id=impianto.pratica_id) 
    tot_particelle = particelle.count()
    print('to',tot_particelle)
    pratica = Pratica.objects.get(id=impianto.pratica_id) # recupera i dati della pratica
    # recupera il primo richiedente
    rich = anaprat_per_tipo(impianto.pratica_id, 'richiedente').first() or Anaprat.objects.filter(pratica_id=impianto.pratica_id).order_by('tipo_id').first()
    # (Q(pratica_id=pratica.id)&
    #                                          Q(matricola_date__icontains=year))
    print(rich)
    print('richiedenti', rich)
    soggetto = Soggetto.objects.get(id=rich.soggetto_id)

    if soggetto.comune_nascita:
        # verifico se maschio o femmina 
        
        if soggetto.codice_fiscale !='':
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
    else:
        pass
    #document.add_paragraph(lista)
    par_0 = document.add_paragraph()
    par_0.alignment = WD_ALIGN_PARAGRAPH.CENTER
    par_0.paragraph_format.space_after = Pt(0)
    par_0.bold=True
    par_0.add_run('ORDINANZA FERMO IMPIANTO', style = 'CduStyle')
    
    par_0_0_1 = document.add_paragraph()
    par_0_0_1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    par_0_0_1.paragraph_format.space_after = Pt(6)
    par_0_0_1.add_run( '(ai sensi dell\'art. 13 e segg. del DPR 162/99)', style = 'NumCduStyle')
    

    par_0_1 = document.add_paragraph()
    par_0_1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    par_0_1.bold=True
    par_0_1.add_run('Il Dirigente del Settore', style = 'HeaderStyle').bold = True

    ###################################### ditta verifiche periodiche
    ditta_visite_periodiche = anaprat_per_tipo(pratica.id, 'verifiche_periodiche').first() # ditta verifiche periodiche
    dvp=get_object_or_404(Soggetto, id=ditta_visite_periodiche.soggetto_id)

    ################### IMPIANTO
    try:
        impianto = Impianto.objects.get(pratica_id=pratica.id)
    except:
        None
    print(dvp,dvp.comune_residenza,'pratica',pratica.id, dvp.id)

    par_0_0_1 = document.add_paragraph()
    # par_0_0_1.paragraph_format.first_line_indent = Inches(0.5)
    par_0_0_1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    par_0_0_1.add_run('''Visto l\' art. 13 comma 3 del DPR n. 162/99 il quale dispone che il soggetto che esegue la verifica periodica rilascia \
al proprietario, nonchè alla ditta incaricata della manutenzione, il verbale relativo e ove negativo, ne comunica l\'esito \
al competente ufficio comunale per i provvedimenti di competenza ;''')


    par_0_1 = document.add_paragraph()
    # par_0_1.paragraph_format.first_line_indent = Inches(0.5)
    par_0_1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    par_0_1.add_run('''Vista la ''')
    if pratica.oggetto:
         par_0_1.add_run(str(pratica.oggetto))
    par_0_1.add_run(''', prodotto dalla ditta ''' + str(dvp.cognome.upper()))
    if dvp.comune_residenza:
        par_0_1.add_run(' con sede in ' + str(dvp.comune_residenza))
    if dvp.addr_sede :
        par_0_1.add_run(' ' + str(dvp.addr_sede))
    par_0_1.add_run(''' e registrato con prot.gen. n. ''' + str(pratica.prot_gen) + ''' del ''' + "%s" % data.strftime('%d/%m/%Y')) 
    par_0_1.add_run(''', relativo all\'impianto ''')
    
    par_0_1.add_run('''in essere presso l\'edificio posto in ''' )
    par_0_1.add_run( str(pratica.street) + ''' ''' + pratica.housenumber + ''', distinta in catasto al ''') 
    par_0_1.add_run(lista)
    par_0_1.add_run(''';''')

    #### dati ascensore
    
    if impianto.num_impianto :
        par_0_1_1 = document.add_paragraph(style='List Bullet')
        par_0_1_1.paragraph_format.first_line_indent = Inches(0.5)
        par_0_1_1.alignment = WD_ALIGN_PARAGRAPH.LEFT
        par_0_1_1.add_run( 'codice : ' + str(impianto.num_impianto))
    
    # matricola
    matricola = Matricola.objects.get(num_impianto_id = impianto.id)
    if matricola.matricola_assegnata:
        par_0_1_2 = document.add_paragraph(style='List Bullet')
        par_0_1_2.paragraph_format.first_line_indent = Inches(0.5)
        par_0_1_2.alignment = WD_ALIGN_PARAGRAPH.LEFT
        par_0_1_2.add_run('matricola : ' + str(matricola.matricola_assegnata))


    par_0_2 = document.add_paragraph()
    par_0_2.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    par_0_2.add_run('''Visto l\' art. 14 comma 1 del DPR n. 162/99 il quale dispone che a seguito di verbale di verifica periodica con esito negativo, \
il competente ufficio comunale dispone il fermo dell'impianto fino alla data della verifica straordinaria con esito favorevole; ''' )

    par_0_3 = document.add_paragraph()
    par_0_3.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    par_0_3.add_run('''Ritenuto dunque necessario procedere alla emissione di ordinanza di fermo impianto fino alla data di avvenuta verifica\
 straordinaria con esito favorevole, in ottemperanza alle disposizioni previste dal DPR n. 162/99 e s.m.i. e in particolare le disposizioni di cui all'\
 art. 14;''' )
    
    par_0_4 = document.add_paragraph()
    par_0_4.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    par_0_4.add_run('''Visto l\' art 107 del D.Lgs 267/2000;''' )

    ordina = document.add_paragraph()
    ordina.alignment = WD_ALIGN_PARAGRAPH.CENTER
    ordina.add_run('''ORDINA''',style = 'CduStyle')
    
    titolare_impianto = anaprat_per_tipo(pratica.id, ['titolare', 'amministratore']).first() # titolare impianto
    if titolare_impianto is None:
        titolare_impianto = anaprat_per_tipo(pratica.id, 'richiedente').first() # richiedente
    if titolare_impianto is None:
        titolare_impianto = Anaprat.objects.filter(pratica_id=pratica.id).order_by('id').first()
    qual_tit = ' titolare '# TipoSoggetto.objects.get(id=titolare_impianto.tipo_id)
    soggetto=get_object_or_404(Soggetto, id=titolare_impianto.soggetto_id)


    p01_1 = document.add_paragraph()
    p01_1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p01_1.add_run('''a ''' )
    p01_1.add_run( str(soggetto.cognome.upper())).bold=True
    if soggetto.nome:
         p01_1.add_run(' ' + str(soggetto.nome.title())).bold=True
    if soggetto.codice_fiscale:
         p01_1.add_run(' (CF: ' + str(soggetto.codice_fiscale + ')'))
    p01_1.add_run(''' in qualità di gestore dell'impianto ubicato in Carrara ''')
    if str(pratica.street) != '':
        p01_1.add_run(str(pratica.street))
    if str(pratica.housenumber) != '':
        p01_1.add_run(' n. ' + str(pratica.housenumber))
    
    
    p01_1.add_run(''', il FERMO ''' ).bold=True
    p01_1.add_run('''dell\'impianto avente matricola n. ''')

    if matricola:
         p01_1.add_run(str(matricola.matricola_assegnata) + ', ' ).bold=True
    else:
         p01_1.add_run(''' NESSUNA MATRICOLA''').bold=True
    
    if impianto.num_impianto:
         p01_1.add_run('''Codice di fabbricazione ''')
         p01_1.add_run(str(impianto.num_impianto.upper())).bold=True
    else:
         p01_1.add_run('''NESSUN CODICE DI FABBRICAZIONE ''').bold=True

    # ditta manutentrice
    try:
        ditta_manutentrice = anaprat_per_tipo(pratica.id, 'manutentrice').first() # ditta_manutentrice
    
        qual_man = TipoSoggetto.objects.get(id=ditta_manutentrice.tipo_id)
        dm=Soggetto.objects.get(id=ditta_manutentrice.soggetto_id) # dm = ditta_manutentrice
        print('dm',dm.pec)
        if dm :
            p01_1.add_run(''' e manuntenuto da ''')
            p01_1.add_run(str(dm) + ''' fino alla data di avvenuta VERIFICA straordinaria con esito favorevole, ''').bold=True
            p01_1.add_run('''in ottemperanza alle disposizioni previste dal D.P.R. n.162/1999 e s.m.i.,\
    con divieto di porlo in esercizio pena l\'applicazione delle sanzioni previste per legge; ''')
    except:
        dm = None

    dispone = document.add_paragraph()
    dispone.alignment = WD_ALIGN_PARAGRAPH.CENTER
    dispone.add_run('''DISPONE''',style = 'CduStyle')

    p02 = document.add_paragraph()
    p02.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p02.add_run('''- ''').bold=True
    p02.add_run('''Che la presente ordinanza mantenga efficacia fino all'acquisizione agli atti del Comune :''')
    
    p02_0 = document.add_paragraph(style='List Bullet')
    p02_0.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p02_0.add_run('''del verbale di verifica straordinaria, ''')
    p02_0.add_run('''con esito positivo ''').bold=True
    p02_0.add_run(''', redatto dal soggetto incaricato delle verifiche periodiche;''')

    p02_0_1 = document.add_paragraph(style='List Bullet')
    p02_0_1.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p02_0_1.add_run('''della dichiarazione di messa in pristino da parte del soggetto incaricato della manutenzione. ''')
    # p02_0_1.add_run('''con esito positivo ''').bold=True
    # p02_0_1.add_run(''', redatto dal soggetto incaricato delle verifiche periodiche;''')


    
    p02_1 = document.add_paragraph()
    p02_1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p02_1.add_run('''- ''').bold=True
    p02_1.add_run('''La notifica della presente ordinanza a : ''')
    p02_1.add_run(str(soggetto.cognome.upper()))
    if soggetto.nome :
         p02_1.add_run(' ' +str(soggetto.nome.upper()))
    p02_1.add_run(''' in qualità di ''')
    p02_1.add_run(str(qual_tit)) # qualità del titolare dell'impianto
    p02_1.add_run(''' di impianto ubicato in Carrara ''' +  str(pratica.street) + ''', ''' + str(pratica.housenumber))
    p02_1.add_run(''' da effettuarsi a mezzo ''')

    if soggetto.pec != '':
         p02_1.add_run(''' Posta Elettronica Certificata all\'indirizzo  ''')
         p02_1.add_run(str(soggetto.pec)).bold=True
    elif soggetto.email != '':
         p02_1.add_run(''' Posta Elettronica all\'indirizzo  ''')
         p02_1.add_run(str(soggetto.email)).bold=True
    else:
        if soggetto.addr_sede :
            p02_1.add_run(''' Raccomandata A.R. all'indirizzo  '''  + str(soggetto.addr_sede)+' - ' + str(soggetto.comune_residenza)).bold=True
        else:
            if soggetto.addr:
                p02_1.add_run(''' Raccomandata A.R. all'indirizzo  '''+ str(soggetto.addr) + ' - ' + str(soggetto.comune_residenza)).bold=True
            else:
                p02_1.add_run(''' MANCA INDIRIZZO ''')

    p03_1 = document.add_paragraph()
    p03_1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p03_1.add_run('''- ''').bold=True
    p03_1.add_run('''e l\'invio della stessa : ''')

    p03_2 = document.add_paragraph()
    p03_2.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p03_2.paragraph_format.left_indent = Inches(0.5)

    p03_2.add_run('''- ''').bold=True
    p03_2.add_run('''al locale Comando di Polizia Municipale, al quale è fatto obbligo di sorvegliare e\
 verificare l\'osservanza delle disposizioni del presente atto e di dar corso agli adempimenti di propria competenza;''')
    

    # INVIO A ditta verifiche periodiche e manutenzione
    if dvp:
        p03_2_1 = document.add_paragraph()
        p03_2_1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p03_2_1.paragraph_format.left_indent = Inches(0.5)
        p03_2_1.add_run('''- ''').bold=True
        p03_2_1.add_run('''alla ditta ''')
        p03_2_1.add_run(str(dvp)+''' in qualità di Ditta incaricata per le visite periodiche''')
        # p03_2_1.add_run(str(qual_man)) # qualità della ditta di manutenzione dell'impianto
        p03_2_1.add_run(''' - ''')

        if dvp.pec:
            print('pec',soggetto.pec)
            p03_2_1.add_run(''' Posta Elettronica Certificata all\'indirizzo  ''' )
            p03_2_1.add_run(str(dvp.pec)).bold=True
        else:
            if soggetto.addr_sede :
                p03_2_1.add_run(''' Raccomandata A.R. all'indirizzo  '''  + str(dvp.addr_sede)+' - ' + str(dvp.comune_residenza)).bold=True
            else:
                if soggetto.addr:
                    p03_2_1.add_run(''' Raccomandata A.R. all'indirizzo  '''+ str(dvp.addr) + ' - ' + str(dvp.comune_residenza)).bold=True
                else:
                    p03_2_1.add_run(''' MANCA INDIRIZZO ''')
    
    if dm:
        p03_3 = document.add_paragraph()
        p03_3.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p03_3.paragraph_format.left_indent = Inches(0.5)
        p03_3.add_run('''- ''').bold=True
        p03_3.add_run('''alla ditta ''')
        p03_3.add_run(str(dm)+''' in qualità di Ditta incaricata per la manutenzione''')
        # p03_3.add_run(str(qual_man)) # qualità della ditta di manutenzione dell'impianto
        p03_3.add_run(''' - ''')

        if dm.pec:
            print('pec',soggetto.pec)
            p03_3.add_run(''' Posta Elettronica Certificata all\'indirizzo  ''')
            p03_3.add_run(str(dm.pec)).bold=True
        else:
            if soggetto.addr_sede :
                p03_3.add_run(''' Raccomandata A.R. all'indirizzo  '''  + str(dm.addr_sede)+' - ' + str(dm.comune_residenza)).bold=True
            else:
                if soggetto.addr:
                    p03_3.add_run(''' Raccomandata A.R. all'indirizzo  '''+ str(dm.addr) + ' - ' + str(dm.comune_residenza)).bold=True
                else:
                    p03_3.add_run(''' MANCA INDIRIZZO ''')

    avverte = document.add_paragraph()
    avverte.alignment = WD_ALIGN_PARAGRAPH.CENTER
    avverte.add_run('''AVVERTE''',style = 'CduStyle')

    p02 = document.add_paragraph()
    p02.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p02.add_run('''- ''').bold=True
    p02.add_run('''che contro il presente provvedimento è ammesso ricorso giurisdizionale avanti al\
 T.A.R. per la Toscana -  Sede di Firenze, da notificarsi a questo Comune ed a eventuali controinteressati,\
 nel termine di 60 giorni dalla data di notificazione del presente provvedimento e da depositarsi presso la Segreteria del Tribunale\
 medesimo entro i successivi 30 giorni con l'atto impugnato e la prova dell\'avvenuta notifica, ai sensi dell\'art. 21 della Legge n. 1034/1971;''')
        
    p03 = document.add_paragraph()
    p03.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p03.add_run('''- ''').bold=True
    
    p03.add_run('''che è ammesso, in alternativa, ricorso straordinario al Presidente della Repubblica entro 120 giorni\
 dalla data della notifica di questo provvedimento, ai sensi e nei modi di cui agli artt. 8 e 9 del D.P.R. n. 1199/1971.''')
    
    par_8_3 = document.add_paragraph()
    par_8_3.paragraph_format.first_line_indent = Inches(0.3)
    par_8_3.paragraph_format.space_before = Pt(1)
    par_8_3.paragraph_format.space_after = Pt(1)
    par_8_3.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
    par_8_3.add_run('Carrara, data della sottoscrizione digitale' )

    par_8_4 = document.add_paragraph()
    par_8_4.paragraph_format.space_before = Pt(1)
    par_8_4.paragraph_format.space_after = Pt(1)
    par_8_4.alignement = WD_ALIGN_PARAGRAPH.CENTER
    par_8_4.paragraph_format.first_line_indent = Inches(4.2)
    par_8_4.add_run('Il Dirigente' )

    par_8_5 = document.add_paragraph()
    par_8_5.paragraph_format.space_before = Pt(1)
    par_8_5.paragraph_format.space_after = Pt(1)
    par_8_5.alignement = WD_ALIGN_PARAGRAPH.CENTER
    par_8_5.paragraph_format.first_line_indent = Inches(4.2)
    par_8_5.add_run('Ing. Luca Amadei' )


    p09 = document.add_paragraph()
    p09.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p09.paragraph_format.space_before = Pt(10)
    p09.add_run('Documento firmato digitalmente ai sensi e per gli effetti di cui agli artt.21, 23, 23bis e 23ter del D.LGS. 82 del 7 marzo 2005 e s.m.i. - Codice dell\'Amministrazione Digitale', style='NormalStyle').italic=True

    


#     

    

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


#######################################################################