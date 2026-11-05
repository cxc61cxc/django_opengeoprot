from django.shortcuts import render
# from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from protocollo.models import Pratica, Cataprat, Anaprat, Soggetto, Particella
from coop.models import *
from paesaggio.models import *
from prg.models import *

from datetime import datetime

### GESTIONE ELENCO MODELLI PER TIPOLOGIA DI PRATICA ### sotto ci sono i modelli già fatti a mo' di esempio

from django.views import View
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .models import *
from protocollo.models import TipoPratica
from django.urls import resolve
from decimal import Decimal


### from
### https://towardsdatascience.com/build-a-django-crud-app-by-using-class-based-views-12bc69d36ab6
class ModelloBaseView(View):
    model = Modello
    fields = '__all__'
    success_url = reverse_lazy('comunicazioni:all')

class ModelloListView(ModelloBaseView, ListView):
    """View to list all modello.
    Use the 'modello_list' variable in the template
    to access all Modello objects"""

class ModelloDetailView(ModelloBaseView, DetailView):
    """View to list the details from one modello.
    Use the 'modello' variable in the template to access
    the specific modello here and in the Views below"""

class ModelloCreateView(ModelloBaseView, CreateView):
    """View to create a new modello"""

class ModelloUpdateView(ModelloBaseView, UpdateView):
    """View to update a modello"""

class ModelloDeleteView(ModelloBaseView, DeleteView):
    """View to delete a modello"""




# from .forms import TaskForm
# Create your views here.


def List(request):
    modelli = Modello.objects.all().order_by('id')
    # app     = request.resolver_match.comunicazioni
    # models  = apps.get_app_config(app).get_models()
    # names   = [model._meta.model.__name__ for model in models]
    # context = {
    #      "names" : names,
    #  }
    # return render(request, app + '/comunic_list.html', context)
    context ={
          'modelli' : modelli,
        }
    return render(request,'comunicazioni/comunic_list.html', context)

###################################################################################


from django.http import HttpResponse
from docx.enum.table import WD_ALIGN_VERTICAL
from docx import Document
from docx import *
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_UNDERLINE
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.section import WD_ORIENT
from docx.shared import Pt, Inches, Mm
from docx.oxml import parse_xml
from docx.oxml.ns import qn
from xml.sax.saxutils import escape
import os
import math
from PIL import Image, ImageDraw, ImageFont
from collections import OrderedDict
import numpy as np
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404

# import pandas as pd
from itertools import groupby
from io import BytesIO



    #### Parere preventivo Paesaggistica

def ParerePreventivoPaesaggio(request, pk=None):
    if pk is None:
        pk = request.session.get('pk')
    id = pk
    print('id',id)
    if not id:
        return HttpResponse('Problema: nessuna pratica selezionata (sessione pk mancante).')
    try:
        pratica = Pratica.objects.get(id=id)
    except Pratica.DoesNotExist:
        return HttpResponse(f'Problema: pratica con id {id} non trovata.')
    print (pratica)
    print('tipo di pratica',pratica.tipo_pratica)

    # verifico che siano presenti commissioni
    commissioni = Commissione.objects.filter(pratica_id=id)
    if commissioni.count() == 0 :
            print('commissioni',commissioni)
            return redirect('protocollo:pratica_detail_url', pk=id)
    print('ci sono',commissioni.count(),'commissioni')
    if pratica.tipo_pratica_id == 13 : # impostare l'ID corretto del Modello
            atto = 'parere_prev_' +str(pratica.tipo_pratica) +  str(pratica.prot_gen) +'_' + "%s" % pratica.data_prot_gen.strftime('%y_%m_%d') +'.docx'
            print('atto',atto)
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
            f1.add_run("Settore 7 - Governo del territorio / Servizio 7.6 - U.O.  Tutela del Paesaggio - P.za due giugno,1 54033 - Carrara (MS)", style = 'FooterStyle')

            f2=footer.add_paragraph()
            f2.paragraph_format.space_after = Pt(0)
            f2.paragraph_format.space_before = Pt(0)
            f2.add_run("geom. Marco Storti - 0585 641235 - marco.storti@comune.carrara.ms.it", style = 'FooterStyle')

            # f3=footer.add_paragraph()
            # f3.paragraph_format.space_after = Pt(0)
            # f3.paragraph_format.space_before = Pt(0)
            # f3.add_run("geom. Carlo Alberto Nicolini - 0585 641252 - carloalberto.nicolini@comune.carrara.ms.it", style = 'FooterStyle')

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
            obj_font.size = Pt(11)
            obj_font.name = 'Arial'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('HeaderStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(9)
            obj_font.name = 'Arial'

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
            obj_charstyle = obj_styles.add_style('NumCduStyleItalic', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = True
            obj_font.size = Pt(9)
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
            p0.add_run('Settore 7 - GOVERNO DEL TERRITORIO',style = 'HeaderStyle')




        # #    stampo i dati della U.O.

            p1 = document.add_paragraph()
            p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p1.add_run('Servizio 7.6- U.O.  Tutela del Paesaggio',style = 'DprStyle')




            # recupera i dati della pratica
            pratica = Pratica.objects.get(id=pratica.id)



            # # recupera TUTTI i richiedenti

            all_rich = Anaprat.objects.filter(pratica_id=pratica.id)
            print('richiedenti', all_rich)
            for a in all_rich:
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
                        prot = pratica.prot_gen
                        data = pratica.data_prot_gen


                    #inserisce il nominativo
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

            # ESTRAE le particelle interessate e le conta
            particelle = Cataprat.objects.filter(pratica_id=pratica.id)
            tot_particelle = particelle.count()

            print('to',tot_particelle)


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
            else:
                    prot = pratica.prot_gen
                    data = pratica.data_prot_gen

            ####################################
            #      OGGETTO
            ###################################
            istanza = 'Istanza di autorizzazione paesaggistica art. 146 D.lgs. 42/’04 con '
            oggetto_lettera = pratica.oggetto

            if pratica.street :

                ubicazione = ', su immobile ubicato in Carrara '
                oggetto_lettera = oggetto_lettera + ubicazione + str(pratica.street).title() + ' ' + pratica.housenumber



            p2_4 = document.add_paragraph()
            p2_4.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p2_4.paragraph_format.space_after = Pt(0)
            p2_4.paragraph_format.space_before = Pt(30)

            p2_4.add_run(str('Oggetto : ') , style='HeaderStyle').bold=True
            p2_4.add_run(str(istanza ), style='HeaderStyle')
            p2_4.add_run(str('procedura semplificata ') , style='HeaderStyle').bold=True
            p2_4.add_run(str('ai sensi  D.P.R. n° 31 del 13/02/2017 – ') , style='HeaderStyle')
            p2_4.add_run(str('Proposta di provvedimento') , style='HeaderStyle').bold=True

            # p2_4_1 = document.add_paragraph()
            # p2_4_1.alignment = WD_ALIGN_PARAGRAPH.LEFT


            # # p2_4_1 = document.add_paragraph()
            # # p2_4_1.alignment = WD_ALIGN_PARAGRAPH.LEFT
            # p2_4_1.paragraph_format.space_after = Pt(2)
            # p2_4_1.add_run(str(oggetto_lettera ), style='HeaderStyle')

            # if lista:
            #     p2_4_1.add_run(', distinto in catasto al ', style='HeaderStyle')
            #     p2_4_1.add_run(lista, style='HeaderStyle')
            # else:
            #     pass


            p2_4_2 = document.add_paragraph()
            p2_4_2.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p2_4_2.paragraph_format.space_after = Pt(1)
            p2_4_2.add_run(str('Estremi del vincolo ricorrente: '), style='HeaderStyle').bold=True


            p2_4_3 = document.add_paragraph()
            p2_4_3.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p2_4_3.add_run(str('D.M. 03/02/1969 - Marina di Carrara - Art. 136 lett. c)  + art. 142 lett. a) D.lgs. 42/04.'), style='HeaderStyle').bold=True
            ####################################
            #      DITTA
            ###################################
            # recupera il primo richiedente (Q(status='on-sale') | Q(status='paused'))
            rich = Anaprat.objects.filter(Q(pratica_id=pratica.id) & Q(tipo_id=1)).order_by('id')[0]
            print('richiedenti', rich)
            soggetto = Soggetto.objects.get(id=rich.soggetto_id)
            # verifico che esista il codice fiscale
            if soggetto.codice_fiscale:
                # verifico se maschio o femmina
                sesso_cf = soggetto.codice_fiscale[6:8]
                if int(sesso_cf)>40:
                    nascita =' nata a ' + soggetto.comune_nascita.title() + ' il ' + str(soggetto.data_nascita)
                else:
                    nascita =' nato a ' + soggetto.comune_nascita.title() + ' il ' + str(soggetto.data_nascita)
                    print('sesso_cf', sesso_cf)
            prot = pratica.prot_gen
            data = pratica.data_prot_gen

            p001 = document.add_paragraph()
            p001.paragraph_format.left_indent = Inches(0.5)
            p001_text = str.title(soggetto.cognome) + ' ' + str.title(soggetto.nome)
            p001.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p001.paragraph_format.space_after = Pt(4)
            p001.add_run(str('DITTA : ' + p001_text ) , style='NumCduStyleItalic')
            ####################################
            #      RICHIEDENTE
            ###################################
            p002 = document.add_paragraph()
            p002.paragraph_format.left_indent = Inches(0.5)

            p002_text = str.upper(soggetto.cognome) + ' ' + str.title(soggetto.nome)
            p002.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p002.paragraph_format.space_after = Pt(12)
            p002.add_run(str('Rif. Pratica: Prot. Gen. ' + str(pratica.prot_gen + ' del ' + "%s" % pratica.data_prot_gen.strftime('%d') +'/'+ "%s" % pratica.data_prot_gen.strftime('%m')+'/'+"%s" % pratica.data_prot_gen.strftime('%Y')) ) , style='NumCduStyleItalic')

            ####################################
            #      PARAGRAFO NormalStyle
            ###################################

            par_1 = document.add_paragraph()
            par_1.paragraph_format.first_line_indent = Inches(0.3)
            # par_1 = paragraph_format.left_indent = Inches(0.5)
            par_1.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_1.paragraph_format.space_before = Pt(1)
            par_1.paragraph_format.space_after = Pt(4)
            par_1.add_run()
            par_1.add_run(('Valutata la conformità dell’intervento alle prescrizioni d’uso contenute nel provvedimento di vincolo  da parte della Commissione Comunale per il Paesaggio, istituita ai sensi art. 153 L.R.T. n° 65/’14,  nella seduta  n° ' ), style='NormalStyle')
            # estrae gli estremi della commissione paesaggistica 10 del 29/06/2023  con il seguente parere:'
            num_com = Commissione.objects.filter(pratica_id=pratica.id).values_list('commissione_number',flat=True).order_by('-id')[:1]
            data_com = Commissione.objects.filter(pratica_id=pratica.id).values_list('commissione_date',flat=True).order_by('-id')[:1]

            commissione_id = Commissione.objects.filter(pratica_id=pratica.id).values_list('id',flat=True).order_by('-id')[:1]
            print('id commissione',commissione_id)
            if commissione_id:
                commissione= Commissione.objects.get(id=commissione_id)
                parere = commissione.parere
                #data_com = comm.commissione_date
                print('num_comm',num_com)
                print('data_comm',data_com)

                # par_1_1= document.add_paragraph()
                par_1.add_run(str(num_com[0]), style='NormalStyle').bold=True

                par_1.add_run((' del '), style='NormalStyle' )
                par_1.add_run("%s" % data.strftime('%d/%m/%Y'), style='NormalStyle').bold=True
                par_1.add_run(' con il seguente parere:', style='NormalStyle')
                # parere della commissione
                par_2 = document.add_paragraph()
                par_2.paragraph_format.space_before = Pt(1)
                par_2.paragraph_format.space_after = Pt(4)
                par_2.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
                par_2.add_run(str('"'+parere + '"'), style='NormalStyle' ).italic=True
                par_2.add_run('', style='NormalStyle' )


            par_4_1 = document.add_paragraph()
            par_4_1.paragraph_format.first_line_indent = Inches(0.3)
            par_4_1.paragraph_format.space_before = Pt(1)
            par_4_1.paragraph_format.space_after = Pt(1)
            par_4_1.alignement = WD_ALIGN_PARAGRAPH.LEFT
            par_4_1.add_run('Si comunica che la documentazione tecnica necessaria per l’espressione del parere vincolante di Codesta Soprintendenza è visionabile  all’URL http://servizi.comune.carrara.ms.it/sabap-lucca', style='NormalStyle' )

            par_4_2 = document.add_paragraph()
            par_4_2.paragraph_format.space_before = Pt(1)
            par_4_2.paragraph_format.space_after = Pt(1)
            par_4_2.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_4_2.add_run('Utente:  sabap-lucca', style='NormalStyle' )

            par_4_3 = document.add_paragraph()
            par_4_3.paragraph_format.space_before = Pt(1)
            par_4_3.paragraph_format.space_after = Pt(1)
            par_4_3.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_4_3.add_run('Password:  20C@rr@r@23', style='NormalStyle' )

            par_4_4 = document.add_paragraph()
            par_4_4.paragraph_format.space_before = Pt(1)
            par_4_4.paragraph_format.space_after = Pt(3)
            par_4_4.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_4_4.add_run('Tali credenziali di accesso sono strettamente riservate e non devono essere divulgate a terze persone non interessate dal procedimento.', style='NormalStyle' )


            par_5 = document.add_paragraph()
            par_5.paragraph_format.first_line_indent = Inches(0.3)
            par_5.paragraph_format.space_before = Pt(1)
            par_5.paragraph_format.space_after = Pt(4)
            par_5.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_5.add_run('La documentazione di cui sopra è riferita all’istanza presentata in data ', style='NormalStyle' )
            par_5.add_run("%s" % data.strftime('%d/%m/%Y'), style='NormalStyle').bold=True
            par_5.add_run(' da ', style='NormalStyle' )

            par_5.add_run(str.title(soggetto.cognome) + ' ' + str.title(soggetto.nome), style='NormalStyle' ).bold=True
            par_5.add_run(' con prot. ', style='NormalStyle' )
            par_5.add_run(str(prot), style='NormalStyle' ).bold=True
            par_5.add_run(', relativamente a lavori di: ', style='NormalStyle' )
            par_5.add_run(str(pratica.oggetto), style='NormalStyle' ).bold=True
            par_5.add_run(', riconducibili alle voci "B3-B6" del DPR 31/’17,  inerenti l’immobile sito in ', style='NormalStyle' )
            par_5.add_run(str(pratica.street) + ', '+ str(pratica.housenumber), style='NormalStyle' )
            par_5.add_run(', identificato in catasto al ', style='NormalStyle' )
            par_5.add_run(lista, style='NormalStyle' )



            par_8_2 = document.add_paragraph()
            # par_8_2.paragraph_format.first_line_indent = Inches(0.3)
            par_8_2.paragraph_format.space_before = Pt(1)
            par_8_2.paragraph_format.space_after = Pt(1)
            par_8_2.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_8_2.add_run('Cordiali saluti', style='NormalStyle' )

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
            par_8_4.add_run('Il Dirigente ad interim', style='NormalStyle' )

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

 #### Avvio del procedimento senza sospensione SUAP
########################################################
##### AVVIO PROCEDIMENTO SENZA SOSPENSIONE SUAP ########
########################################################
def SuapAvvioProcNoSosp(request):

        id = request.session.get('pk')
        print('id',id)
        pratica = Pratica.objects.get(id=id) # ritorna  i dati pratica
        print (pratica)
        print('tipo',pratica.tipo_pratica)

        if pratica.tipo_pratica_id == 11 or pratica.tipo_pratica_id == 12 or pratica.tipo_pratica_id == 19 or pratica.tipo_pratica_id == 40: # per insegna o suolo pubblico VERIFICARE GLI ID
            print('insegna')

            atto = 'avvio_proc_' +str(pratica.tipo_pratica) + '_' +  str(pratica.prot_gen) +'_' + "%s" % pratica.data_prot_gen.strftime('%Y%m%d') +'.docx'

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
            f1.add_run("Settore 7 - Governo del territorio / Servizio 7.2 SUAP, demanio e paesaggio - U.O. 7.4 S.U.A.P. - P.za due giugno,1 54033 - Carrara (MS)", style = 'FooterStyle')

            f2=footer.add_paragraph()
            f2.paragraph_format.space_after = Pt(0)
            f2.paragraph_format.space_before = Pt(0)
            f2.add_run("dott.ssa Michela Parisi - 0585 641496 - michela.parisi@comune.carrara.ms.it", style = 'FooterStyle')

            f3=footer.add_paragraph()
            f3.paragraph_format.space_after = Pt(0)
            f3.paragraph_format.space_before = Pt(0)
            f3.add_run("geom. Valerio Vinchesi - 0585 641291 - valerio.vinchesi@comune.carrara.ms.it", style = 'FooterStyle')

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
            obj_font.size = Pt(11)
            obj_font.name = 'Arial'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('HeaderStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(8)
            obj_font.name = 'Arial'

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
            obj_charstyle = obj_styles.add_style('NumCduStyleItalic', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = True
            obj_font.size = Pt(9)
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

            paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW

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
            p0.add_run('Settore 7 - GOVERNO DEL TERRITORIO',style = 'FooterStyle')




        # #    stampo i dati della U.O.

            p1 = document.add_paragraph()
            p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p1.add_run('Servizio 7.2 SUAP, demanio e paesaggio - U.O. 7.4 S.U.A.P.',style = 'FooterStyle')





            # recupera i dati della pratica
            pratica = Pratica.objects.get(id=pratica.id)



            # # recupera TUTTI i richiedenti

            all_rich = Anaprat.objects.filter(pratica_id=pratica.id)
            print('richiedenti', all_rich)
            for a in all_rich:
                soggetto=Soggetto.objects.get(id=a.soggetto_id)



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
                                mappali = 'Foglio ' + part.foglio + ' map ' + part.mappale
                                if p.subalterno !='-':
                                      mappali = mappali + ' sub '+str(p.subalterno)+', '
                            foglio_pre= part.foglio
                            lista.append(mappali)
                    print(lista, foglio_pre, part.foglio)
                    #document.add_paragraph(lista)
            else:
                    prot = pratica.prot_gen
                    data = pratica.data_prot_gen

            ####################################
            #      OGGETTO
            ###################################
            if pratica.tipo_pratica_id == 12:
                preambolo='Comunicazione di avvio del procedimento della pratica \
finalizzata al rilascio di autorizzazione all\' installazione di insegne di esercizio permanenti'

            elif pratica.tipo_pratica_id == 19:
                preambolo='Comunicazione di avvio del procedimento della pratica \
finalizzata al rilascio di autorizzazione alla '
            else:
                preambolo =''

            oggetto_lettera = preambolo
            # oggetto_lettera = pratica.oggetto

            if pratica.street :
                ubicazione = ', su immobile ubicato in Carrara '
                housenumber = pratica.housenumber

                if housenumber :
                    oggetto_lettera = oggetto_lettera +' '+ str(pratica.oggetto) + ubicazione + str(pratica.street) + ' ' + str(pratica.housenumber)
                else:
                                        oggetto_lettera = oggetto_lettera + ubicazione + str(pratica.street).title()




            p2_4 = document.add_paragraph()
            p2_4.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p2_4.paragraph_format.space_before = Pt(30)
            p2_4.add_run(str('Oggetto : ') , style='NumCduStyleItalic').bold=True
            # p2_4 = document.add_paragraph()
            # p2_4.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p2_4.paragraph_format.space_after = Pt(4)
            p2_4.add_run(str(oggetto_lettera ), style='NumCduStyleItalic')
            if lista:
                p2_4.add_run(', distinto in catasto al ', style='NumCduStyleItalic')
                p2_4.add_run(lista, style='NumCduStyleItalic')
            else:
                pass
            ####################################
            #      DITTA
            ###################################
            # recupera il primo richiedente (Q(status='on-sale') | Q(status='paused'))
            rich = Anaprat.objects.filter(Q(pratica_id=pratica.id) & Q(tipo_id=1)).order_by('id')[0]
            print('richiedenti', rich)
            soggetto = Soggetto.objects.get(id=rich.soggetto_id)
            # verifico che esista il codice fiscale
            if soggetto.codice_fiscale:
                # verifico se maschio o femmina
                sesso_cf = soggetto.codice_fiscale[6:8]
                if type(sesso_cf) is int:
                    print('sesso_cf',sesso_cf)
                    if int(sesso_cf)>40:
                        nascita =' nata a ' + soggetto.comune_nascita.title() + ' il ' + str(soggetto.data_nascita)
                    else:
                        nascita =' nato a ' + soggetto.comune_nascita.title() + ' il ' + str(soggetto.data_nascita)
                        print('sesso_cf', sesso_cf)
            prot = pratica.prot_gen
            data = pratica.data_prot_gen

            p001 = document.add_paragraph()
            p001.paragraph_format.left_indent = Inches(0.5)
            p001_text = str.title(soggetto.cognome) + ' ' + str.title(soggetto.nome)
            p001.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p001.paragraph_format.space_after = Pt(4)
            p001.add_run(str('DITTA : ' + p001_text ) , style='NumCduStyleItalic')
            ####################################
            #      RICHIEDENTE
            ###################################
            p002 = document.add_paragraph()
            p002.paragraph_format.left_indent = Inches(0.5)

            p002_text = str.upper(soggetto.cognome) + ' ' + str.title(soggetto.nome)
            p002.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p002.paragraph_format.space_after = Pt(12)
            p002.add_run(str('Rif. Pratica: Prot. Gen. ' + str(pratica.prot_gen + ' del ' + "%s" % pratica.data_prot_gen.strftime('%d') +'/'+ "%s" % pratica.data_prot_gen.strftime('%m')+'/'+"%s" % pratica.data_prot_gen.strftime('%Y')) ) , style='NumCduStyleItalic')

            ####################################
            #      PARAGRAFO NormalStyle
            ###################################

            par_1 = document.add_paragraph()
            par_1.paragraph_format.first_line_indent = Inches(0.3)
            # par_1 = paragraph_format.left_indent = Inches(0.5)
            par_1.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW

            par_1.paragraph_format.space_before = Pt(1)
            par_1.paragraph_format.space_after = Pt(4)
            par_1.add_run()
            par_1.add_run(('Con riferimento alla pratica pervenuta con Prot.Gen. n° ' ), style='NormalStyle')
            par_1.add_run(str(pratica.prot_gen), style='NormalStyle').bold=True
            par_1.add_run((' del '), style='NormalStyle' )
            par_1.add_run("%s" % data.strftime('%d/%m/%Y'), style='NormalStyle').bold=True
            par_1.add_run(''', si comunica ai sensi e per gli effetti degli art. 7, 8 della legge 7 Agosto 1990, \
n° 241 e s.m.i., che questo Ufficio ha dato avvio al procedimento. La pratica è di competenza dello Sportello Unico \
per le Attività Produttive del Comune di Carrara, Piazza 2 Giugno 1, presso il quale codesta società potrà prendere \
visione degli atti.''', style='NormalStyle' )
            RUP = 'dott.ssa Michela Parisi'
            ISTRUTTORE = 'geom. Valerio Vinchesi'
            par_3 = document.add_paragraph()
            par_3.paragraph_format.space_before = Pt(1)
            par_3.paragraph_format.space_after = Pt(1)
            par_3.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_3.add_run('Responsabile del procedimento : ', style='NormalStyle' ).bold=True
            par_3.add_run(str(RUP), style='NormalStyle' ).italic=True
            par_3_1 = document.add_paragraph()
            par_3_1.paragraph_format.space_before = Pt(1)
            par_3_1.paragraph_format.space_after = Pt(4)
            par_3_1.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_3_1.add_run('Istruttore tecnico : ', style='NormalStyle' ).bold=True
            par_3_1.add_run(str(ISTRUTTORE), style='NormalStyle' ).italic=True

            par_4 = document.add_paragraph()
            par_4.paragraph_format.first_line_indent = Inches(0.3)
            par_4.paragraph_format.space_before = Pt(1)
            par_4.paragraph_format.space_after = Pt(1)
            par_4.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_4.add_run('''Il procedimento dovrà concludersi entro 60 giorni dal ricevimento della documentazione.\
 Si informa che la pratica, regolare e completa, sarà inviata agli enti competenti al rilascio dei pareri/atti istruttori di competenza.''', style='NormalStyle' )

            par_4_2 = document.add_paragraph()
            par_4_2.paragraph_format.first_line_indent = Inches(0.3)
            par_4_2.paragraph_format.space_before = Pt(1)
            par_4_2.paragraph_format.space_after = Pt(1)
            par_4_2.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_4_2.add_run('''I termini del procedimento potranno essere sospesi nel caso in cui gli uffici comunali \
o gli enti titolari degli endoprocedimenti richiedano l’integrazione degli atti o dei documenti ai fini istruttori.\
In tal caso i termini del procedimento riprenderanno a decorrere del momento della presentazione della documentazione richiesta. \
Tutte le eventuali documentazioni integrative richieste dagli enti interessati e/o uffici comunali \
dovranno essere presentati tramite questo Sportello.''', style='NormalStyle' )

            # par_4_4 = document.add_paragraph()
            # par_4_4.paragraph_format.space_before = Pt(1)
            # par_4_4.paragraph_format.space_after = Pt(1)
            # par_4_4.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            # par_4_4.add_run('Tutte le eventuali documentazioni integrative richieste dagli enti interessati e/o uffici comunali dovranno essere presentati tramite questo Sportello.', style='NormalStyle' )


            par_5 = document.add_paragraph()
            par_5.paragraph_format.first_line_indent = Inches(0.3)
            par_5.paragraph_format.space_before = Pt(1)
            par_5.paragraph_format.space_after = Pt(4)
            par_5.alignement = WD_ALIGN_PARAGRAPH.LEFT
            par_5.add_run('''Ai sensi di quanto stabilito dall’art. 28 della Legge 9 agosto 2013 n. 98 la Pubblica Amministrazione procedente o, in caso di procedimenti in cui intervengono più amministrazioni, \
quella responsabile del ritardo ed i soggetti privati preposti all\'esercizio di attività amministrative, di cui all’art. 1, comma 1-ter, della legge 7 agosto 1990, n. 241, corrispondono all’interessato, \
a titolo di indennizzo per il mero ritardo, una somma pari a 30 euro per ogni giorno di ritardo, con decorrenza dalla data di scadenza del termine del procedimento,
comunque complessivamente non superiore a 2.000 euro. ''', style='NormalStyle' )

            par_6 = document.add_paragraph()
            par_6.paragraph_format.first_line_indent = Inches(0.3)
            par_6.paragraph_format.space_before = Pt(1)
            par_6.paragraph_format.space_after = Pt(1)
            par_6.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_6.add_run('Al fine di ottenere l’indennizzo, l’istante è tenuto ad azionare il potere sostitutivo previsto ', style='NormalStyle' )
            par_6.add_run('dall’art. 2, comma 9-bis, della legge n. 241 del 1990 nel termine perentorio di ', style='NormalStyle' )
            par_6.add_run('venti giorni dalla scadenza del termine di conclusione del procedimento. ', style='NormalStyle' )

            par_6_1 = document.add_paragraph()
            # par_6_1.paragraph_format.first_line_indent = Inches(0.3)
            par_6_1.paragraph_format.space_before = Pt(1)
            par_6_1.paragraph_format.space_after = Pt(1)
            par_6_1.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_6_1.add_run('Nel caso di procedimenti in cui intervengono più amministrazioni, l’interessato ', style='NormalStyle' )
            par_6_1.add_run('presenta istanza all’amministrazione procedente, che la trasmette tempestivamente ', style='NormalStyle' )
            par_6_1.add_run('al titolare del potere sostitutivo dell’amministrazione responsabile del ritardo.', style='NormalStyle' )

            par_7 = document.add_paragraph()
            par_7.paragraph_format.first_line_indent = Inches(0.3)
            par_7.paragraph_format.space_before = Pt(1)
            par_7.paragraph_format.space_after = Pt(1)
            par_7.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_7.add_run('Nel caso in cui anche il titolare del potere sostitutivo non emani il provvedimento ', style='NormalStyle' )
            par_7.add_run('entro un termine pari alla metà di quello originariamente previsto (30 giorni) o non liquidi ', style='NormalStyle' )
            par_7.add_run('l’indennizzo maturato fino alla data della medesima liquidazione, l’istante può proporre ricorso ', style='NormalStyle' )
            par_7.add_run('ai sensi dell’articolo 117 del codice del processo amministrativo di cui ', style='NormalStyle' )
            par_7.add_run('all’Allegato 1 al D.Lgs. 2 luglio 2010 n. 104, e successive modificazioni, oppure, ricorrendone i presupposti, ', style='NormalStyle' )
            par_7.add_run('dell’articolo 118 dello stesso codice. ', style='NormalStyle' )

            par_7_1 = document.add_paragraph()
            # par_7_1.paragraph_format.first_line_indent = Inches(0.3)
            par_7_1.paragraph_format.space_before = Pt(1)
            par_7_1.paragraph_format.space_after = Pt(1)
            par_7_1.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_7_1.add_run('Il soggetto cui è attribuito il potere sostitutivo è il Segretario Generale del Comune di Carrara.', style='NormalStyle' )

            par_8 = document.add_paragraph()
            # par_8.paragraph_format.first_line_indent = Inches(0.3)
            par_8.paragraph_format.space_before = Pt(1)
            par_8.paragraph_format.space_after = Pt(1)
            par_8.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_8.add_run('Si informa, infine, che, in relazione al procedimento attivato, lo SUAP provvede direttamente alla riscossione \
delle spese e dei diritti istruttori di competenza delle varie amministrazioni coinvolte. \
Questo Sportello si riserva pertanto di comunicare l’importo e le modalità di versamento.', style='NormalStyle' )


            par_8_1 = document.add_paragraph()
            # par_8_1.paragraph_format.first_line_indent = Inches(0.3)
            par_8_1.paragraph_format.space_before = Pt(1)
            par_8_1.paragraph_format.space_after = Pt(1)
            par_8_1.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_8_1.add_run('Per integrazioni e/o comunicazioni relative all’oggetto dell’istanza, la S.V. è pregata di citare il numero di ', style='NormalStyle' )

            par_8_1.add_run(str(pratica.tipo_pratica)+'-', style='NormalStyle' ).bold=True
            par_8_1.add_run(str(pratica.prot_gen)+'-' , style='NormalStyle' ).bold=True
            par_8_1.add_run("%s" % data.strftime('%Y'), style='NormalStyle').bold=True

            par_8_2 = document.add_paragraph()
            # par_8_2.paragraph_format.first_line_indent = Inches(0.3)
            par_8_2.paragraph_format.space_before = Pt(1)
            par_8_2.paragraph_format.space_after = Pt(1)
            par_8_2.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_8_2.add_run('Cordiali saluti', style='NormalStyle' )

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
            par_8_4.add_run('Il Dirigente ad interim', style='NormalStyle' )

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


########################################################
##### AVVIO PROCEDIMENTO CON SOSPENSIONE SUAP ########
########################################################
def SuapAvvioProcSosp(request):

        id = request.session.get('pk')
        print('id',id)
        pratica = Pratica.objects.get(id=id) # ritorna  i dati pratica
        print (pratica)
        print('tipo',pratica.tipo_pratica)

        if pratica.tipo_pratica_id == 11 or pratica.tipo_pratica_id == 12 or pratica.tipo_pratica_id == 19 or pratica.tipo_pratica_id == 40: # per insegna o suolo pubblico VERIFICARE GLI ID

            atto = 'avvio_proc_sospensione_' +str(pratica.tipo_pratica) + '_' +  str(pratica.prot_gen) +'_' + "%s" % pratica.data_prot_gen.strftime('%Y%m%d') +'.docx'

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
            f1.add_run("Settore 7 - Governo del territorio / Servizio 7.2 SUAP, demanio e paesaggio - U.O. 7.4 S.U.A.P. - P.za due giugno,1 54033 - Carrara (MS)", style = 'FooterStyle')

            f2=footer.add_paragraph()
            f2.paragraph_format.space_after = Pt(0)
            f2.paragraph_format.space_before = Pt(0)
            f2.add_run("dott.ssa Michela Parisi - 0585 641496 - michela.parisi@comune.carrara.ms.it", style = 'FooterStyle')

            f3=footer.add_paragraph()
            f3.paragraph_format.space_after = Pt(0)
            f3.paragraph_format.space_before = Pt(0)
            f3.add_run("geom. Valerio Vinchesi - 0585 641291 - valerio.vinchesi@comune.carrara.ms.it", style = 'FooterStyle')

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
            obj_font.size = Pt(11)
            obj_font.name = 'Arial'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('HeaderStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(8)
            obj_font.name = 'Arial'

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
            obj_charstyle = obj_styles.add_style('NumCduStyleItalic', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = True
            obj_font.size = Pt(9)
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

            paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW

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
            p0.add_run('Settore 7 - GOVERNO DEL TERRITORIO',style = 'FooterStyle')




        # #    stampo i dati della U.O.

            p1 = document.add_paragraph()
            p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p1.add_run('Servizio 7.2 SUAP, demanio e paesaggio - U.O. 7.4 S.U.A.P.',style = 'FooterStyle')





            # recupera i dati della pratica
            pratica = Pratica.objects.get(id=pratica.id)



            # # recupera TUTTI i richiedenti

            all_rich = Anaprat.objects.filter(pratica_id=pratica.id)
            print('richiedenti', all_rich)
            for a in all_rich:
                soggetto=Soggetto.objects.get(id=a.soggetto_id)



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
                                mappali = 'Foglio ' + part.foglio + ' map ' + part.mappale
                                if p.subalterno !='-':
                                      mappali = mappali + ' sub '+str(p.subalterno)+', '
                            foglio_pre= part.foglio
                            lista.append(mappali)
                    print(lista, foglio_pre, part.foglio)
                    #document.add_paragraph(lista)
            else:
                    prot = pratica.prot_gen
                    data = pratica.data_prot_gen

            ####################################
            #      OGGETTO
            ###################################
            preambolo='Comunicazione di avvio del procedimento e sospensione della pratica \
finalizzata al rilascio di autorizzazione all\' installazione di insegne di esercizio permanenti'
            oggetto_lettera = preambolo

            if pratica.street :

                ubicazione = ', su immobile ubicato in Carrara '
                housenumber = pratica.housenumber

                if housenumber :
                    oggetto_lettera = oggetto_lettera + ubicazione + str(pratica.street) + ' ' + str(pratica.housenumber)
                else:
                                        oggetto_lettera = oggetto_lettera + ubicazione + str(pratica.street).title()




            p2_4 = document.add_paragraph()
            p2_4.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p2_4.paragraph_format.space_before = Pt(30)
            p2_4.add_run(str('Oggetto : ') , style='NumCduStyleItalic').bold=True
            # p2_4 = document.add_paragraph()
            # p2_4.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p2_4.paragraph_format.space_after = Pt(4)
            p2_4.add_run(str(oggetto_lettera ), style='NumCduStyleItalic')
            if lista:
                p2_4.add_run(', distinto in catasto al ', style='NumCduStyleItalic')
                p2_4.add_run(lista, style='NumCduStyleItalic')
            else:
                pass
            ####################################
            #      DITTA
            ###################################
            # recupera il primo richiedente (Q(status='on-sale') | Q(status='paused'))
            rich = Anaprat.objects.filter(Q(pratica_id=pratica.id) & Q(tipo_id=1)).order_by('id')[0]
            print('richiedenti', rich)
            soggetto = Soggetto.objects.get(id=rich.soggetto_id)
            # verifico che esista il codice fiscale
            if len(soggetto.codice_fiscale) == 16:
                # verifico se maschio o femmina
                sesso_cf = soggetto.codice_fiscale[6:8]
                if int(sesso_cf)>40:
                    nascita =' nata a ' + soggetto.comune_nascita.title() + ' il ' + str(soggetto.data_nascita)
                else:
                    nascita =' nato a ' + soggetto.comune_nascita.title() + ' il ' + str(soggetto.data_nascita)
                    print('sesso_cf', sesso_cf)
            prot = pratica.prot_gen
            data = pratica.data_prot_gen

            p001 = document.add_paragraph()
            p001.paragraph_format.left_indent = Inches(0.5)
            p001_text = str.title(soggetto.cognome) + ' ' + str.title(soggetto.nome)
            p001.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p001.paragraph_format.space_after = Pt(4)
            p001.add_run(str('DITTA : ' + p001_text ) , style='NumCduStyleItalic')
            ####################################
            #      RICHIEDENTE
            ###################################
            p002 = document.add_paragraph()
            p002.paragraph_format.left_indent = Inches(0.5)

            p002_text = str.upper(soggetto.cognome) + ' ' + str.title(soggetto.nome)
            p002.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p002.paragraph_format.space_after = Pt(12)
            p002.add_run(str('Rif. Pratica: Prot. Gen. ' + str(pratica.prot_gen + ' del ' + "%s" % pratica.data_prot_gen.strftime('%d') +'/'+ "%s" % pratica.data_prot_gen.strftime('%m')+'/'+"%s" % pratica.data_prot_gen.strftime('%Y')) ) , style='NumCduStyleItalic')

            ####################################
            #      PARAGRAFO NormalStyle
            ###################################

            par_1 = document.add_paragraph()
            par_1.paragraph_format.first_line_indent = Inches(0.3)
            # par_1 = paragraph_format.left_indent = Inches(0.5)
            par_1.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW

            par_1.paragraph_format.space_before = Pt(1)
            par_1.paragraph_format.space_after = Pt(4)
            par_1.add_run()
            par_1.add_run(('Con riferimento alla pratica pervenuta con Prot.Gen. n° ' ), style='NormalStyle')
            par_1.add_run(str(pratica.prot_gen), style='NormalStyle').bold=True
            par_1.add_run((' del '), style='NormalStyle' )
            par_1.add_run("%s" % data.strftime('%d/%m/%Y'), style='NormalStyle').bold=True
            par_1.add_run(''', si comunica ai sensi e per gli effetti degli art. 7, 8 della legge 7 Agosto 1990, \
n° 241 e s.m.i., che questo Ufficio ha dato avvio al procedimento. La pratica è di competenza dello Sportello Unico \
per le Attività Produttive del Comune di Carrara, Piazza 2 Giugno 1, presso il quale codesta società potrà prendere \
visione degli atti.''', style='NormalStyle' )
            RUP = 'dott.ssa Michela Parisi'
            ISTRUTTORE = 'geom. Valerio Vinchesi'
            par_3 = document.add_paragraph()
            par_3.paragraph_format.space_before = Pt(1)
            par_3.paragraph_format.space_after = Pt(1)
            par_3.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_3.add_run('Responsabile del procedimento : ', style='NormalStyle' ).bold=True
            par_3.add_run(str(RUP), style='NormalStyle' ).italic=True
            par_3_1 = document.add_paragraph()
            par_3_1.paragraph_format.space_before = Pt(1)
            par_3_1.paragraph_format.space_after = Pt(4)
            par_3_1.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_3_1.add_run('Istruttore tecnico : ', style='NormalStyle' ).bold=True
            par_3_1.add_run(str(ISTRUTTORE), style='NormalStyle' ).italic=True

            par_4 = document.add_paragraph()
            par_4.paragraph_format.first_line_indent = Inches(0.3)
            par_4.paragraph_format.space_before = Pt(1)
            par_4.paragraph_format.space_after = Pt(1)
            par_4.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_4.add_run('''Il procedimento dovrà concludersi entro 60 giorni dal ricevimento della documentazione.\
 Si informa che la pratica, regolare e completa, sarà inviata agli enti competenti al rilascio dei pareri/atti istruttori di competenza.''', style='NormalStyle' )

            par_4_2 = document.add_paragraph()
            par_4_2.paragraph_format.first_line_indent = Inches(0.3)
            par_4_2.paragraph_format.space_before = Pt(1)
            par_4_2.paragraph_format.space_after = Pt(1)
            par_4_2.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_4_2.add_run('''I termini del procedimento potranno essere sospesi nel caso in cui gli uffici comunali \
o gli enti titolari degli endoprocedimenti richiedano l’integrazione degli atti o dei documenti ai fini istruttori.\
In tal caso i termini del procedimento riprenderanno a decorrere del momento della presentazione della documentazione richiesta. \
Tutte le eventuali documentazioni integrative richieste dagli enti interessati e/o uffici comunali \
dovranno essere presentati tramite questo Sportello.''', style='NormalStyle' )

            # par_4_4 = document.add_paragraph()
            # par_4_4.paragraph_format.space_before = Pt(1)
            # par_4_4.paragraph_format.space_after = Pt(1)
            # par_4_4.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            # par_4_4.add_run('Tutte le eventuali documentazioni integrative richieste dagli enti interessati e/o uffici comunali dovranno essere presentati tramite questo Sportello.', style='NormalStyle' )


            par_5 = document.add_paragraph()
            par_5.paragraph_format.first_line_indent = Inches(0.3)
            par_5.paragraph_format.space_before = Pt(1)
            par_5.paragraph_format.space_after = Pt(4)
            par_5.alignement = WD_ALIGN_PARAGRAPH.LEFT
            par_5.add_run('''Ai sensi di quanto stabilito dall’art. 28 della Legge 9 agosto 2013 n. 98 la Pubblica Amministrazione procedente o, in caso di procedimenti in cui intervengono più amministrazioni, \
quella responsabile del ritardo ed i soggetti privati preposti all\'esercizio di attività amministrative, di cui all’art. 1, comma 1-ter, della legge 7 agosto 1990, n. 241, corrispondono all’interessato, \
a titolo di indennizzo per il mero ritardo, una somma pari a 30 euro per ogni giorno di ritardo, con decorrenza dalla data di scadenza del termine del procedimento,
comunque complessivamente non superiore a 2.000 euro. ''', style='NormalStyle' )

            par_6 = document.add_paragraph()
            par_6.paragraph_format.first_line_indent = Inches(0.3)
            par_6.paragraph_format.space_before = Pt(1)
            par_6.paragraph_format.space_after = Pt(1)
            par_6.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_6.add_run('Al fine di ottenere l’indennizzo, l’istante è tenuto ad azionare il potere sostitutivo previsto ', style='NormalStyle' )
            par_6.add_run('dall’art. 2, comma 9-bis, della legge n. 241 del 1990 nel termine perentorio di ', style='NormalStyle' )
            par_6.add_run('venti giorni dalla scadenza del termine di conclusione del procedimento. ', style='NormalStyle' )

            par_6_1 = document.add_paragraph()
            # par_6_1.paragraph_format.first_line_indent = Inches(0.3)
            par_6_1.paragraph_format.space_before = Pt(1)
            par_6_1.paragraph_format.space_after = Pt(1)
            par_6_1.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_6_1.add_run('Nel caso di procedimenti in cui intervengono più amministrazioni, l’interessato ', style='NormalStyle' )
            par_6_1.add_run('presenta istanza all’amministrazione procedente, che la trasmette tempestivamente ', style='NormalStyle' )
            par_6_1.add_run('al titolare del potere sostitutivo dell’amministrazione responsabile del ritardo.', style='NormalStyle' )

            par_7 = document.add_paragraph()
            par_7.paragraph_format.first_line_indent = Inches(0.3)
            par_7.paragraph_format.space_before = Pt(1)
            par_7.paragraph_format.space_after = Pt(1)
            par_7.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_7.add_run('Nel caso in cui anche il titolare del potere sostitutivo non emani il provvedimento ', style='NormalStyle' )
            par_7.add_run('entro un termine pari alla metà di quello originariamente previsto (30 giorni) o non liquidi ', style='NormalStyle' )
            par_7.add_run('l’indennizzo maturato fino alla data della medesima liquidazione, l’istante può proporre ricorso ', style='NormalStyle' )
            par_7.add_run('ai sensi dell’articolo 117 del codice del processo amministrativo di cui ', style='NormalStyle' )
            par_7.add_run('all’Allegato 1 al D.Lgs. 2 luglio 2010 n. 104, e successive modificazioni, oppure, ricorrendone i presupposti, ', style='NormalStyle' )
            par_7.add_run('dell’articolo 118 dello stesso codice. ', style='NormalStyle' )

            par_7_1 = document.add_paragraph()
            # par_7_1.paragraph_format.first_line_indent = Inches(0.3)
            par_7_1.paragraph_format.space_before = Pt(1)
            par_7_1.paragraph_format.space_after = Pt(1)
            par_7_1.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_7_1.add_run('Il soggetto cui è attribuito il potere sostitutivo è il Segretario Generale del Comune di Carrara.', style='NormalStyle' )

            par_8 = document.add_paragraph()
            # par_8.paragraph_format.first_line_indent = Inches(0.3)
            par_8.paragraph_format.space_before = Pt(1)
            par_8.paragraph_format.space_after = Pt(1)
            par_8.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_8.add_run('Si informa, infine, che, in relazione al procedimento attivato, lo SUAP provvede direttamente alla riscossione \
delle spese e dei diritti istruttori di competenza delle varie amministrazioni coinvolte. \
Questo Sportello si riserva pertanto di comunicare l’importo e le modalità di versamento.', style='NormalStyle' )


            par_8_1 = document.add_paragraph()
            # par_8_1.paragraph_format.first_line_indent = Inches(0.3)
            par_8_1.paragraph_format.space_before = Pt(1)
            par_8_1.paragraph_format.space_after = Pt(1)
            par_8_1.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_8_1.add_run('Per integrazioni e/o comunicazioni relative all’oggetto dell’istanza, la S.V. è pregata di citare il numero di ', style='NormalStyle' )

            par_8_1.add_run(str(pratica.tipo_pratica)+'-', style='NormalStyle' ).bold=True
            par_8_1.add_run(str(pratica.prot_gen)+'-' , style='NormalStyle' ).bold=True
            par_8_1.add_run("%s" % data.strftime('%Y'), style='NormalStyle').bold=True

            par_8_2 = document.add_paragraph()
            # par_8_2.paragraph_format.first_line_indent = Inches(0.3)
            par_8_2.paragraph_format.space_before = Pt(1)
            par_8_2.paragraph_format.space_after = Pt(1)
            par_8_2.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_8_2.add_run('Cordiali saluti', style='NormalStyle' )

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
            par_8_4.add_run('Il Dirigente ad interim', style='NormalStyle' )

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



###     STAMPA CARTELLINA

_LABEL_ID = [0]

def _add_colored_label(document, text, fill="FFC000", font_color="000000", font_size=36):
    """Inserisce una colonna colorata fluttuante a sinistra con il testo
    ruotato dal basso verso l'alto (w:textDirection btLr)."""
    _LABEL_ID[0] += 1
    rid = _LABEL_ID[0]

    emu = 36000
    x = 211 * emu
    y = 10 * emu
    cx = 18 * emu
    cy = 277 * emu

    ns = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
          'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
          'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
          'xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape"')

    xml = (
        '<w:r ' + ns + '>'
        '<w:drawing>'
          '<wp:anchor distT="0" distB="0" distL="0" distR="0" simplePos="0" '
                     'relativeHeight="2" behindDoc="0" locked="0" layoutInCell="1" allowOverlap="1">'
            '<wp:simplePos x="0" y="0"/>'
            '<wp:positionH relativeFrom="page"><wp:posOffset>{x}</wp:posOffset></wp:positionH>'
            '<wp:positionV relativeFrom="page"><wp:posOffset>{y}</wp:posOffset></wp:positionV>'
            '<wp:extent cx="{cx}" cy="{cy}"/>'
            '<wp:effectExtent l="0" t="0" r="0" b="0"/>'
            '<wp:wrapNone/>'
            '<wp:docPr id="{rid}" name="Label{rid}"/>'
            '<wp:cNvGraphicFramePr/>'
            '<a:graphic>'
              '<a:graphicData uri="http://schemas.microsoft.com/office/word/2010/wordprocessingShape">'
                '<wps:wsp>'
                  '<wps:cNvSpPr txBox="1"/>'
                  '<wps:spPr>'
                    '<a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
                    '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
                    '<a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>'
                    '<a:ln><a:noFill/></a:ln>'
                  '</wps:spPr>'
                  '<wps:txbx>'
                    '<w:txbxContent>'
                      '<w:p>'
                        '<w:pPr>'
                          '<w:textDirection w:val="btLr"/>'
                          '<w:jc w:val="center"/>'
                          '<w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/>'
                        '</w:pPr>'
                        '<w:r>'
                          '<w:rPr>'
                            '<w:b/>'
                            '<w:color w:val="{fc}"/>'
                            '<w:sz w:val="{fs}"/><w:szCs w:val="{fs}"/>'
                            '<w:rFonts w:ascii="Arial" w:hAnsi="Arial"/>'
                          '</w:rPr>'
                          '<w:t xml:space="preserve">{text}</w:t>'
                        '</w:r>'
                      '</w:p>'
                    '</w:txbxContent>'
                  '</wps:txbx>'
                  '<wps:bodyPr vert="vert270" lIns="0" tIns="0" rIns="0" bIns="0" anchor="ctr">'
                    '<a:noAutofit/>'
                  '</wps:bodyPr>'
                '</wps:wsp>'
              '</a:graphicData>'
            '</a:graphic>'
          '</wp:anchor>'
        '</w:drawing>'
        '</w:r>'
    ).format(x=x, y=y, cx=cx, cy=cy, rid=rid, fill=fill, fc=font_color, fs=font_size, text=escape(text))

    r = parse_xml(xml)
    p = document.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p._p.append(r)


def _float_picture(run, x, y):
    """Converti un'immagine inline (run.add_picture) in una shape
    ancorata alla pagina alle coordinate (x, y) in EMU, così da non
    occupare spazio nel flusso del testo."""
    drawing = run._r.find(qn('w:drawing'))
    if drawing is None:
        return
    inline = drawing.find(qn('wp:inline'))
    if inline is None:
        return
    extent = inline.find(qn('wp:extent'))
    docPr = inline.find(qn('wp:docPr'))
    graphic = inline.find(qn('a:graphic'))
    anchor = parse_xml(
        '<wp:anchor distT="0" distB="0" distL="0" distR="0" simplePos="0" '
        'relativeHeight="3" behindDoc="0" locked="0" layoutInCell="1" allowOverlap="1" '
        'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        '<wp:simplePos x="0" y="0"/>'
        '<wp:positionH relativeFrom="page"><wp:posOffset>{x}</wp:posOffset></wp:positionH>'
        '<wp:positionV relativeFrom="page"><wp:posOffset>{y}</wp:posOffset></wp:positionV>'
        '</wp:anchor>'.format(x=x, y=y)
    )
    anchor.append(extent)
    anchor.append(parse_xml('<wp:effectExtent l="0" t="0" r="0" b="0" '
                            'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"/>'))
    anchor.append(parse_xml('<wp:wrapNone '
                            'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"/>'))
    anchor.append(docPr)
    anchor.append(parse_xml('<wp:cNvGraphicFramePr '
                            'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"/>'))
    anchor.append(graphic)
    drawing.append(anchor)
    drawing.remove(inline)


def _merc_y(lat, n):
    """Ordinata di Mercator (in frazioni di tile, moltiplicata per n) per una latitudine."""
    lat_rad = math.radians(lat)
    return (1 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2 * n


def _add_map_image(document, posizione, mpoly=None, particelle=None, cols=5, rows=3, default_zoom=17, return_image=False, show_bar=True):
    """Stitch delle tile OSM locali (static/tiles). Se mpoly_pratica è
    presente, lo zoom viene calcolato sul suo bounding box lasciando il 30%
    di margine; vengono disegnate le singole particelle (con etichetta
    foglio/mappale) e la mappa fluttua nell'A4 di sinistra."""
    if not posizione:
        return None

    lng = posizione.x
    lat = posizione.y
    zoom = default_zoom
    center_lng, center_lat = lng, lat

    # zoom adattivo al bounding box di mpoly_pratica (30% di margine)
    ext = getattr(mpoly, 'extent', None)
    if ext and (ext[2] - ext[0]) > 0 and (ext[3] - ext[1]) > 0:
        xmin, ymin, xmax, ymax = ext
        allowed_x = cols * 256 * 0.7
        allowed_y = rows * 256 * 0.7
        for z in range(19, 9, -1):
            nz = 2 ** z
            px_lng = (xmax - xmin) / 360.0 * (nz * 256)
            px_lat = abs(_merc_y(ymax, nz) - _merc_y(ymin, nz)) * 256
            if px_lng <= allowed_x and px_lat <= allowed_y:
                zoom = z
                break

    def _compute_xy(cx, cy, z):
        nz = 2 ** z
        cxt = (cx + 180.0) / 360.0 * nz
        cyt = _merc_y(cy, nz)
        return nz, cxt, cyt

    n, xt, yt = _compute_xy(center_lng, center_lat, zoom)
    x0 = int(math.floor(xt - (cols - 1) / 2.0))
    y0 = int(math.floor(yt - (rows - 1) / 2.0))

    tile_size = 256
    img = Image.new('RGBA', (cols * tile_size, rows * tile_size), (255, 255, 255, 255))
    base = os.path.join('static', 'tiles', str(zoom))

    def _load_tiles(im, bdir, ax0, ay0):
        found = 0
        for i in range(cols):
            for j in range(rows):
                path = os.path.join(bdir, str(ax0 + i), str(ay0 + j) + '.png')
                if os.path.exists(path):
                    try:
                        im.paste(Image.open(path).convert('RGBA'), (i * tile_size, j * tile_size))
                        found += 1
                    except Exception:
                        pass
        return found

    found = _load_tiles(img, base, x0, y0)

    # fallback: lo zoom calcolato potrebbe non avere tile in cache
    if found == 0 and (zoom != default_zoom
                       or abs(center_lng - lng) > 1e-9
                       or abs(center_lat - lat) > 1e-9):
        zoom = default_zoom
        n, xt, yt = _compute_xy(lng, lat, zoom)
        x0 = int(math.floor(xt - (cols - 1) / 2.0))
        y0 = int(math.floor(yt - (rows - 1) / 2.0))
        base = os.path.join('static', 'tiles', str(zoom))
        img = Image.new('RGBA', (cols * tile_size, rows * tile_size), (255, 255, 255, 255))
        _load_tiles(img, base, x0, y0)

    # proietta lng/lat in pixel immagine (usata per poligoni ed etichette)
    def _proj(lng, lat):
        cxt = (lng + 180.0) / 360.0 * n
        cyt = _merc_y(lat, n)
        return ((cxt - x0) * tile_size, (cyt - y0) * tile_size)

    draw = ImageDraw.Draw(img)

    # perimetro complessivo di mpoly_pratica (tenue)
    if mpoly:
        for poly in mpoly:
            for ring in poly:
                pts = [_proj(coord[0], coord[1]) for coord in ring]
                if len(pts) > 2:
                    draw.polygon(pts, outline=(120, 120, 120, 200), fill=None, width=2)

    # singole particelle con etichetta del mappale sul margine
    if particelle:
        outline = (200, 0, 0, 255)
        try:
            lab_font = ImageFont.truetype('/usr/share/matplotlib/mpl-data/fonts/ttf/DejaVuSans-Oblique.ttf', 16)
        except Exception:
            lab_font = ImageFont.load_default()
        for idx, part in enumerate(particelle):
            geom = getattr(part, 'mpoly', None)
            if not geom:
                continue
            polys = geom if geom.geom_type == 'MultiPolygon' else [geom]
            all_pts = []
            for poly in polys:
                for ring in poly:
                    pts = [_proj(coord[0], coord[1]) for coord in ring]
                    if len(pts) > 2:
                        draw.polygon(pts, outline=outline, fill=None, width=3)
                        all_pts.extend(pts)
            if all_pts:
                xs = [p[0] for p in all_pts]
                ys = [p[1] for p in all_pts]
                top_x = (min(xs) + max(xs)) / 2.0
                top_y = min(ys)
                c = geom.centroid
                if c:
                    ccx, ccy = _proj(c.x, c.y)
                else:
                    ccx, ccy = top_x, top_y
                # etichetta a metà strada fra il margine superiore e il centroide
                lx = top_x + (ccx - top_x) * 0.5
                ly = top_y + (ccy - top_y) * 0.5
                label = str(getattr(part, 'mappale', ''))
                tb = draw.textbbox((0, 0), label, font=lab_font)
                w = tb[2] - tb[0] + 6
                h = tb[3] - tb[1] + 4
                draw.rectangle([lx - w / 2, ly - h / 2, lx + w / 2, ly + h / 2], fill=(255, 255, 255, 220))
                draw.text((lx - w / 2 + 3, ly - h / 2 + 2), label, fill=(0, 0, 0, 255), font=lab_font)

    # marker dell'ubicazione (posizione), sempre visibile anche senza particelle
    mx, my = _proj(lng, lat)
    # ombra
    draw.ellipse([mx - 15, my - 10, mx + 15, my + 22], fill=(0, 0, 0, 55))
    # cerchio rosso ben visibile
    draw.ellipse([mx - 13, my - 13, mx + 13, my + 13], fill=(220, 0, 0, 255), outline=(255, 255, 255, 255), width=3)
    draw.ellipse([mx - 4, my - 4, mx + 4, my + 4], fill=(255, 255, 255, 255))

    # didascalia disegnata sull'immagine
    try:
        font = ImageFont.truetype('/usr/share/matplotlib/mpl-data/fonts/ttf/DejaVuSans-Bold.ttf', 30)
    except Exception:
        font = ImageFont.load_default()
    bar_h = 60
    ImageDraw.Draw(img).rectangle([0, img.height - bar_h, img.width, img.height], fill=(255, 255, 255, 215))
    ImageDraw.Draw(img).text((15, img.height - bar_h + 8), "Mappa dell’ubicazione", fill=(0, 0, 0, 255), font=font)
    try:
        osm_font = ImageFont.truetype('/usr/share/matplotlib/mpl-data/fonts/ttf/DejaVuSans.ttf', 14)
    except Exception:
        osm_font = ImageFont.load_default()
    ImageDraw.Draw(img).text((15, img.height - bar_h + 36), "© OpenStreetMap contributors", fill=(80, 80, 80, 255), font=osm_font)

    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)

    if return_image:
        return buf

    pmap = document.add_paragraph()
    pmap.paragraph_format.space_before = Pt(0)
    pmap.paragraph_format.space_after = Pt(0)
    run = pmap.add_run()
    run.add_picture(buf, width=Mm(200))
    if show_bar:
        _float_picture(run, 5 * 36000, 40 * 36000)


def Cartellina(request, pk):
        # id = request.session.get('pk')
        pratica = get_object_or_404(Pratica, id=pk)
        print (pratica)
        print('tipo',pratica.tipo_pratica)

        commissioni = Commissione.objects.filter(pratica_id=pk).order_by('-commissione_date')[:1]
        if commissioni:
            user = request.user.username
            # print('commissioni',commissioni, 'user',user)
            # return redirect('protocollo:pratica_detail_url', pk=id)


        atto = 'cartellina_' +str(pratica.tipo_pratica) +'_' + str(pratica.prot_gen) +'_' + "%s" % pratica.data_prot_gen.strftime('%Y%m%d') +'.docx'

        document = Document()
        # imposta A4 verticale e margini
        section = document.sections[0]
        section.page_height = Mm(297)
        section.page_width = Mm(420)
        section.left_margin = Mm(234)
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




    #   IMPOSTA GLI STILI DEI SINGOLI PARAGRAFI




        # document.add_paragraph()
        font = document.styles['Normal'].font
        font.size=Pt(11)
        font.name='Arial'



        obj_styles = document.styles
        obj_charstyle = obj_styles.add_style('Titolo', WD_STYLE_TYPE.CHARACTER)
        obj_font = obj_charstyle.font
        obj_font.bold = True
        obj_font.size = Pt(18)
        obj_font.name = 'Arial'



        obj_styles = document.styles
        obj_charstyle = obj_styles.add_style('NormalStyle', WD_STYLE_TYPE.CHARACTER)
        obj_font = obj_charstyle.font
        obj_font.size = Pt(10)
        obj_font.name = 'Arial'

        obj_styles = document.styles
        obj_charstyle = obj_styles.add_style('SottoHeaderStyle', WD_STYLE_TYPE.CHARACTER)
        obj_font = obj_charstyle.font
        obj_font.size = Pt(11)
        obj_font.name = 'Arial'

        obj_styles = document.styles
        obj_charstyle = obj_styles.add_style('HeaderStyle', WD_STYLE_TYPE.CHARACTER)
        obj_font = obj_charstyle.font
        obj_font.size = Pt(9)
        obj_font.name = 'Arial'

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
        obj_charstyle = obj_styles.add_style('NumCduStyleItalic', WD_STYLE_TYPE.CHARACTER)
        obj_font = obj_charstyle.font
        obj_font.italic = True
        obj_font.size = Pt(9)
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


         # recupera i dati della pratica
        pratica = Pratica.objects.get(id=pratica.id)

        # Changing the orientation to landscape
        section.orientation = WD_ORIENT.LANDSCAPE

        # paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW

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

        # colonna colorata a sinistra con il tipo di pratica ruotato dal basso verso l'alto
        _tipo_label = str(pratica.tipo_pratica).upper()
        _colori_colonna = {
            'CDU': 'FFC000',
            'C.D.U.': 'FFC000',
            'ASCENSORE': '70AD47',
            'SCIA': '2E75B6',
            'CILA': '2E75B6',
            'PDC': 'C00000',
            'PERMESSO DI COSTRUIRE': 'C00000',
            'SANATORIA': 'C00000',
            'INSEGNA': '7FEF00',
        }
        _fill = _colori_colonna.get(_tipo_label, '1F4E79')
        _add_colored_label(document, _tipo_label, fill=_fill, font_color='FFFFFF', font_size=54)


        p0 = document.add_paragraph()
        p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p0.paragraph_format.space_before = Pt(0)
        p0.paragraph_format.space_after = Pt(1)
        p0.add_run('Settore 6 - GOVERNO DEL TERRITORIO - Servizio 6.1',style = 'HeaderStyle')


        prot = pratica.prot_gen
        data = pratica.data_prot_gen

    # #    stampo i dati della U.O.

        p1 = document.add_paragraph()
        p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p1.add_run('U.O. 6.1.2 Sportello Unico per l’Edilizia (S.U.E.) e vigilanza abusivismo',style = 'DprStyle')

         # stampa data:ora e user
        ora_di_stampa = datetime.now()

        p00 = document.add_paragraph()
        p00.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p00.paragraph_format.space_before = Pt(0)
        p00.paragraph_format.space_after = Pt(30)
        p00.add_run("%s" % ora_di_stampa.strftime('%d/%m/%Y : %H:%M:%S'  ),style = 'HeaderStyle')
        p00.add_run(' - ' + str(request.user.username),style = 'HeaderStyle')

        p0 = document.add_paragraph()
        p0.alignment = WD_ALIGN_PARAGRAPH.LEFT



        p0.add_run(' ( '+str(pratica.tipo_pratica.description) + ' )',style='FooterStyle').italic=True
        # titolo----> tipo di pratica
        p = document.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.add_run(' '+ str(pratica.tipo_pratica).upper(),style='Titolo').underline=True
        # inserisco il numero degli atti rilasciati se presenti
        # verifico i CDU
        atti = Cerdesurb.objects.filter(pratica_id=pratica.id)
        if atti:
            for a in atti:



                p.add_run(' - ' + str(a.cdu_number)+ ' del ' + "%s" % a.cdu_date.strftime('%d/%m/%Y'),style='Titolo').underline=True

        p2 = document.add_paragraph()
        p2.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p2.add_run('Prot. Gen. ',style='HeaderStyle')
        p2.add_run(str(pratica.prot_gen),style='CduStyle').bold=True



        p2.add_run(' del ',style='HeaderStyle')
        p2.add_run("%s" % pratica.data_prot_gen.strftime('%d/%m/%Y'),style='CduStyle').bold=True

        p2_1 = document.add_paragraph()
        p2_1.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p2_1.add_run('Progressivo: ',style='HeaderStyle')
        p2_1.add_run(str(pratica.code_p),style='HeaderStyle').bold=True

        p2_1.add_run('/',style='HeaderStyle')
        p2_1.add_run("%s" % pratica.data_prot_gen.strftime('%Y'),style='HeaderStyle').bold=True


        print('atti',atti)
        p3 = document.add_paragraph()
        p3.paragraph_format.space_after = Pt(30)
        p3.alignment = WD_ALIGN_PARAGRAPH.LEFT


        p3_1 = document.add_paragraph()
        p3_1.paragraph_format.space_after = Pt(30)
        p3_1.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p3_1.paragraph_format.space_before = Pt(30)

        p3_1.add_run('Oggetto : ',style='NormalStyle').bold=True
        p3_1.add_run(str(pratica.oggetto),style='CduStyle').italic=True

        p3_3 = document.add_paragraph()
        p3_3.paragraph_format.space_after = Pt(30)
        p3_3.alignment = WD_ALIGN_PARAGRAPH.LEFT

        p3_3.add_run('Ubicazione : ',style='NormalStyle').bold=True
        p3_3.add_run(str(pratica.street),style='CduStyle').italic=True

        if pratica.housenumber:
            p3_3.add_run(', '+str(pratica.housenumber),style='CduStyle').italic=True








        # # recupera TUTTI i richiedenti

        all_rich = Anaprat.objects.filter(pratica_id=pratica.id).order_by('tipo_id')
        print('richiedenti', all_rich)
        for a in all_rich:


            soggetto = Soggetto.objects.get(id=a.soggetto_id)
            print (a.tipo)
            p4 = document.add_paragraph()
            p4.paragraph_format.space_after = Pt(4)
            p4.alignment = WD_ALIGN_PARAGRAPH.LEFT

            p4.add_run(' ' + str(soggetto.cognome.upper() + ' '),style='NormalStyle').bold=True
            p4.add_run(str(soggetto.nome.title()),style='NormalStyle').bold=True
            p4.add_run(' ( ' + str(a.tipo) + ' )',style='HeaderStyle').italic=True

            p4_1 = document.add_paragraph()
            p4_1.paragraph_format.space_before = Pt(4)
            p4_1.paragraph_format.space_after = Pt(4)
            p4_1.paragraph_format.first_line_indent = Inches(1.6)
            p4_1.alignment = WD_ALIGN_PARAGRAPH.LEFT
            if soggetto.cellulare:
                p4_1.add_run((' cellulare: ' + str(soggetto.cellulare)),style='FooterStyle')
            if soggetto.telefono:
                p4_1.add_run(' telefono: ' + str(soggetto.telefono),style='FooterStyle')

        # ESTRAE le particelle interessate e le conta
        particelle = Cataprat.objects.filter(pratica_id=pratica.id)
        tot_particelle = particelle.count()

        print('tot particelle',tot_particelle)


        # print(particelle)

        foglio_pre="" # imposta a blank il foglio precedente
        lista =[] # lista le particelle nella pratica
        if tot_particelle:
            # paragraph = document.add_paragraph()
            for p in particelle:
                # mappali ={}
                part = Particella.objects.get(id=p.particella_id)
                print('part',part)
                if foglio_pre==part.foglio:
                    mappali = ', ' + part.mappale
                    if p.subalterno != '-':
                        mappali = mappali + ' sub ' + str(p.subalterno)
                else:
                    mappali = ' Foglio ' + part.foglio + ' map ' + part.mappale
                    if p.subalterno != '-':
                        mappali = mappali + ' sub ' + str(p.subalterno)

                foglio_pre= part.foglio
                lista.append(mappali)
                print(lista, foglio_pre, part.foglio)
                #document.add_paragraph(lista)
        else:
                prot = pratica.prot_gen
                data = pratica.data_prot_gen

        if lista:
            pp2 = document.add_paragraph()
            pp2.alignment = WD_ALIGN_PARAGRAPH.LEFT
            pp2.paragraph_format.space_before = Pt(30)

            pp2.add_run('Particelle :',style='NormalStyle').bold=True
            pp2 = document.add_paragraph()
            pp2.alignment = WD_ALIGN_PARAGRAPH.LEFT
            pp2.add_run(lista,style='NumCduStyleItalic')


        # mappa dell'ubicazione (dopo le particelle) con perimetro mpoly_pratica
        part_ids = [p.particella_id for p in particelle]
        particelle_objs = list(Particella.objects.filter(id__in=part_ids, mpoly__isnull=False))
        _add_map_image(document, pratica.posizione, mpoly=pratica.mpoly_pratica,
                       particelle=particelle_objs, cols=5, rows=3)


        # stampa commissioni paesaggio se presenti
        commissioni = Commissione.objects.filter(pratica_id=pk).order_by('-commissione_date')
        if commissioni.count() > 0 :
            print('commissioni',commissioni)
            p_comm_1 = document.add_paragraph()
            p_comm_1.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p_comm_1.paragraph_format.space_before = Pt(4)
            p_comm_1.add_run('Commissioni paesaggio',style='CduStyle').bold=True
            for c in commissioni:
                p_comm_2 = document.add_paragraph()
                p_comm_2.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p_comm_2.paragraph_format.space_before = Pt(4)
                p_comm_2.add_run('num. commissione : ' + str(c.commissione_number) + ' del ' + "%s" % c.commissione_date.strftime('%d/%m/%Y') + ' '+ str(c.parere) ,style='NumCduStyleItalic')

        # stampa convenzioni cooperative se presenti

        conv = IstrConv.objects.filter(pratica_id=pk)
            # print('jaha77adad7ad7.....',id)
            # p_conv_1 = document.add_paragraph()
            # p_conv_1.alignment = WD_ALIGN_PARAGRAPH.LEFT
            # p_conv_1.paragraph_format.space_before = Pt(4)
            # p_conv_1.add_run('Convenzione',style='CduStyle').bold=True
        # conv = IstrConv.objects.get(pratica_id=id)
        # print(conv)
        if conv :
            for c in conv:

                p_conv_1 = document.add_paragraph()
                p_conv_1.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p_conv_1.paragraph_format.space_before = Pt(4)
                p_conv_1.add_run('Convenzione',style='CduStyle').bold=True
                p_conv_1.add_run( '      Diritto di ' + str(c.tipo_diritto),style='CduStyle').bold=True

                conv_euro = round(c.conv_lire/Decimal(1936.27),2)
                p_conv_2 = document.add_paragraph()
                p_conv_2.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p_conv_2.paragraph_format.space_before = Pt(4)
                if c.data_atto:
                    p_conv_2.add_run('Atto : ' + str(c.notaio) + ' del ' + "%s" % c.data_atto.strftime('%d/%m/%Y') +' - '+ str(c.atto) ,style='NumCduStyleItalic')

                    delta = (c.data_rival - c.data_atto)
                    p_conv_2_1 = document.add_paragraph()
                    p_conv_2_1.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    p_conv_2_1.paragraph_format.space_before = Pt(4)
                    p_conv_2_1.add_run(' anni trascorsi : ' + str(int(delta.days/365)) ,style='NumCduStyleItalic')

                else:
                    p_conv_2.add_run('Atto : ' + str(c.notaio) + ' del ???????? '  + str(c.atto) ,style='NumCduStyleItalic')


                p_conv_2_2 = document.add_paragraph()
                p_conv_2_2.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p_conv_2_2.paragraph_format.space_before = Pt(4)
                p_conv_2_2.add_run(' data di rivalutazione : ' + "%s" % c.data_rival.strftime('%d/%m/%Y') ,style='NumCduStyleItalic')


                p_conv_3 = document.add_paragraph()
                p_conv_3.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p_conv_3.paragraph_format.space_before = Pt(4)
                p_conv_3.add_run('Importo diritto di proprietà : ' + str(int(c.valore_dirsup))  ,style='NormalStyle')


                p_conv_5 = document.add_paragraph()
                p_conv_5.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p_conv_5.paragraph_format.space_before = Pt(4)

                p_conv_5.add_run('Importo rimozione vincolo : ' + str(c.crv_uiu) + ' € ' ,style='NormalStyle')

                print('conv_euro')

        else:
              print('why?....pecchè?....')


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


########################################################
##### AVVIO PROCEDIMENTO PDC ########
########################################################
def PdcAvvioProc(request):

        id = request.session.get('pk')
        print('id',id)
        pratica = Pratica.objects.get(id=id) # ritorna  i dati pratica
        print (pratica)
        print('tipo',pratica.tipo_pratica)

        if pratica.tipo_pratica_id == 17 : # per PDC

            atto = 'avvio_proc_pdc_' +str(pratica.tipo_pratica) + '_' +  str(pratica.prot_gen) +'_' + "%s" % pratica.data_prot_gen.strftime('%Y%m%d') +'.docx'

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

            # f1=footer.add_paragraph()
            # f1.paragraph_format.space_after = Pt(0)
            # f1.paragraph_format.space_before = Pt(0)
            # f1.add_run("Settore 6 - Governo del territorio - P.za due giugno,1 54033 - Carrara (MS)", style = 'FooterStyle')

            f2=footer.add_paragraph()
            f2.alignment = WD_ALIGN_PARAGRAPH.CENTER
            f2.paragraph_format.space_after = Pt(0)
            f2.paragraph_format.space_before = Pt(0)
            f2.add_run("Piazza due giugno, 1", style = 'FooterStyle')

            f3=footer.add_paragraph()
            f3.alignment = WD_ALIGN_PARAGRAPH.CENTER
            f3.paragraph_format.space_after = Pt(0)
            f3.paragraph_format.space_before = Pt(0)
            f3.add_run("54033 Carrara (MS)", style = 'FooterStyle')

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
            obj_charstyle = obj_styles.add_style('NormalStyleItalic', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = True

            obj_font.size = Pt(10)
            obj_font.name = 'Arial'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('SottoHeaderStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(11)
            obj_font.name = 'Arial'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('HeaderStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(8)
            obj_font.name = 'Arial'

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
            obj_charstyle = obj_styles.add_style('NumCduStyleItalic', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = True
            obj_font.size = Pt(9)
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

            paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW

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
            p0.add_run('Settore 6 - GOVERNO DEL TERRITORIO',style = 'FooterStyle')




        # #    stampo i dati della U.O.

            # p1 = document.add_paragraph()
            # p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
            # p1.add_run('Servizio 7.2 SUAP, demanio e paesaggio - U.O. 7.4 S.U.A.P.',style = 'FooterStyle')





            # recupera i dati della pratica
            pratica = Pratica.objects.get(id=pratica.id)



            # # recupera TUTTI i richiedenti

            all_rich = Anaprat.objects.filter(pratica_id=pratica.id)
            print('richiedenti', all_rich)
            for a in all_rich:
                soggetto=Soggetto.objects.get(id=a.soggetto_id)



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
                                mappali = 'fg ' + part.foglio + ' map ' + part.mappale
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
            rich = Anaprat.objects.filter(Q(pratica_id=pratica.id) & Q(tipo_id=1)).order_by('id')[0]
            # recuperea il tecnico istruttore
            istr_tec = Anaprat.objects.get(Q(pratica_id=pratica.id) & Q(tipo_id=3))
            s_istr_tec = Soggetto.objects.get(id=istr_tec.soggetto_id)

            print('richiedenti', rich)
            soggetto = Soggetto.objects.get(id=rich.soggetto_id)
            # verifico che esista il codice fiscale
            if soggetto.codice_fiscale:
                # verifico se maschio o femmina
                sesso_cf = soggetto.codice_fiscale[6:8]
                if int(sesso_cf)>40:
                    nascita =' nata a ' + soggetto.comune_nascita.title() + ' il ' + str(soggetto.data_nascita)
                else:
                    nascita =' nato a ' + soggetto.comune_nascita.title() + ' il ' + str(soggetto.data_nascita)
                    print('sesso_cf', sesso_cf)
            prot = pratica.prot_gen
            data = pratica.data_prot_gen


            ####################################
            #      OGGETTO
            ###################################
            preambolo='Avvio di procedimento ai sensi degli artt.7 e ss. della L. 241/1990 \
e smi e degli artt. 134 e 142 della L.R.T. 65/2014 e smi - Istanza di Permesso di Costruire \
presentata da ' + soggetto.cognome.title() + ' ' + soggetto.nome.title() + ' Prot. Gen. n. ' + pratica.prot_gen + ' del ' + "%s" % pratica.data_prot_gen.strftime('%d') +'/'+ "%s" % pratica.data_prot_gen.strftime('%m')+'/'+"%s" % pratica.data_prot_gen.strftime('%Y')


            oggetto_lettera = preambolo

            # if pratica.street :

            #     ubicazione = ' Istanza di Permesso di Costruire presentata da  ' + soggetto.cognome + ' ' + soggetto.nome
            #     housenumber = pratica.housenumber

            if pratica.housenumber :
                    ubicazione=str(pratica.street) + ' ' + str(pratica.housenumber)
            else:
                                        ubicazione =  str(pratica.street).title()




            p2_4 = document.add_paragraph()
            p2_4.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p2_4.paragraph_format.space_before = Pt(30)
            p2_4.add_run(str('Oggetto : ') , style='NumCduStyleItalic').bold=True
            # p2_4 = document.add_paragraph()
            # p2_4.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p2_4.paragraph_format.space_after = Pt(4)
            p2_4.add_run(str(oggetto_lettera ), style='NumCduStyleItalic').bold=True

            ####################################
            #      PARAGRAFO NormalStyle
            ###################################

            par_1 = document.add_paragraph()
            par_1.paragraph_format.first_line_indent = Inches(0.3)
            # par_1 = paragraph_format.left_indent = Inches(0.5)
            par_1.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW

            par_1.paragraph_format.space_before = Pt(1)
            par_1.paragraph_format.space_after = Pt(4)
            par_1.add_run()
            par_1.add_run(('Con riferimento all\' istanza depositata in data ' ), style='NormalStyle')
            par_1.add_run("%s" % data.strftime('%d/%m/%Y'), style='NormalStyle')
            par_1.add_run((' prot. gen. n. '), style='NormalStyle')
            par_1.add_run(str(pratica.prot_gen), style='NormalStyle').bold=True
            # par_1.add_run((' del '), style='NormalStyle' )
            # par_1.add_run("%s" % data.strftime('%d/%m/%Y'), style='NormalStyle').bold=True
            par_1.add_run(''', con la quale è stato richiesto il rilascio di Permesso di Costruire, ai sensi degli artt. 134 e 142 della L.R.T. n. 65/2014 e smi \
per lavori consistenti in ''', style='NormalStyle' )
            par_1.add_run(('"' + str(pratica.oggetto+'"')), style='NormalStyleItalic' ).bold=True
            par_1.add_run(''', sull'immobile sito in Carrara,  ''', style='NormalStyle' )
            par_1.add_run( ubicazione, style='NormalStyle' )

            if lista:
                par_1.add_run(', catastalmente censito al ', style='NormalStyle')
                par_1.add_run(lista, style='NormalStyle')
            else:
                pass



            par_4 = document.add_paragraph()
            par_4.paragraph_format.first_line_indent = Inches(0.3)
            par_4.paragraph_format.space_before = Pt(1)
            par_4.paragraph_format.space_after = Pt(1)
            par_4.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_4.add_run('''Il termine di conclusione del presente procedimento è fissato in 90 gg. ( o in 180 gg. quando il procedimento è qualificato come particolarmente complesso ) dalla data di deposito dell'istanza stessa, salvo sospensione e/o interruzione dei termini.''', style='NormalStyle' )

            par_4_2 = document.add_paragraph()
            par_4_2.paragraph_format.first_line_indent = Inches(0.3)
            par_4_2.paragraph_format.space_before = Pt(1)
            par_4_2.paragraph_format.space_after = Pt(1)
            par_4_2.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_4_2.add_run('''Decorso il termine sopra richiamato l'interessato può chiedere al titolare del potere sostitutivo interno al Comune, ovvero al Segretario Generale, di adempiere entro 15 gg. dal ricevimento dell'istanza.''', style='NormalStyle' )

            par_4_3 = document.add_paragraph()
            par_4_3.paragraph_format.first_line_indent = Inches(0.3)
            par_4_3.paragraph_format.space_before = Pt(1)
            par_4_3.paragraph_format.space_after = Pt(1)
            par_4_3.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_4_3.add_run('''Nel caso in cui il Comune ancora non adempia, l'interessato può presentare istanza alla Regione Toscana, come disposto dall'art. 144 L.R.T. 65/2014 e smi.''', style='NormalStyle' )


            par_4_4 = document.add_paragraph()
            par_4_4.paragraph_format.first_line_indent = Inches(0.3)
            par_4_4.paragraph_format.space_before = Pt(5)
            par_4_4.paragraph_format.space_after = Pt(5)
            par_4_4.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_4_4.add_run('In osservanza degli artt. 5 e 7 della L. 241/1990 e smi, si informa che l\'Ufficio competente è l\'U.O. SUE e che la pratica è stata assegnata all\'Istruttore Tecnico, ' + s_istr_tec.nome +' '+s_istr_tec.cognome, style='NormalStyle' )
            par_4_4.add_run(' contattabile al ' + s_istr_tec.telefono +' ed all\'indirizzo mail : ' + s_istr_tec.email +'.', style='NormalStyle' )

            par_4_5 = document.add_paragraph()
            par_4_5.paragraph_format.first_line_indent = Inches(0.3)
            par_4_5.paragraph_format.space_before = Pt(1)
            par_4_5.paragraph_format.space_after = Pt(8)
            par_4_5.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_4_5.add_run(''' Si invita la S.V. qualora dovesse rivolgersi presso il Settore o intraprendere corrispondenza a citare le sottoelencate diciture:''', style='NormalStyle' )
            par_4_5.add_run(' Prot. Gen. '+  pratica.prot_gen + ' del ' + "%s" % pratica.data_prot_gen.strftime('%d') +'/'+ "%s" % pratica.data_prot_gen.strftime('%m')+'/'+"%s" % pratica.data_prot_gen.strftime('%Y')+'.', style='NormalStyle' )


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
            par_8_4.add_run('Il Dirigente ad interim', style='NormalStyle' )

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


########################################################
##### RICHIESTA PARERE ########
########################################################
def RichiestaParere(request):

        id = request.session.get('pk')
        print('id',id)
        pratica = Pratica.objects.get(id=id) # ritorna  i dati pratica
        print (pratica)
        print('tipo',pratica.tipo_pratica)

        if pratica.tipo_pratica_id == 12  or pratica.tipo_pratica_id == 19 or pratica.tipo_pratica_id == 11: # per PDC

            atto = 'richiesta_parere_' +str(pratica.tipo_pratica) + '_' +  str(pratica.prot_gen) +'_' + "%s" % pratica.data_prot_gen.strftime('%Y%m%d') +'.docx'

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

            # f1=footer.add_paragraph()
            # f1.paragraph_format.space_after = Pt(0)
            # f1.paragraph_format.space_before = Pt(0)
            # f1.add_run("Settore 7 - Governo del territorio / Servizio 7.2 SUAP, demanio e paesaggio - U.O. 7.4 S.U.A.P. - P.za due giugno,1 54033 - Carrara (MS)", style = 'FooterStyle')

            # f2=footer.add_paragraph()
            # f2.alignment = WD_ALIGN_PARAGRAPH.CENTER
            # f2.paragraph_format.space_after = Pt(0)
            # f2.paragraph_format.space_before = Pt(0)
            # f2.add_run("Piazza due giugno, 1", style = 'FooterStyle')

            # f3=footer.add_paragraph()
            # f3.alignment = WD_ALIGN_PARAGRAPH.CENTER
            # f3.paragraph_format.space_after = Pt(0)
            # f3.paragraph_format.space_before = Pt(0)
            # f3.add_run("54033 Carrara (MS)", style = 'FooterStyle')

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
            obj_charstyle = obj_styles.add_style('NormalStyleItalic', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = True

            obj_font.size = Pt(10)
            obj_font.name = 'Arial'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('SottoHeaderStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(11)
            obj_font.name = 'Arial'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('HeaderStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(8)
            obj_font.name = 'Arial'

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
            obj_charstyle = obj_styles.add_style('NumCduStyleItalic', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = True
            obj_font.size = Pt(9)
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
            #   IMPOSTA IL FOOTER
            footer=section.footer

            f1=footer.add_paragraph()
            f1.alignment = WD_ALIGN_PARAGRAPH.CENTER
            f1.paragraph_format.space_after = Pt(0)
            f1.paragraph_format.space_before = Pt(3)
            f1.add_run("Comune di Carrara - P.za due giugno,1 54033 - Carrara (MS)", style = 'FooterStyle')

            f2=footer.add_paragraph()
            f2.alignment = WD_ALIGN_PARAGRAPH.CENTER

            f2.paragraph_format.space_after = Pt(0)
            f2.paragraph_format.space_before = Pt(0)
            f2.add_run("geom. Valerio Vinchesi - 0585 641235 - valerio.vinchesi@comune.carrara.ms.it", style = 'FooterStyle')



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

            run = paragraph.add_run()
            run.add_picture(image_path, width=Inches(1.6))
            # Posiziona centralmente l'immagine
            paragraph_format = paragraph.paragraph_format
            paragraph_format.alignment = 1 # 1 - allineato centrato 0 - allineato a sx


            p0 = document.add_paragraph()
            p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p0.paragraph_format.space_before = Pt(0)
            p0.paragraph_format.space_after = Pt(1)
            p0.add_run('Settore 6 - GOVERNO DEL TERRITORIO',style = 'FooterStyle')


            #

        # #    stampo i dati della U.O.

            # p1 = document.add_paragraph()
            # p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
            # p1.add_run('Servizio 7.2 SUAP, demanio e paesaggio - U.O. 7.4 S.U.A.P.',style = 'FooterStyle')





            # recupera i dati della pratica
            pratica = Pratica.objects.get(id=pratica.id)



            # # recupera TUTTI i richiedenti

            all_rich = Anaprat.objects.filter(pratica_id=pratica.id)
            print('richiedenti', all_rich)
            for a in all_rich:
                soggetto=Soggetto.objects.get(id=a.soggetto_id)

                 #inserisce POLIZIA MUNICIPALE
                p2 = document.add_paragraph()
                p2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                p2.paragraph_format.space_after = Pt(3)
                p2.add_run('Spett.Le Polizia Municipale ' , style='NumCduStyle').bold=True

                p2_0 = document.add_paragraph()
                p2_0.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                p2_0.paragraph_format.space_after = Pt(3)
                p2_0.add_run('Comune di Carrara ' , style='NumCduStyle').bold=True

                p2_01 = document.add_paragraph()
                p2_01.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                p2_01.paragraph_format.space_after = Pt(9)
                p2_01.add_run('Sede' , style='NumCduStyle').bold=True

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
                                mappali = 'fg ' + part.foglio + ' map ' + part.mappale
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
            rich = Anaprat.objects.filter(Q(pratica_id=pratica.id) & Q(tipo_id=1)).order_by('id')[0]
            # recuperea il tecnico istruttore
            '''
            istr_tec = Anaprat.objects.get(Q(pratica_id=pratica.id) & Q(tipo_id=3))
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

            if ubicazione != '0':
                preambolo='Richiesta di parere per la pratica di autorizzazione relativa alla ' + pratica.oggetto +  ' in Carrara ' + str(ubicazione)

#soggetto.cognome + ' ' + soggetto.nome + ' Prot. Gen. n. ' + pratica.prot_gen + ' del ' + "%s" % pratica.data_prot_gen.strftime('%d') +'/'+ "%s" % pratica.data_prot_gen.strftime('%m')+'/'+"%s" % pratica.data_prot_gen.strftime('%Y')


            oggetto_lettera = preambolo

            # if pratica.street :

            #     ubicazione = ' Istanza di Permesso di Costruire presentata da  ' + soggetto.cognome + ' ' + soggetto.nome
            #     housenumber = pratica.housenumber

            p0_1 = document.add_paragraph()
            p0_1.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p0_1.paragraph_format.space_before = Pt(20)
            p0_1.paragraph_format.space_after = Pt(1)
            p0_1.add_run('RICHIESTA ATTI ISTRUTTORI E/O PARERI',style = 'CertificaStyle')


            p2_4 = document.add_paragraph()
            p2_4.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p2_4.paragraph_format.space_before = Pt(10)
            p2_4.add_run(str('Oggetto : ') , style='NumCduStyleItalic').bold=True
            # p2_4 = document.add_paragraph()
            # p2_4.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p2_4.paragraph_format.space_after = Pt(4)
            p2_4.add_run(str(oggetto_lettera )+' su immobile distinto in catatsto al ', style='NumCduStyleItalic').bold=True
            p2_4.add_run((lista), style='NumCduStyleItalic').bold=True

            ####################################
            #      DITTA
            ###################################
            # recupera il primo richiedente (Q(status='on-sale') | Q(status='paused'))
            rich = Anaprat.objects.filter(Q(pratica_id=pratica.id) & Q(tipo_id=1)).order_by('id')[0]
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

            p001 = document.add_paragraph()
            p001.paragraph_format.left_indent = Inches(0.5)
            p001_text = str.title(soggetto.cognome) + ' ' + str.title(soggetto.nome)
            p001.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p001.paragraph_format.space_after = Pt(4)
            p001.add_run(str('DITTA : ' + p001_text ) , style='NumCduStyleItalic')
            ####################################
            #      RICHIEDENTE
            ###################################
            p002 = document.add_paragraph()
            p002.paragraph_format.left_indent = Inches(0.5)

            p002_text = str.upper(soggetto.cognome) + ' ' + str.title(soggetto.nome)
            p002.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p002.paragraph_format.space_after = Pt(12)
            p002.add_run(str('Rif. Pratica: Prot. Gen. ' + str(pratica.prot_gen + ' del ' + "%s" % pratica.data_prot_gen.strftime('%d') +'/'+ "%s" % pratica.data_prot_gen.strftime('%m')+'/'+"%s" % pratica.data_prot_gen.strftime('%Y')) + ' - Prot. SUAP n. '+ str(pratica.code_p) +'/'+"%s" % pratica.data_prot_gen.strftime('%Y') ) , style='NumCduStyleItalic')

            par_1 = document.add_paragraph()
            par_1.paragraph_format.first_line_indent = Inches(0.3)
            # par_1 = paragraph_format.left_indent = Inches(0.5)
            par_1.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW

            par_1.paragraph_format.space_before = Pt(1)
            par_1.paragraph_format.space_after = Pt(4)
            par_1.add_run()
            par_1.add_run(('''La Ditta in oggetto ha presentato a questo Sportello Unico domanda di autorizzazione alla '''), style='NormalStyle')
            par_1.add_run(str(pratica.oggetto), style='NormalStyle')
            par_1.add_run((' da posizionarsi in Carrara, ' + ubicazione), style='NormalStyle' )
            par_1.add_run((', su immobile distinto in catasto al ') , style='NormalStyle' )
            par_1.add_run((lista) , style='NormalStyle' )
            par_1.add_run(('.') , style='NormalStyle' )

            par_2 = document.add_paragraph()
            par_2.paragraph_format.first_line_indent = Inches(0.3)
            # par_1 = paragraph_format.left_indent = Inches(0.5)
            par_2.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_2.paragraph_format.space_before = Pt(1)
            par_2.paragraph_format.space_after = Pt(4)
            par_2.add_run()
            par_2.add_run(('''Considerato che il procedimento dovrà concludersi entro il termine di sessanta giorni\
dalla data di presentazione della pratica a questo sportello, salvo richiesta di integrazioni o chiarimenti da parte degli enti o uffici coinvolti\
negli endoprocedimenti, che dovranno essere comunicati alla scrivente struttura, si trasmette copia della documentazione\
prodotta dalla ditta, al fine di poter esprimere il parere di competenza in tempo utile per poter ottemperare a quanto previsto dalla normativa.'''), style='NormalStyle')

            par_3 = document.add_paragraph()
            par_3.paragraph_format.first_line_indent = Inches(0.3)
            # par_1 = paragraph_format.left_indent = Inches(0.5)
            par_3.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_3.paragraph_format.space_before = Pt(1)
            par_3.paragraph_format.space_after = Pt(4)
            par_3.add_run()
            par_3.add_run(('Distinti saluti'), style='NormalStyle')

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
            par_8_4.add_run('Il Responsabile', style='NormalStyle' )

            par_8_5 = document.add_paragraph()
            par_8_5.paragraph_format.space_before = Pt(1)
            par_8_5.paragraph_format.space_after = Pt(1)
            par_8_5.alignement = WD_ALIGN_PARAGRAPH.CENTER
            par_8_5.paragraph_format.first_line_indent = Inches(4.2)
            par_8_5.add_run('Dott.ssa Michela Parisi', style='NormalStyle' )


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


########################################################
##### RESOCONTO CALCOLO VALORE DIRITTO DI SUPERFICIE ###
########################################################
def DirSupCalc(request):

        id = request.session.get('pk')
        print('id',id)
        pratica = Pratica.objects.get(id=id) # ritorna  i dati pratica
        print (pratica)
        print('tipo',pratica.tipo_pratica)

        if pratica.tipo_pratica_id == 36 : # Diritto di superficie
            print('diritto di superficie')

            atto = 'dir_sup_' +str(pratica.tipo_pratica) + '_' +  str(pratica.prot_gen) +'_' + "%s" % pratica.data_prot_gen.strftime('%Y%m%d') +'.docx'

            document = Document()
            # imposta A4 verticale e margini
            section = document.sections[0]
            section.page_height = Mm(297)
            section.page_width = Mm(210)
            section.left_margin = Mm(20)
            section.right_margin = Mm(20)
            section.top_margin = Mm(10)
            section.bottom_margin = Mm(8)
            # section.header_distance = Mm(10)
            section.footer_distance = Mm(10)

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
            f1.add_run("Settore 6 - Governo del territorio  - P.za due giugno,1 54033 - Carrara (MS)", style = 'FooterStyle')

            f2=footer.add_paragraph()
            f2.paragraph_format.space_after = Pt(0)
            f2.paragraph_format.space_before = Pt(0)
            # f2.add_run("dott.ssa Michela Parisi - 0585 641496 - michela.parisi@comune.carrara.ms.it", style = 'FooterStyle')

            f3=footer.add_paragraph()
            f3.paragraph_format.space_after = Pt(0)
            f3.paragraph_format.space_before = Pt(0)
            # f3.add_run("geom. Valerio Vinchesi - 0585 641291 - valerio.vinchesi@comune.carrara.ms.it", style = 'FooterStyle')

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
            obj_font.size = Pt(11)
            obj_font.name = 'Arial'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('HeaderStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(8)
            obj_font.name = 'Arial'

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
            obj_charstyle = obj_styles.add_style('NumCduStyleItalic', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = True
            obj_font.size = Pt(9)
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

            paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW

            docx_title=atto

            # Inserisci l'immagine nel documento
            # https://www.shibutan-bloomers.com/python_library_python-docx-2_en/7091/

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
            p0.add_run('Settore 6 - GOVERNO DEL TERRITORIO',style = 'FooterStyle')




        # #    stampo i dati della U.O.

            p1 = document.add_paragraph()
            p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
            #p1.add_run('Servizio 7.2 SUAP, demanio e paesaggio - U.O. 7.4 S.U.A.P.',style = 'FooterStyle')





            # recupera i dati della pratica
            pratica = Pratica.objects.get(id=pratica.id)



            # # recupera TUTTI i richiedenti

            all_rich = Anaprat.objects.filter(pratica_id=pratica.id)
            print('richiedenti', all_rich)
            for a in all_rich:
                soggetto=Soggetto.objects.get(id=a.soggetto_id)



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
                                mappali = 'Foglio ' + part.foglio + ' map ' + part.mappale
                                if p.subalterno !='-':
                                      mappali = mappali + ' sub '+str(p.subalterno)+', '
                            foglio_pre= part.foglio
                            lista.append(mappali)
                    print(lista, foglio_pre, part.foglio)
                    #document.add_paragraph(lista)
            else:
                    prot = pratica.prot_gen
                    data = pratica.data_prot_gen

            ####################################
            #      OGGETTO
            ###################################
            if pratica.tipo_pratica_id == 12:
                preambolo='Comunicazione di avvio del procedimento della pratica \
finalizzata al rilascio di autorizzazione all\' installazione di insegne di esercizio permanenti'

            elif pratica.tipo_pratica_id == 19:
                preambolo='Comunicazione di avvio del procedimento della pratica \
finalizzata al rilascio di autorizzazione alla '
            else:
                preambolo =''

            oggetto_lettera = preambolo
            # oggetto_lettera = pratica.oggetto

            if pratica.street :
                ubicazione = ', su immobile ubicato in Carrara '
                housenumber = pratica.housenumber

                if housenumber :
                    oggetto_lettera = oggetto_lettera +' '+ str(pratica.oggetto) + ubicazione + str(pratica.street) + ' ' + str(pratica.housenumber)
                else:
                                        oggetto_lettera = oggetto_lettera + ubicazione + str(pratica.street).title()




            p2_4 = document.add_paragraph()
            p2_4.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p2_4.paragraph_format.space_before = Pt(30)
            p2_4.add_run(str('Oggetto : ') , style='NumCduStyleItalic').bold=True
            # p2_4 = document.add_paragraph()
            # p2_4.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p2_4.paragraph_format.space_after = Pt(4)
            p2_4.add_run(str(oggetto_lettera ), style='NumCduStyleItalic')
            if lista:
                p2_4.add_run(', distinto in catasto al ', style='NumCduStyleItalic')
                p2_4.add_run(lista, style='NumCduStyleItalic')
            else:
                pass
            ####################################
            #      DITTA
            ###################################
            # recupera il primo richiedente (Q(status='on-sale') | Q(status='paused'))
            rich = Anaprat.objects.filter(Q(pratica_id=pratica.id) & Q(tipo_id=1)).order_by('id')[0]
            print('richiedenti', rich)
            soggetto = Soggetto.objects.get(id=rich.soggetto_id)
            # verifico che esista il codice fiscale
            if soggetto.codice_fiscale:
                # verifico se maschio o femmina
                sesso_cf = soggetto.codice_fiscale[6:8]
                if type(sesso_cf) is int:
                    print('sesso_cf',sesso_cf)
                    if int(sesso_cf)>40:
                        nascita =' nata a ' + soggetto.comune_nascita.title() + ' il ' + str(soggetto.data_nascita)
                    else:
                        nascita =' nato a ' + soggetto.comune_nascita.title() + ' il ' + str(soggetto.data_nascita)
                        print('sesso_cf', sesso_cf)
            prot = pratica.prot_gen
            data = pratica.data_prot_gen

            p001 = document.add_paragraph()
            p001.paragraph_format.left_indent = Inches(0.5)
            p001_text = str.title(soggetto.cognome) + ' ' + str.title(soggetto.nome)
            p001.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p001.paragraph_format.space_after = Pt(4)
            p001.add_run(str('DITTA : ' + p001_text ) , style='NumCduStyleItalic')
            ####################################
            #      RICHIEDENTE
            ###################################
            p002 = document.add_paragraph()
            p002.paragraph_format.left_indent = Inches(0.5)

            p002_text = str.upper(soggetto.cognome) + ' ' + str.title(soggetto.nome)
            p002.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p002.paragraph_format.space_after = Pt(12)
            p002.add_run(str('Rif. Pratica: Prot. Gen. ' + str(pratica.prot_gen + ' del ' + "%s" % pratica.data_prot_gen.strftime('%d') +'/'+ "%s" % pratica.data_prot_gen.strftime('%m')+'/'+"%s" % pratica.data_prot_gen.strftime('%Y')) ) , style='NumCduStyleItalic')

            ####################################
            #      PARAGRAFO NormalStyle
            ###################################

            par_1 = document.add_paragraph()
            par_1.paragraph_format.first_line_indent = Inches(0.3)
            # par_1 = paragraph_format.left_indent = Inches(0.5)
            par_1.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW

            par_1.paragraph_format.space_before = Pt(1)
            par_1.paragraph_format.space_after = Pt(4)
            par_1.add_run()
            par_1.add_run(('Con riferimento alla pratica pervenuta con Prot.Gen. n° ' ), style='NormalStyle')
            par_1.add_run(str(pratica.prot_gen), style='NormalStyle').bold=True
            par_1.add_run((' del '), style='NormalStyle' )
            par_1.add_run("%s" % data.strftime('%d/%m/%Y'), style='NormalStyle').bold=True
            par_1.add_run(''', si comunica ai sensi e per gli effetti degli art. 7, 8 della legge 7 Agosto 1990, \
n° 241 e s.m.i., che questo Ufficio ha dato avvio al procedimento. La pratica è di competenza dello Sportello Unico \
per le Attività Produttive del Comune di Carrara, Piazza 2 Giugno 1, presso il quale codesta società potrà prendere \
visione degli atti.''', style='NormalStyle' )
            RUP = 'dott.ssa Michela Parisi'
            ISTRUTTORE = 'geom. Valerio Vinchesi'
            par_3 = document.add_paragraph()
            par_3.paragraph_format.space_before = Pt(1)
            par_3.paragraph_format.space_after = Pt(1)
            par_3.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_3.add_run('Responsabile del procedimento : ', style='NormalStyle' ).bold=True
            par_3.add_run(str(RUP), style='NormalStyle' ).italic=True
            par_3_1 = document.add_paragraph()
            par_3_1.paragraph_format.space_before = Pt(1)
            par_3_1.paragraph_format.space_after = Pt(4)
            par_3_1.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_3_1.add_run('Istruttore tecnico : ', style='NormalStyle' ).bold=True
            par_3_1.add_run(str(ISTRUTTORE), style='NormalStyle' ).italic=True

            par_4 = document.add_paragraph()
            par_4.paragraph_format.first_line_indent = Inches(0.3)
            par_4.paragraph_format.space_before = Pt(1)
            par_4.paragraph_format.space_after = Pt(1)
            par_4.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_4.add_run('''Il procedimento dovrà concludersi entro 60 giorni dal ricevimento della documentazione.\
 Si informa che la pratica, regolare e completa, sarà inviata agli enti competenti al rilascio dei pareri/atti istruttori di competenza.''', style='NormalStyle' )

            par_4_2 = document.add_paragraph()
            par_4_2.paragraph_format.first_line_indent = Inches(0.3)
            par_4_2.paragraph_format.space_before = Pt(1)
            par_4_2.paragraph_format.space_after = Pt(1)
            par_4_2.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_4_2.add_run('''I termini del procedimento potranno essere sospesi nel caso in cui gli uffici comunali \
o gli enti titolari degli endoprocedimenti richiedano l’integrazione degli atti o dei documenti ai fini istruttori.\
In tal caso i termini del procedimento riprenderanno a decorrere del momento della presentazione della documentazione richiesta. \
Tutte le eventuali documentazioni integrative richieste dagli enti interessati e/o uffici comunali \
dovranno essere presentati tramite questo Sportello.''', style='NormalStyle' )

            # par_4_4 = document.add_paragraph()
            # par_4_4.paragraph_format.space_before = Pt(1)
            # par_4_4.paragraph_format.space_after = Pt(1)
            # par_4_4.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            # par_4_4.add_run('Tutte le eventuali documentazioni integrative richieste dagli enti interessati e/o uffici comunali dovranno essere presentati tramite questo Sportello.', style='NormalStyle' )


            par_5 = document.add_paragraph()
            par_5.paragraph_format.first_line_indent = Inches(0.3)
            par_5.paragraph_format.space_before = Pt(1)
            par_5.paragraph_format.space_after = Pt(4)
            par_5.alignement = WD_ALIGN_PARAGRAPH.LEFT
            par_5.add_run('''Ai sensi di quanto stabilito dall’art. 28 della Legge 9 agosto 2013 n. 98 la Pubblica Amministrazione procedente o, in caso di procedimenti in cui intervengono più amministrazioni, \
quella responsabile del ritardo ed i soggetti privati preposti all\'esercizio di attività amministrative, di cui all’art. 1, comma 1-ter, della legge 7 agosto 1990, n. 241, corrispondono all’interessato, \
a titolo di indennizzo per il mero ritardo, una somma pari a 30 euro per ogni giorno di ritardo, con decorrenza dalla data di scadenza del termine del procedimento,
comunque complessivamente non superiore a 2.000 euro. ''', style='NormalStyle' )

            par_6 = document.add_paragraph()
            par_6.paragraph_format.first_line_indent = Inches(0.3)
            par_6.paragraph_format.space_before = Pt(1)
            par_6.paragraph_format.space_after = Pt(1)
            par_6.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_6.add_run('Al fine di ottenere l’indennizzo, l’istante è tenuto ad azionare il potere sostitutivo previsto ', style='NormalStyle' )
            par_6.add_run('dall’art. 2, comma 9-bis, della legge n. 241 del 1990 nel termine perentorio di ', style='NormalStyle' )
            par_6.add_run('venti giorni dalla scadenza del termine di conclusione del procedimento. ', style='NormalStyle' )

            par_6_1 = document.add_paragraph()
            # par_6_1.paragraph_format.first_line_indent = Inches(0.3)
            par_6_1.paragraph_format.space_before = Pt(1)
            par_6_1.paragraph_format.space_after = Pt(1)
            par_6_1.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_6_1.add_run('Nel caso di procedimenti in cui intervengono più amministrazioni, l’interessato ', style='NormalStyle' )
            par_6_1.add_run('presenta istanza all’amministrazione procedente, che la trasmette tempestivamente ', style='NormalStyle' )
            par_6_1.add_run('al titolare del potere sostitutivo dell’amministrazione responsabile del ritardo.', style='NormalStyle' )

            par_7 = document.add_paragraph()
            par_7.paragraph_format.first_line_indent = Inches(0.3)
            par_7.paragraph_format.space_before = Pt(1)
            par_7.paragraph_format.space_after = Pt(1)
            par_7.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_7.add_run('Nel caso in cui anche il titolare del potere sostitutivo non emani il provvedimento ', style='NormalStyle' )
            par_7.add_run('entro un termine pari alla metà di quello originariamente previsto (30 giorni) o non liquidi ', style='NormalStyle' )
            par_7.add_run('l’indennizzo maturato fino alla data della medesima liquidazione, l’istante può proporre ricorso ', style='NormalStyle' )
            par_7.add_run('ai sensi dell’articolo 117 del codice del processo amministrativo di cui ', style='NormalStyle' )
            par_7.add_run('all’Allegato 1 al D.Lgs. 2 luglio 2010 n. 104, e successive modificazioni, oppure, ricorrendone i presupposti, ', style='NormalStyle' )
            par_7.add_run('dell’articolo 118 dello stesso codice. ', style='NormalStyle' )

            par_7_1 = document.add_paragraph()
            # par_7_1.paragraph_format.first_line_indent = Inches(0.3)
            par_7_1.paragraph_format.space_before = Pt(1)
            par_7_1.paragraph_format.space_after = Pt(1)
            par_7_1.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_7_1.add_run('Il soggetto cui è attribuito il potere sostitutivo è il Segretario Generale del Comune di Carrara.', style='NormalStyle' )

            par_8 = document.add_paragraph()
            # par_8.paragraph_format.first_line_indent = Inches(0.3)
            par_8.paragraph_format.space_before = Pt(1)
            par_8.paragraph_format.space_after = Pt(1)
            par_8.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_8.add_run('Si informa, infine, che, in relazione al procedimento attivato, lo SUAP provvede direttamente alla riscossione \
delle spese e dei diritti istruttori di competenza delle varie amministrazioni coinvolte. \
Questo Sportello si riserva pertanto di comunicare l’importo e le modalità di versamento.', style='NormalStyle' )


            par_8_1 = document.add_paragraph()
            # par_8_1.paragraph_format.first_line_indent = Inches(0.3)
            par_8_1.paragraph_format.space_before = Pt(1)
            par_8_1.paragraph_format.space_after = Pt(1)
            par_8_1.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_8_1.add_run('Per integrazioni e/o comunicazioni relative all’oggetto dell’istanza, la S.V. è pregata di citare il numero di ', style='NormalStyle' )

            par_8_1.add_run(str(pratica.tipo_pratica)+'-', style='NormalStyle' ).bold=True
            par_8_1.add_run(str(pratica.prot_gen)+'-' , style='NormalStyle' ).bold=True
            par_8_1.add_run("%s" % data.strftime('%Y'), style='NormalStyle').bold=True

            par_8_2 = document.add_paragraph()
            # par_8_2.paragraph_format.first_line_indent = Inches(0.3)
            par_8_2.paragraph_format.space_before = Pt(1)
            par_8_2.paragraph_format.space_after = Pt(1)
            par_8_2.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_8_2.add_run('Cordiali saluti', style='NormalStyle' )

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
            par_8_4.add_run('Il Dirigente ad interim', style='NormalStyle' )

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


#######################################################
##### RISPOSTA VVFF ########
########################################################
def Risposta_vvff(request):

        id = request.session.get('pk')
        print('id',id)
        pratica = Pratica.objects.get(id=id) # ritorna  i dati pratica
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
            f1.add_run("P.za due giugno,1 54033 - Carrara (MS)", style = 'FooterStyle')

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
            print('richiedenti', all_rich)
            for a in all_rich:
                soggetto=Soggetto.objects.get(id=a.soggetto_id)

                 #inserisce POLIZIA MUNICIPALE
                # p2 = document.add_paragraph()
                # p2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                # p2.paragraph_format.space_after = Pt(3)
                # p2.add_run('Spett.Le Polizia Municipale ' , style='NumCduStyle').bold=True

                # p2_0 = document.add_paragraph()
                # p2_0.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                # p2_0.paragraph_format.space_after = Pt(3)
                # p2_0.add_run('Comune di Carrara ' , style='NumCduStyle').bold=True

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
                                mappali = 'fg ' + part.foglio + ' map ' + part.mappale
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
            rich = Anaprat.objects.filter(Q(pratica_id=pratica.id) & Q(tipo_id=1)).order_by('id')[0]
            # recuperea il tecnico istruttore
            '''
            istr_tec = Anaprat.objects.get(Q(pratica_id=pratica.id) & Q(tipo_id=3))
            '''
            '''
            s_istr_tec = Soggetto.objects.get(id=istr_tec.soggetto_id)
            '''
            print('richiedenti', rich)
            soggetto = Soggetto.objects.get(id=rich.soggetto_id)
            # verifico che esista il codice fiscale
            if soggetto.codice_fiscale:
                # verifico se maschio o femmina
                sesso_cf = soggetto.codice_fiscale[6:8]
                if type(sesso_cf) is int:
                    if int(sesso_cf)>40:
                        nascita =' nata a ' + soggetto.comune_nascita.title() + ' il ' + str(soggetto.data_nascita)
                    else:
                        nascita =' nato a ' + soggetto.comune_nascita.title() + ' il ' + str(soggetto.data_nascita)
                        print('sesso_cf', sesso_cf)
            else:
                nascita = ''
            prot = pratica.prot_gen
            data = pratica.data_prot_gen

            if pratica.housenumber :
                ubicazione=str(pratica.street) + ' ' + str(pratica.housenumber)
            else:
                ubicazione =  str(pratica.street).title()


            ####################################
            #      OGGETTO
            ###################################

            if ubicazione != '':
                preambolo='Comunicazione del Comando VV.FF. del ' + "%s" % pratica.data_prot_gen.strftime('%d') +'/'+ "%s" % pratica.data_prot_gen.strftime('%m')+'/'+"%s" % pratica.data_prot_gen.strftime('%Y') +  ' Prot. Gen ' + str(pratica.prot_gen)
                pre_oggetto = str(pratica.oggetto) + ' ' + str(ubicazione)
#soggetto.cognome + ' ' + soggetto.nome + ' Prot. Gen. n. ' + pratica.prot_gen + ' del ' + "%s" % pratica.data_prot_gen.strftime('%d') +'/'+ "%s" % pratica.data_prot_gen.strftime('%m')+'/'+"%s" % pratica.data_prot_gen.strftime('%Y')


            oggetto_lettera = preambolo



            p2_4 = document.add_paragraph()
            p2_4.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p2_4.paragraph_format.space_before = Pt(50)
            p2_4.add_run(str('Oggetto : ') , style='NumCduStyleItalic').bold=True
            # p2_4 = document.add_paragraph()
            # p2_4.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p2_4.paragraph_format.space_after = Pt(4)
            p2_4.add_run(str(oggetto_lettera )+' ', style='NumCduStyleItalic').bold=True
            p2_4.add_run((lista), style='NumCduStyleItalic').bold=True

            p2_4_1 = document.add_paragraph()
            p2_4_1.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p2_4_1.paragraph_format.left_indent = Inches(0.5)
            p2_4_1.add_run(str(pre_oggetto), style='HeaderStyle')


            ####################################
            #      DITTA
            ###################################
            # recupera il primo richiedente (Q(status='on-sale') | Q(status='paused'))
            rich = Anaprat.objects.filter(Q(pratica_id=pratica.id) & Q(tipo_id=1)).order_by('id')[0]
            print('richiedenti', rich)
            soggetto = Soggetto.objects.get(id=rich.soggetto_id)
             # verifico che esista il codice fiscale
            if soggetto.codice_fiscale:

                # verifico se maschio o femmina
                sesso_cf = soggetto.codice_fiscale[6:8]
                if type(sesso_cf) is int:
                    if int(sesso_cf)>40:
                        nascita =' nata a ' + soggetto.comune_nascita.title() + ' il ' + str(soggetto.data_nascita)
                    else:
                        nascita =' nato a ' + soggetto.comune_nascita.title() + ' il ' + str(soggetto.data_nascita)
                        print('sesso_cf', sesso_cf)
            else:
                nascita=''
            prot = pratica.prot_gen
            data = pratica.data_prot_gen


            p2_5 = document.add_paragraph()
            p2_5.paragraph_format.first_line_indent = Inches(0.5)
            p2_5.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY
            p2_5.paragraph_format.space_before = Pt(1)
            p2_5.paragraph_format.space_after = Pt(4)
            p2_5.add_run(str('''Con riferimento a quanto in oggetto, come già segnalato con precedenti note relativamente \
alle Vs comunicazioni inerenti gli impianti Fuori Servizio, si rappresenta che per l'adozione dei provvedimenti di competenza \
è necessario che codesto comando indichi, nelle comunicazioni di segnalazione, oltre all'indirizzo dell'immobile oggetto di intervento \
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



########################################################
##### RICHIESTA INTEGRAZIONE DOCUMENTALE ASCENSORE ###
########################################################
def IntegraAscensore(request):


        id = request.session.get('pk')
        print('id',id)
        pratica = Pratica.objects.get(id=id) # ritorna  i dati pratica
        print (pratica)
        print('tipo',pratica.tipo_pratica)

        if pratica.tipo_pratica_id == 38 : # Ascensore
            print('matricola ascensore')

            atto = 'ascensore_integra_' +str(pratica.tipo_pratica) + '_' +  str(pratica.prot_gen) +'_' + "%s" % pratica.data_prot_gen.strftime('%Y%m%d') +'.docx'

            document = Document()
            # imposta A4 verticale e margini
            section = document.sections[0]
            section.page_height = Mm(297)
            section.page_width = Mm(210)
            section.left_margin = Mm(20)
            section.right_margin = Mm(20)
            section.top_margin = Mm(10)
            section.bottom_margin = Mm(8)
            # section.header_distance = Mm(10)
            section.footer_distance = Mm(10)

            paragraph = document.add_paragraph()
            # Selecting a section of the document

            section = document.sections[0]
            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('FooterStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(8)
            obj_font.name = 'Arial'

        #   IMPOSTA IL FOOTER
            footer=section.footer

            f1=footer.add_paragraph()
            f1.paragraph_format.space_after = Pt(0)
            f1.paragraph_format.space_before = Pt(0)
            f1.add_run("Settore 6 - Governo del territorio  - P.za due giugno,1 54033 - Carrara (MS)", style = 'FooterStyle')

            f2=footer.add_paragraph()
            f2.paragraph_format.space_after = Pt(0)
            f2.paragraph_format.space_before = Pt(0)
            # f2.add_run("dott.ssa Michela Parisi - 0585 641496 - michela.parisi@comune.carrara.ms.it", style = 'FooterStyle')

            f3=footer.add_paragraph()
            f3.paragraph_format.space_after = Pt(0)
            f3.paragraph_format.space_before = Pt(0)
            # f3.add_run("geom. Valerio Vinchesi - 0585 641291 - valerio.vinchesi@comune.carrara.ms.it", style = 'FooterStyle')

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
            obj_font.size = Pt(11)
            obj_font.name = 'Arial'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('HeaderStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(8)
            obj_font.name = 'Arial'

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
            obj_charstyle = obj_styles.add_style('NumCduStyleItalic', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = True
            obj_font.size = Pt(9)
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

            # Inserisci l'immagine nel documento
            # https://www.shibutan-bloomers.com/python_library_python-docx-2_en/7091/

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
            p0.add_run('Settore 6 - GOVERNO DEL TERRITORIO',style = 'FooterStyle')




        # #    stampo i dati della U.O.

            p1 = document.add_paragraph()
            p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
            #p1.add_run('Servizio 7.2 SUAP, demanio e paesaggio - U.O. 7.4 S.U.A.P.',style = 'FooterStyle')





            # recupera i dati della pratica
            pratica = Pratica.objects.get(id=pratica.id)



            # # recupera TUTTI i richiedenti

            all_rich = Anaprat.objects.filter(pratica_id=pratica.id)
            print('richiedenti', all_rich)
            for a in all_rich:
                soggetto=Soggetto.objects.get(id=a.soggetto_id)



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
                                mappali = 'Foglio ' + part.foglio + ' map ' + part.mappale
                                if p.subalterno !='-':
                                      mappali = mappali + ' sub '+str(p.subalterno)+', '
                            foglio_pre= part.foglio
                            lista.append(mappali)
                    print(lista, foglio_pre, part.foglio)
                    #document.add_paragraph(lista)
            else:
                    prot = pratica.prot_gen
                    data = pratica.data_prot_gen

            ####################################
            #      OGGETTO
            ###################################
            if pratica.tipo_pratica_id == 12:
                preambolo='Comunicazione di avvio del procedimento della pratica \
finalizzata al rilascio di autorizzazione all\' installazione di insegne di esercizio permanenti'

            elif pratica.tipo_pratica_id == 19:
                preambolo='Comunicazione di avvio del procedimento della pratica \
finalizzata al rilascio di autorizzazione alla '
            else:
                preambolo =''

            oggetto_lettera = preambolo
            # oggetto_lettera = pratica.oggetto

            if pratica.street :
                ubicazione = ', su immobile ubicato in Carrara '
                housenumber = pratica.housenumber

                if housenumber :
                    oggetto_lettera = oggetto_lettera +' '+ str(pratica.oggetto) + ubicazione + str(pratica.street) + ' ' + str(pratica.housenumber)
                else:
                                        oggetto_lettera = oggetto_lettera + ubicazione + str(pratica.street).title()




            p2_4 = document.add_paragraph()
            p2_4.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p2_4.paragraph_format.space_before = Pt(30)
            p2_4.add_run(str('Oggetto : ') , style='NumCduStyleItalic').bold=True
            # p2_4 = document.add_paragraph()
            # p2_4.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p2_4.paragraph_format.space_after = Pt(4)
            p2_4.add_run(str(oggetto_lettera ), style='NumCduStyleItalic')
            if lista:
                p2_4.add_run(', distinto in catasto al ', style='NumCduStyleItalic')
                p2_4.add_run(lista, style='NumCduStyleItalic')
            else:
                pass
            ####################################
            #      DITTA
            ###################################
            # recupera il primo richiedente (Q(status='on-sale') | Q(status='paused'))
            rich = Anaprat.objects.filter(Q(pratica_id=pratica.id) & Q(tipo_id=1)).order_by('id')[0]
            print('richiedenti', rich)
            soggetto = Soggetto.objects.get(id=rich.soggetto_id)
            # verifico che esista il codice fiscale
            if soggetto.codice_fiscale:
                # verifico se maschio o femmina
                sesso_cf = soggetto.codice_fiscale[6:8]
                if type(sesso_cf) is int:
                    print('sesso_cf',sesso_cf)
                    if int(sesso_cf)>40:
                        nascita =' nata a ' + soggetto.comune_nascita.title() + ' il ' + str(soggetto.data_nascita)
                    else:
                        nascita =' nato a ' + soggetto.comune_nascita.title() + ' il ' + str(soggetto.data_nascita)
                        print('sesso_cf', sesso_cf)
            prot = pratica.prot_gen
            data = pratica.data_prot_gen

            p001 = document.add_paragraph()
            p001.paragraph_format.left_indent = Inches(0.5)
            p001_text = str.title(soggetto.cognome) + ' ' + str.title(soggetto.nome)
            p001.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p001.paragraph_format.space_after = Pt(4)
            p001.add_run(str('DITTA : ' + p001_text ) , style='NumCduStyleItalic')
            ####################################
            #      RICHIEDENTE
            ###################################
            p002 = document.add_paragraph()
            p002.paragraph_format.left_indent = Inches(0.5)

            p002_text = str.upper(soggetto.cognome) + ' ' + str.title(soggetto.nome)
            p002.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p002.paragraph_format.space_after = Pt(12)
            p002.add_run(str('Rif. Pratica: Prot. Gen. ' + str(pratica.prot_gen + ' del ' + "%s" % pratica.data_prot_gen.strftime('%d') +'/'+ "%s" % pratica.data_prot_gen.strftime('%m')+'/'+"%s" % pratica.data_prot_gen.strftime('%Y')) ) , style='NumCduStyleItalic')

            ####################################
            #      PARAGRAFO NormalStyle
            ###################################

            par_1 = document.add_paragraph()
            par_1.paragraph_format.first_line_indent = Inches(0.3)
            # par_1 = paragraph_format.left_indent = Inches(0.5)
            par_1.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW

            par_1.paragraph_format.space_before = Pt(1)
            par_1.paragraph_format.space_after = Pt(4)
            par_1.add_run()
            par_1.add_run(('Con riferimento alla pratica pervenuta con Prot.Gen. n° ' ), style='NormalStyle')
            par_1.add_run(str(pratica.prot_gen), style='NormalStyle').bold=True
            par_1.add_run((' del '), style='NormalStyle' )
            par_1.add_run("%s" % data.strftime('%d/%m/%Y'), style='NormalStyle').bold=True
            par_1.add_run(''', si comunica ai sensi e per gli effetti degli art. 7, 8 della legge 7 Agosto 1990, \
n° 241 e s.m.i., che questo Ufficio ha dato avvio al procedimento. La pratica è di competenza dello Sportello Unico \
per le Attività Produttive del Comune di Carrara, Piazza 2 Giugno 1, presso il quale codesta società potrà prendere \
visione degli atti.''', style='NormalStyle' )
            RUP = 'dott.ssa Michela Parisi'
            ISTRUTTORE = 'geom. Valerio Vinchesi'
            par_3 = document.add_paragraph()
            par_3.paragraph_format.space_before = Pt(1)
            par_3.paragraph_format.space_after = Pt(1)
            par_3.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_3.add_run('Responsabile del procedimento : ', style='NormalStyle' ).bold=True
            par_3.add_run(str(RUP), style='NormalStyle' ).italic=True
            par_3_1 = document.add_paragraph()
            par_3_1.paragraph_format.space_before = Pt(1)
            par_3_1.paragraph_format.space_after = Pt(4)
            par_3_1.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_3_1.add_run('Istruttore tecnico : ', style='NormalStyle' ).bold=True
            par_3_1.add_run(str(ISTRUTTORE), style='NormalStyle' ).italic=True

            par_4 = document.add_paragraph()
            par_4.paragraph_format.first_line_indent = Inches(0.3)
            par_4.paragraph_format.space_before = Pt(1)
            par_4.paragraph_format.space_after = Pt(1)
            par_4.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_4.add_run('''Il procedimento dovrà concludersi entro 60 giorni dal ricevimento della documentazione.\
 Si informa che la pratica, regolare e completa, sarà inviata agli enti competenti al rilascio dei pareri/atti istruttori di competenza.''', style='NormalStyle' )

            par_4_2 = document.add_paragraph()
            par_4_2.paragraph_format.first_line_indent = Inches(0.3)
            par_4_2.paragraph_format.space_before = Pt(1)
            par_4_2.paragraph_format.space_after = Pt(1)
            par_4_2.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_4_2.add_run('''I termini del procedimento potranno essere sospesi nel caso in cui gli uffici comunali \
o gli enti titolari degli endoprocedimenti richiedano l’integrazione degli atti o dei documenti ai fini istruttori.\
In tal caso i termini del procedimento riprenderanno a decorrere del momento della presentazione della documentazione richiesta. \
Tutte le eventuali documentazioni integrative richieste dagli enti interessati e/o uffici comunali \
dovranno essere presentati tramite questo Sportello.''', style='NormalStyle' )

            # par_4_4 = document.add_paragraph()
            # par_4_4.paragraph_format.space_before = Pt(1)
            # par_4_4.paragraph_format.space_after = Pt(1)
            # par_4_4.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            # par_4_4.add_run('Tutte le eventuali documentazioni integrative richieste dagli enti interessati e/o uffici comunali dovranno essere presentati tramite questo Sportello.', style='NormalStyle' )


            par_5 = document.add_paragraph()
            par_5.paragraph_format.first_line_indent = Inches(0.3)
            par_5.paragraph_format.space_before = Pt(1)
            par_5.paragraph_format.space_after = Pt(4)
            par_5.alignement = WD_ALIGN_PARAGRAPH.LEFT
            par_5.add_run('''Ai sensi di quanto stabilito dall’art. 28 della Legge 9 agosto 2013 n. 98 la Pubblica Amministrazione procedente o, in caso di procedimenti in cui intervengono più amministrazioni, \
quella responsabile del ritardo ed i soggetti privati preposti all\'esercizio di attività amministrative, di cui all’art. 1, comma 1-ter, della legge 7 agosto 1990, n. 241, corrispondono all’interessato, \
a titolo di indennizzo per il mero ritardo, una somma pari a 30 euro per ogni giorno di ritardo, con decorrenza dalla data di scadenza del termine del procedimento,
comunque complessivamente non superiore a 2.000 euro. ''', style='NormalStyle' )

            par_6 = document.add_paragraph()
            par_6.paragraph_format.first_line_indent = Inches(0.3)
            par_6.paragraph_format.space_before = Pt(1)
            par_6.paragraph_format.space_after = Pt(1)
            par_6.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_6.add_run('Al fine di ottenere l’indennizzo, l’istante è tenuto ad azionare il potere sostitutivo previsto ', style='NormalStyle' )
            par_6.add_run('dall’art. 2, comma 9-bis, della legge n. 241 del 1990 nel termine perentorio di ', style='NormalStyle' )
            par_6.add_run('venti giorni dalla scadenza del termine di conclusione del procedimento. ', style='NormalStyle' )

            par_6_1 = document.add_paragraph()
            # par_6_1.paragraph_format.first_line_indent = Inches(0.3)
            par_6_1.paragraph_format.space_before = Pt(1)
            par_6_1.paragraph_format.space_after = Pt(1)
            par_6_1.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_6_1.add_run('Nel caso di procedimenti in cui intervengono più amministrazioni, l’interessato ', style='NormalStyle' )
            par_6_1.add_run('presenta istanza all’amministrazione procedente, che la trasmette tempestivamente ', style='NormalStyle' )
            par_6_1.add_run('al titolare del potere sostitutivo dell’amministrazione responsabile del ritardo.', style='NormalStyle' )

            par_7 = document.add_paragraph()
            par_7.paragraph_format.first_line_indent = Inches(0.3)
            par_7.paragraph_format.space_before = Pt(1)
            par_7.paragraph_format.space_after = Pt(1)
            par_7.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_7.add_run('Nel caso in cui anche il titolare del potere sostitutivo non emani il provvedimento ', style='NormalStyle' )
            par_7.add_run('entro un termine pari alla metà di quello originariamente previsto (30 giorni) o non liquidi ', style='NormalStyle' )
            par_7.add_run('l’indennizzo maturato fino alla data della medesima liquidazione, l’istante può proporre ricorso ', style='NormalStyle' )
            par_7.add_run('ai sensi dell’articolo 117 del codice del processo amministrativo di cui ', style='NormalStyle' )
            par_7.add_run('all’Allegato 1 al D.Lgs. 2 luglio 2010 n. 104, e successive modificazioni, oppure, ricorrendone i presupposti, ', style='NormalStyle' )
            par_7.add_run('dell’articolo 118 dello stesso codice. ', style='NormalStyle' )

            par_7_1 = document.add_paragraph()
            # par_7_1.paragraph_format.first_line_indent = Inches(0.3)
            par_7_1.paragraph_format.space_before = Pt(1)
            par_7_1.paragraph_format.space_after = Pt(1)
            par_7_1.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_7_1.add_run('Il soggetto cui è attribuito il potere sostitutivo è il Segretario Generale del Comune di Carrara.', style='NormalStyle' )

            par_8 = document.add_paragraph()
            # par_8.paragraph_format.first_line_indent = Inches(0.3)
            par_8.paragraph_format.space_before = Pt(1)
            par_8.paragraph_format.space_after = Pt(1)
            par_8.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_8.add_run('Si informa, infine, che, in relazione al procedimento attivato, lo SUAP provvede direttamente alla riscossione \
delle spese e dei diritti istruttori di competenza delle varie amministrazioni coinvolte. \
Questo Sportello si riserva pertanto di comunicare l’importo e le modalità di versamento.', style='NormalStyle' )


            par_8_1 = document.add_paragraph()
            # par_8_1.paragraph_format.first_line_indent = Inches(0.3)
            par_8_1.paragraph_format.space_before = Pt(1)
            par_8_1.paragraph_format.space_after = Pt(1)
            par_8_1.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_8_1.add_run('Per integrazioni e/o comunicazioni relative all’oggetto dell’istanza, la S.V. è pregata di citare il numero di ', style='NormalStyle' )

            par_8_1.add_run(str(pratica.tipo_pratica)+'-', style='NormalStyle' ).bold=True
            par_8_1.add_run(str(pratica.prot_gen)+'-' , style='NormalStyle' ).bold=True
            par_8_1.add_run("%s" % data.strftime('%Y'), style='NormalStyle').bold=True

            par_8_2 = document.add_paragraph()
            # par_8_2.paragraph_format.first_line_indent = Inches(0.3)
            par_8_2.paragraph_format.space_before = Pt(1)
            par_8_2.paragraph_format.space_after = Pt(1)
            par_8_2.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_8_2.add_run('Cordiali saluti', style='NormalStyle' )

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
            par_8_4.add_run('Il Dirigente ad interim', style='NormalStyle' )

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
        


########################################################
##### AVVIO PROCEDIMENTO PDC ########
########################################################
def Integrazione(request, pk):

        id = pk
        print('id',id)
        pratica = Pratica.objects.get(id=id) # ritorna  i dati pratica
        print ('pratica',pratica)
        print('tipo',pratica.tipo_pratica)

        if pratica.tipo_pratica_id == 38 : # per ASCENSORE

            atto = 'richiesta_integrazione_' +str(pratica.tipo_pratica) + '_' +  str(pratica.prot_gen) +'_' + "%s" % pratica.data_prot_gen.strftime('%Y%m%d') +'.docx'

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

            # f1=footer.add_paragraph()
            # f1.paragraph_format.space_after = Pt(0)
            # f1.paragraph_format.space_before = Pt(0)
            # f1.add_run("Settore 6 - Governo del territorio - P.za due giugno,1 54033 - Carrara (MS)", style = 'FooterStyle')

            f2=footer.add_paragraph()
            f2.alignment = WD_ALIGN_PARAGRAPH.CENTER
            f2.paragraph_format.space_after = Pt(0)
            f2.paragraph_format.space_before = Pt(0)
            f2.add_run("Piazza due giugno, 1", style = 'FooterStyle')

            f3=footer.add_paragraph()
            f3.alignment = WD_ALIGN_PARAGRAPH.CENTER
            f3.paragraph_format.space_after = Pt(0)
            f3.paragraph_format.space_before = Pt(0)
            f3.add_run("54033 Carrara (MS)", style = 'FooterStyle')

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
            obj_charstyle = obj_styles.add_style('NormalStyleItalic', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = True

            obj_font.size = Pt(10)
            obj_font.name = 'Arial'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('SottoHeaderStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(11)
            obj_font.name = 'Arial'

            obj_styles = document.styles
            obj_charstyle = obj_styles.add_style('HeaderStyle', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.size = Pt(8)
            obj_font.name = 'Arial'

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
            obj_charstyle = obj_styles.add_style('NumCduStyleItalic', WD_STYLE_TYPE.CHARACTER)
            obj_font = obj_charstyle.font
            obj_font.italic = True
            obj_font.size = Pt(9)
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

            paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW

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
            p0.add_run('Settore 6 - GOVERNO DEL TERRITORIO',style = 'FooterStyle')




        # #    stampo i dati della U.O.

            # p1 = document.add_paragraph()
            # p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
            # p1.add_run('Servizio 7.2 SUAP, demanio e paesaggio - U.O. 7.4 S.U.A.P.',style = 'FooterStyle')





            # recupera i dati della pratica
            pratica = Pratica.objects.get(id=pratica.id)



            # # recupera TUTTI i richiedenti

            all_rich = Anaprat.objects.filter(pratica_id=pratica.id)
            print('richiedenti', all_rich)
            for a in all_rich:
                soggetto=Soggetto.objects.get(id=a.soggetto_id)



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
                if soggetto.addr_sede:
                    p2_1.add_run(str.title(soggetto.addr_sede), style='NumCduStyle')

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
                                mappali = 'fg ' + part.foglio + ' map ' + part.mappale
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

            rich = Anaprat.objects.filter(Q(pratica_id=pratica.id) & Q(tipo_id=1) | Q(tipo_id=14)).order_by('id')[0]
            # recuperea il tecnico istruttore
            try:
                istr_tec = Anaprat.objects.get(Q(pratica_id=pratica.id) & Q(tipo_id=3))
                s_istr_tec = Soggetto.objects.get(id=istr_tec.soggetto_id)
            except:
                istr_tec = ''
                s_istr_tec = ''
            print('richiedenti', rich)
            soggetto = Soggetto.objects.get(id=rich.soggetto_id)
            # verifico che esista il codice fiscale
            if soggetto.codice_fiscale and len(soggetto.codice_fiscale)==16:
                # verifico se maschio o femmina
                sesso_cf = soggetto.codice_fiscale[6:8]
                if int(sesso_cf)>40:
                    nascita =' nata a ' + soggetto.comune_nascita.title() + ' il ' + str(soggetto.data_nascita)
                else:
                    nascita =' nato a ' + soggetto.comune_nascita.title() + ' il ' + str(soggetto.data_nascita)
                    print('sesso_cf', sesso_cf)
            prot = pratica.prot_gen
            data = pratica.data_prot_gen


            ####################################
            #      OGGETTO
            ###################################
            preambolo='Avvio di procedimento ai sensi degli artt.7 e ss. della L. 241/1990 e smi'
            preambolo+='\n\tIstanza del ' + "%s" % pratica.data_prot_gen.strftime('%d') +'/'+ "%s" % pratica.data_prot_gen.strftime('%m')+'/'+"%s" % pratica.data_prot_gen.strftime('%Y') + ' Prot. Gen. n. ' + pratica.prot_gen 
            preambolo += '\n\tComunicazione di avvio del procedimento ed interruzione dei termini.'
            oggetto_lettera = preambolo

            # if pratica.street :

            #     ubicazione = ' Istanza di Permesso di Costruire presentata da  ' + soggetto.cognome + ' ' + soggetto.nome
            #     housenumber = pratica.housenumber

            if pratica.housenumber :
                    ubicazione=str(pratica.street) + ' ' + str(pratica.housenumber)
            else:
                                        ubicazione =  str(pratica.street).title()




            p2_4 = document.add_paragraph()
            p2_4.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p2_4.paragraph_format.space_before = Pt(30)
            p2_4.add_run(str('Oggetto : ') , style='NumCduStyleItalic').bold=True
            # p2_4 = document.add_paragraph()
            # p2_4.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p2_4.paragraph_format.space_after = Pt(4)
            p2_4.add_run(str(oggetto_lettera ), style='NumCduStyleItalic').bold=True

            ####################################
            #      PARAGRAFO NormalStyle
            ###################################

            par_1 = document.add_paragraph()
            par_1.paragraph_format.first_line_indent = Inches(0.3)
            # par_1 = paragraph_format.left_indent = Inches(0.5)
            par_1.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_HI

            par_1.paragraph_format.space_before = Pt(1)
            par_1.paragraph_format.space_after = Pt(4)
            par_1.add_run()
            par_1.add_run(('Con riferimento all\' istanza depositata in data ' ), style='NormalStyle')
            par_1.add_run("%s" % data.strftime('%d/%m/%Y'), style='NormalStyle')
            par_1.add_run((' prot. gen. n. '), style='NormalStyle')
            par_1.add_run(str(pratica.prot_gen), style='NormalStyle').bold=True
            # par_1.add_run((' del '), style='NormalStyle' )
            # par_1.add_run("%s" % data.strftime('%d/%m/%Y'), style='NormalStyle').bold=True
            par_1.add_run(''', con la quale è stata richiesta ''', style='NormalStyle' )
            par_1.add_run(('"' + str(pratica.oggetto+'"')), style='NormalStyleItalic' ).bold=True
            par_1.add_run(', ai sensi del DPR n. 162 del 30/04/1999 e smi per l\'impianto di sollevamento installato', style='NormalStyle')
            par_1.add_run(''', sull'immobile sito in Carrara,  ''', style='NormalStyle' )
            par_1.add_run( ubicazione, style='NormalStyle' )

            if lista:
                par_1.add_run(', catastalmente censito al ', style='NormalStyle')
                par_1.add_run(lista, style='NormalStyle')
            else:
                pass
            
            par_1.add_run(''', si comunica che la pratica risulta carente della seguente documentazione: ''', style='NormalStyle' )

            par_2 = document.add_paragraph()
            par_2.paragraph_format.first_line_indent = Inches(0.3)
            # par_1 = paragraph_format.left_indent = Inches(0.5)
            par_2.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_HI

            par_2.add_run( '.........documentazione mancante', style='NormalStyle' )


            par_4 = document.add_paragraph()
            par_4.paragraph_format.first_line_indent = Inches(0.3)
            par_4.paragraph_format.space_before = Pt(1)
            par_4.paragraph_format.space_after = Pt(1)
            par_4.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY
            par_4.add_run('''La documentazione di cui sopra dovrà essere trasmessa entro 15 giorni dal ricevimento della presente, in unica soluzione, al protocollo generale di questo Comune. ''', style='NormalStyle' )
            par_4.add_run('''In caso di non ottemperanza l\'istanza verrà archiviata ed il riesame della stessa potrà essere attivato in seguito alla presentazione di nuova istanza. ''', style='NormalStyle' )

            # par_4_2 = document.add_paragraph()
            # par_4_2.paragraph_format.first_line_indent = Inches(0.3)
            # par_4_2.paragraph_format.space_before = Pt(1)
            # par_4_2.paragraph_format.space_after = Pt(1)
            # par_4_2.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            # par_4_2.add_run('''Decorso il termine sopra richiamato l'interessato può chiedere al titolare del potere sostitutivo interno al Comune, ovvero al Segretario Generale, di adempiere entro 15 gg. dal ricevimento dell'istanza.''', style='NormalStyle' )

            # par_4_3 = document.add_paragraph()
            # par_4_3.paragraph_format.first_line_indent = Inches(0.3)
            # par_4_3.paragraph_format.space_before = Pt(1)
            # par_4_3.paragraph_format.space_after = Pt(1)
            # par_4_3.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            # par_4_3.add_run('''Nel caso in cui il Comune ancora non adempia, l'interessato può presentare istanza alla Regione Toscana, come disposto dall'art. 144 L.R.T. 65/2014 e smi.''', style='NormalStyle' )


            par_4_4 = document.add_paragraph()
            par_4_4.paragraph_format.first_line_indent = Inches(0.3)
            par_4_4.paragraph_format.space_before = Pt(5)
            par_4_4.paragraph_format.space_after = Pt(5)
            par_4_4.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            par_4_4.add_run('In osservanza degli artt. 5 e 7 della L. 241/1990 e smi, si informa che l\'Ufficio competente è \
l\'U.O. 6.1.2 "Sportello Unico Edilizia (SUEP) e vigilanza abusivismo", la pratica è stata assegnata all\'Istruttore Tecnico, \
geom. Carlo Alberto Nicolini', style='NormalStyle' )
            par_4_4.add_run(' contattabile al 0585 641 252 ed all\'indirizzo mail' , style='NormalStyle' )
            par_4_4.add_run(' carloalberto.nicolini@comune.carrara.ms.it ', style='NumCduStyleItalic')
            par_4_4.add_run('e che gli uffici sono aperti al pubblico il martedì pomeriggio dalle ore 15:00 alle 17:00 ed il mercoledì mattina dalle ore 9:00 alle 12:30, previo appuntamento.', style='NormalStyle' )

            # par_4_5 = document.add_paragraph()
            # par_4_5.paragraph_format.first_line_indent = Inches(0.3)
            # par_4_5.paragraph_format.space_before = Pt(1)
            # par_4_5.paragraph_format.space_after = Pt(8)
            # par_4_5.alignement = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW
            # par_4_5.add_run(''' Si invita la S.V. qualora dovesse rivolgersi presso il Settore o intraprendere corrispondenza a citare le sottoelencate diciture:''', style='NormalStyle' )
            # par_4_5.add_run(' Prot. Gen. '+  pratica.prot_gen + ' del ' + "%s" % pratica.data_prot_gen.strftime('%d') +'/'+ "%s" % pratica.data_prot_gen.strftime('%m')+'/'+"%s" % pratica.data_prot_gen.strftime('%Y')+'.', style='NormalStyle' )


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
            par_8_4.add_run('Il Dirigente ad interim', style='NormalStyle' )

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

