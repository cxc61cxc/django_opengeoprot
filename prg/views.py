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
from collections import defaultdict
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import *
from .models import Piano, Destinazione, Cerdesurb, Marca, Istruttoria
from protocollo.models import *
from protocollo.utils import log_action
from django.db.models import Max

#  elenca i piani urbanistici

def piani_list_view(request):

    piani = Piano.objects.all().order_by('-data_atto', 'name')

    
    context = {
        'piani': piani,
    }
    return render(request,'prg/piani_list_view.html', context)



def PianoAddView(request):
    submitted = False
    if request.method == "POST":
        form = PianoForm(request.POST)
        print (form)
        if form.is_valid():
            piano = form.save()
            submitted = True
            log_action(request, 'CREATO', f'Piano {piano.id}')
            # pk = Pratica.objects.latest('id').id # ricava l'ID della pratica inserita
            return HttpResponseRedirect(reverse('prg:piani_list_url')) # questo ridirige alla pagina di dettaglio pratica

    else:
        form = PianoForm()
        if 'submitted' in request.GET:
            submitted = True

    return render(request,'prg/piano_add.html',{'form':form,'submitted':submitted})





def PianoEditView(request, id):
    piano = Piano.objects.get(id=id)
    if request.method == 'POST':
       form = PianoForm(request.POST, instance=piano)
       if form.is_valid():
           # update the existing `Pratica` in the database
           form.save()
           log_action(request, 'MODIFICATO', f'Piano {piano.id}')
           # redirect to the detail page of the `Pratica` we just updated
           return redirect('prg:piani_list_url')
    else:
        form = PianoForm(instance=piano)

    return render(request,
                'prg/piano_edit.html',
                {'form': form, 'piano':piano})


def PianoDetailView(request, id):
    piano = get_object_or_404(Piano, id=id)
    log_action(request, 'VISUALIZZATO', f'Piano {piano.id}')
    # lista le destinazioni del piano
    destinazioni = Destinazione.objects.filter(piano=piano)
    print(destinazioni)
    return render(request, 'prg/piano_detail.html', {'piano': piano, 'destinazioni':destinazioni})

######################################################################
#                           DESTINAZIONI
######################################################################


# edita la destinazione

def DestinazioneEditView(request, id):
    destinazione = Destinazione.objects.get(id=id)
    print(destinazione)
    if request.method == 'POST':
       form = DestinazioneForm(request.POST, instance=destinazione)
       if form.is_valid():
           # update the existing `Pratica` in the database
           form.save()
           log_action(request, 'MODIFICATO', f'Destinazione {destinazione.id}')
           # redirect to the detail page of the `Pratica` we just updated
           return redirect('prg:piano_detail_url', destinazione.piano_id)
    else:
        form = DestinazioneForm( instance=destinazione)

    return render(request,
                'prg/destinazione_edit.html',
                {'form': form})


# AGGIUNGE la destinazione

def DestinazioneAddView(request, id):
    
    if request.method == 'POST':
        form = DestinazioneForm(request.POST)
        if form.is_valid():
            nuovo = form.save(commit=False)
            nuovo.piano_id = id
            print(f"Nuovo destinazione: {nuovo}")
            nuovo.save()
            log_action(request, 'CREATO', f'Destinazione {nuovo.id}', {'piano': id})
            print ('jlkljad078ad', Destinazione.objects.filter(piano_id=id))
           # redirect to the detail page of the `Pratica` we just updated
            return redirect('prg:piano_detail_url', id)
    else:
        form = DestinazioneForm()

    return render(request,
                'prg/destinazione_piano_add.html',
                {'form': form})


######################################################################
#   CDU
######################################################################


#   elenca i certificati di destinazione urbanistica

def cerdesurb_list_view(request):

    cerdesurb = Cerdesurb.objects.all().order_by('cdu_date','cdu_number')
    numero = cerdesurb.count()
    print('numero',numero)
    context = {
        'vedi':"vedi",
        'cerdesurb': cerdesurb,
        'numero':numero,
    }
    return render(request,'prg/cerdesurb_list_view.html', context)



@login_required
# @user_passes_test(lambda u: u.groups.filter(name='editor_settore_6').count() == 1, login_url='home')
#   aggiunge un cdu legato alla pratica ( un cdu per pratica )

def cerdesurb_add_view(request, pk):
    # ora pk è passato come parametro
    try:
        pratica=Pratica.objects.get(id=pk)
    except Pratica.DoesNotExist:
        # gestisci errore
        return redirect('nome_url_di_errore')
    
    submitted = False
    # pk = request.session.get('pk')
    form = CduForm(request.POST)
   
    pratica=Pratica.objects.get(id=pk)
    tipo_pratica_id = pratica.tipo_pratica_id
    # provo a impostare il numero di CDU
    # cerco i cdu per l'anno in corso
    today = datetime.date.today()
    year = today.year
    # se è un cdu
    # conto i cdu presenti nell'anno
    if tipo_pratica_id == 7:
        queryset = Cerdesurb.objects.filter(Q(cdu_date__year=year) & Q(uso__in=['Atto','Successione', 'Altro']))
        numero = queryset.aggregate(Max('cdu_number'))['cdu_number__max']
        print('max_cdu_number', numero)
        # Se vuoi il count, puoi farlo separatamente
        count = queryset.count()
    else:
        numero = int(pratica.prot_gen)
    # if tipo_pratica_id == 7:
    #     numero = Cerdesurb.objects.filter(Q(cdu_date__year=year) & Q(uso__in=['Atto','Successione', 'Altro'])).count()
    #     print('max_cdu_number',numero.aggregate(Max('cdu_number'))['cdu_number__max'])
    # else:
    #     numero = int(pratica.prot_gen)
    print('numero',numero)
    #   propone il
    print('anno',year)
    # numero = Cerdesurb.objects.filter(cdu_date__icontains=year).count()
    if numero  :
        nuovo_cdu = numero+1
    else:
        nuovo_cdu = 1
    print ('prossimo cdu',nuovo_cdu) # stampa il numeroo dei cdu nell'anno

    # ora il numero di cdu proposto dovrebbe risultare 1 per il primo cdu dell'anno e proporre il nuovo numero se già presenti altri (nuovo_cdu)

    print('aggiunge cdu a pratica id',pk)
    # pratica = Cerdesurb.objects.filter(pratica = pk)
    # pratica= Pratica.objects.get(id=pk)
    tipo=pratica.tipo_pratica
    num_cdu=nuovo_cdu
    print ('tipo',tipo,'tipo_pratica',pratica.tipo_pratica)
    # if str(tipo)=='cdu': # esegue se la pratica è id=3 name = cdu    
    if request.method == "POST":

            print(num_cdu,'zero cdu',tipo)
                  

            if form.is_valid():
                    obj=form.save(commit=False)
                    obj.pratica_id = pk
                    if tipo_pratica_id != 7:
                        obj.uso = 'Informativa'
                        
                    obj.save()
                    cdu_id = obj.id
                    log_action(request, 'CREATO', f'Cerdesurb {cdu_id}', {'pratica': pk})
                    return redirect('prg:cerdesurb_detail_url' ,cdu_id)
    else:
            form = CduForm()
           
            if 'submitted' in request.GET:
                submitted = True
                print('id',id)
            context = { 'form':form,
                        'pratica':pratica,
                        'submitted':submitted, 
                        'cdu_proposto':nuovo_cdu,
                        'today':today,}
            return render(request,'prg/cerdesurb_add_view.html',context)
    # else :
    #     print('non arriva nessun dato')
    #     return render(request,'prg/cerdesurb_add_view.html',{'form':form,'pratica':pratica,'submitted':submitted, 'cdu_proposto':nuovo_cdu})

    return redirect('protocollo:pratica_detail_url' ,pk)



           


# dettaglio cdu e particelle

def CduDetailView(request, id):
    if request.session.session_key:
        # La sessione è attiva
        print('sessione attiva')
    else:
        # Non c'è sessione attiva
        print('sessione non attiva')
    pk = 0
    #   recupero il cdu
    cdu = get_object_or_404(Cerdesurb, id=id)
    pk = cdu.pratica_id
    log_action(request, 'VISUALIZZATO', f'Cerdesurb {cdu.id}')
    print(cdu.pratica.id)
    # imposto la lista delle particelle
    particelle=[]
    richiedente=[]



##########################################
    # marche da bollo
##########################################


    marche = Marca.objects.filter(cdu_id=cdu.id) 
    # tot_marche = marche.count()
    print('marcheee',marche)

    # lista le particelle del CDU
    cataprat = Cataprat.objects.filter(pratica_id=pk)

    for p in cataprat:
        mappali ={} # imposto il dizionario

        part = Particella.objects.get(id=p.particella_id)

        mappali['id_cataprat']=p.id
        print(p.id,'yd755d6ns')
        mappali['foglio']=part.foglio
        mappali['mappale']=part.mappale
        dest = Istruttoria.objects.filter(cataprat=p.id)
        mappali['tot']=dest.count()

        particelle.append(mappali)

    particelle.sort(key=lambda x: (int(x['foglio']) if x['foglio'].isdigit() else x['foglio'], int(x['mappale']) if str(x['mappale']).isdigit() else x['mappale']))
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
            'cdu': cdu,
            'particelle':particelle,
            'richiedente':richiedente,
            'marche': marche}


    return render(request, 'prg/cerdesurb_detail_view.html', context)

#   modifica dati cdu

# @user_passes_test(lambda u: u.groups.filter(name='editor_settore_6').count() == 1, login_url='home')
@login_required
def CduEditView(request, id):
    cdu_edit=[]
    cdu = Cerdesurb.objects.get(id=id)
    print('cdu',cdu)
    pk= cdu.id
    print('pk',pk)
    if request.method == 'POST':
       form = CduForm(request.POST, instance=cdu)
       if form.is_valid():
           # update the existing `Pratica` in the database
           form.save()
           log_action(request, 'MODIFICATO', f'Cerdesurb {cdu.id}')
           # redirect to the detail page of the `Pratica` we just updated
           return redirect('prg:cerdesurb_detail_url', pk )
    else:
        form = CduForm(instance=cdu)

    return render(request,
                'prg/cerdesurb_edit.html',
                {'form': form, 'cdu':cdu})

#############################
#gestione marche da bollo
#############################


def marca_list(request, id):
    cerdesurb = get_object_or_404(Cerdesurb, pk=id)
    marche = cerdesurb.marche.all()
    return render(request, 'prg/marca_list.html', {'marche': marche, 'cdu': cerdesurb.id})

def marca_create(request, id):
    cerdesurb = get_object_or_404(Cerdesurb, pk=id)
    if request.method == 'POST':
        form = MarcaForm(request.POST)
        if form.is_valid():
            marca = form.save(commit=False)
            marca.cdu_id = id
            marca.save()
            log_action(request, 'CREATO', f'Marca {marca.id}', {'cdu': id})
            return redirect('prg:cerdesurb_detail_url', id=id)
    else:
        form = MarcaForm()
    return render(request, 'prg/marca_form.html', {'form': form, 'cdu':id})

def marca_update(request, pk):
    marca = get_object_or_404(Marca, pk=pk)
    cdu_id = marca.cdu_id
    if request.method == 'POST':
        form = MarcaForm(request.POST, instance=marca)
        if form.is_valid():
            form.save()
            log_action(request, 'MODIFICATO', f'Marca {marca.id}')
            return redirect('prg:cerdesurb_detail_url', id=cdu_id)
    else:
        form = MarcaForm(instance=marca)
    return render(request, 'prg/marca_form.html', {'form': form, 'cdu':cdu_id})

def marca_delete(request, pk):
    marca = get_object_or_404(Marca, pk=pk)
    cdu_id = marca.cdu_id
    if request.method == 'POST':
        marca.delete()
        log_action(request, 'ELIMINATO', f'Marca {marca.id}', {'cdu': cdu_id})
        return redirect('prg:cerdesurb_detail_url', id=cdu_id)
    return render(request, 'prg/marca_confirm_delete.html', {'marca': marca})




# CduDetailView
########################################################################

#               ISTRUTTORIA PARTICELLA

########################################################################


def AddDestinazioniView(request, id):
    


    pk = request.session.get('pk')
    cataprat = id
    print('id',id,'pk',pk)
    if request.method == "POST":

        # cataprat = request.POST.get('cataprat') # prendo l'id della pratica ( pratica_id ) del Model Cataprat
        if request.POST.get('select'):
            list = request.POST.getlist('select')
            print('post arrivato')
        # if request.POST.get('select_parte'):
            list_select = request.POST.getlist('select_parte')
            print('list',list,'list_select',list_select)
            for destinazione_id in list:
                destinazione_id=destinazione_id
                print(destinazione_id)
                parte=0
                if list_select:
                    for select_id in list_select:
                        if select_id==destinazione_id:
                            print('select_id',select_id,'uguale a',destinazione_id)
                            parte=1
                  
                dest = Istruttoria(cataprat_id=id, destinazione_id=destinazione_id,parte=parte)
                dest.save()
                print('salvata destinazione id',dest.destinazione_id)



        return redirect('prg:istruttoria_detail_url' ,id)




def SearchDestinazioneView(request):
    search_text = request.POST.get('search')

    destinazioni = Destinazione.objects.filter(description__icontains=search_text)
    context ={'destinazioni':destinazioni,}
    print('destinazioni',destinazioni)
    return render(request,'prg/partials/add_istruttoria_view.html', context)




def DestinazioniIstruttoriaView(request, id): # ID di piano
    if id != '':
        print('id',id)
        pk_pratica = Cataprat.objects.filter(id=id).values('pratica_id')
        print(pk_pratica,'hjd77dhdjkdo')
    else:
        print('no id')
    print('id_piano',id)
    submitted = False
    if request.method == "POST":
        # piano=request.POST['id']
        piano=Piano.objects.get(id=request.POST['id'])

        destinazioni=Destinazione.objects.filter(piano_id=request.POST['id'])
        particella = Cataprat.objects.get(id=id)
        
        context = {
        'piano':piano,
        'destinazioni':destinazioni,
        'particella':particella,
        'cataprat':id, #l'id della particella in Cataprat
        }
        return render(request,'prg/add_istruttoria_view.html', context)

    else:
        form = IstruttoriaForm()
        print('vi è qualcosa di sbagliato!...kjkd54ad78ad')



        if 'submitted' in request.GET:
            submitted = True

    return render(request,'prg/add_istruttoria_view.html',{'form':form,'submitted':submitted})


# PDF stampa istruttoria particella
def pdf_particella(request, *args, **kwargs):
    particella_id = kwargs.get('pk')
    particella= get_object_or_404(Cataprat,id=particella_id)
    destinazioni = Istruttoria.objects.filter(cataprat_id=particella.id)


    istruttoria=[]
    for a in destinazioni:
        destinazione={} # creo un dizionario vuoto
        dest_cataprat = Destinazione.objects.get(id=a.destinazione_id)
        print(a.destinazione_id)
        destinazione['id']=a.id
        destinazione['cataprat_id']=a.cataprat_id
        destinazione['destinazione_id']=a.destinazione_id
        destinazione['description']=dest_cataprat.description
        destinazione['parte']=a.parte
        
        istruttoria.append(destinazione)
        print(destinazione)
        pass

#   ELIMINA Istruttoria

def DeleteIstruttoriaView(request, id):
    # pk = request.session.get('pk')
    istruttoria = Istruttoria.objects.get(id=id)
    pk = istruttoria.cataprat_id
    
    
    print('punto di arrivo 215sd74d44dg64dg','id ',id, 'pk',pk)
        
    print ('istruttoria',istruttoria, 'id',id)

    istruttoria.delete()
    log_action(request, 'ELIMINATO', f'Istruttoria {id}', {'cataprat': pk})
        # istruttoria = Istruttoria.objects.filter(id=id).delete() # we need this for both GET and POST
    print ('istruttoria',istruttoria, 'id',id)
    return redirect('prg:istruttoria_detail_url' , pk)
    


@login_required

def IstruttoriaDetailView(request,id):
    pk = Cataprat.objects.get(id=id).pratica_id
    cdu = get_object_or_404(Cerdesurb, pratica_id=pk)
    print('id',id)

    cdu = Cerdesurb.objects.get(pratica_id=pk)
    log_action(request, 'VISUALIZZATO', f'Istruttoria per cataprat {id}')
    print(cdu)
    data_ref = cdu.data_riferimento
    print(data_ref)
    
    particelle_istruttoria = Istruttoria.objects.filter(cataprat_id=id)
    print('particelle_istruttoria',particelle_istruttoria)
    print('id_cataprat',id)
    
    istruttoria = []
    for d in particelle_istruttoria:
        destinazioni ={}
        dest = Destinazione.objects.get(id=d.destinazione_id)
        print('dest',d.id)
        order = Piano.objects.get(id=dest.piano_id)
        destinazioni['cataprat_id'] = d.cataprat_id
        destinazioni['id'] = dest.id
        destinazioni['id_istruttoria']=d.id
        destinazioni['piano']= dest.piano
        destinazioni['ordine']=order.ordine
        destinazioni['description']= dest.description
        destinazioni['parte']= d.parte

        istruttoria.append(destinazioni)
        # istruttoria = sorted(istruttoria, dest.piano)
    # print('sorted',sorted(istruttoria, key=lambda i: i['ordine']))
        # print('istruttoria',istruttoria)
        istruttoria = sorted(istruttoria, key=lambda i: i['description']) # ordina in base alla descrizione
        istruttoria = sorted(istruttoria, key=lambda i: i['ordine']) # ordina in base al numero d'ordine dei Piani
   
    print('')
    # lista le particelle del CDU
    mappale = Cataprat.objects.get(id=id)
    particella = Particella.objects.get(id=mappale.particella_id)
    richiedente=[]
    anaprat = Anaprat.objects.filter(pratica_id=pk)[:1]
    for s in anaprat:
        soggetti={}
        sogg = Soggetto.objects.get(id=s.soggetto_id)
        soggetti['id_anaprat']=s.id
        soggetti['cognome']=sogg.cognome
        soggetti['nome']=sogg.nome

        richiedente.append(soggetti)
        print (sogg.cognome)
        
        print(data_ref)
        piano = Piano.objects.filter(Q(data_in__lt=data_ref) & ( Q(data_out__gt=data_ref) | Q(data_out__isnull=True)) ).order_by('ordine') # NON TOCCARE, funziona
        # piano = piano.filter(Q(data_out__isnull=False))
        print (piano)

        # elenca le altre particelle del cdu ( includendo quella corrente ) per poter accedere velocemente
        # senza ripassare dal dettaglio del cdu
        other_part=[]
        altre_particelle = Cataprat.objects.filter(pratica_id=cdu.pratica_id)
        for other in altre_particelle:
            ap={}
            partic = Particella.objects.get(id=other.particella_id)
            ap['id_particella']=partic.id
            ap['id_cataprat']= other.id
            ap['foglio']=partic.foglio
            ap['mappale']=partic.mappale
            ap['is_current']= (other.id == id)

            other_part.append(ap)

        cataprat_ids = [ap['id_cataprat'] for ap in other_part]
        istruttorie_qs = Istruttoria.objects.filter(cataprat_id__in=cataprat_ids).select_related('destinazione__piano')

        destinazioni_by_cataprat = defaultdict(list)
        for ist in istruttorie_qs:
            dest = ist.destinazione
            dest_piano = dest.piano if dest and dest.piano else None
            destinazioni_by_cataprat[ist.cataprat_id].append({
                'description': dest.name if dest else '',
                'piano': dest_piano.name if dest_piano else '',
                'ordine': dest_piano.ordine if dest_piano else 0,
                'parte': ist.parte,
            })

        for ap in other_part:
            dests = destinazioni_by_cataprat.get(ap['id_cataprat'], [])
            ap['destinazioni'] = sorted(dests, key=lambda i: (i['ordine'], i['description']))
            parts = []
            for d in ap['destinazioni']:
                label = d['description']
                if d['parte']:
                    label += ' (in parte)'
                else:
                    label += ' (intera)'
                if d['piano']:
                    label = d['piano'] + ' - ' + label
                parts.append(label)
            ap['destinazioni_str'] = '; '.join(parts)
            ap['tot'] = len(dests)

        other_part.sort(key=lambda x: (int(x['foglio']) if x['foglio'].isdigit() else x['foglio'], int(x['mappale']) if str(x['mappale']).isdigit() else x['mappale']))
        print('altre_particelle',altre_particelle)
        context = {
            'piano':piano,
            'istruttoria':istruttoria,
            'cdu':cdu,
            'cognome':sogg.cognome,
            'nome':sogg.nome,
            'particella':particella,
            'cataprat':id, #l'id della particella in Cataprat
            'altre_particelle':other_part,
        }
    return render(request,'prg/istruttoria_particella_list.html', context)


def cdu_list(request):
    exclude = 'Informativa'
    lista = Cerdesurb.objects.all().exclude(uso__iexact=exclude).order_by('-cdu_date', '-cdu_number')
    
    return render(request, 'prg/cdu_list.html',{'lista':lista})
    
########################################################################
#               menu a discesa collegati (piano->destinazioni di piano)
#   https://stackoverflow.com/questions/57122613/how-to-implement-3-way-dependent-chained-dropdown-list-with-django
#   https://simpleisbetterthancomplex.com/tutorial/2018/01/29/how-to-implement-dependent-or-chained-dropdown-list-with-django.html
########################################################################




###################################################################################

#                                   STAMPA CDU

###################################################################################


from django.http import HttpResponse, Http404
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

def CreateDoc(request,id):
    cdu = Cerdesurb.objects.get(id=id) # cdu da produrre
    print(cdu)
    pratica = Pratica.objects.get(id=cdu.pratica_id)
    log_action(request, 'GENERATO DOCUMENTO', f'CDU {cdu.id}', {'pratica_id': pratica.id, 'cdu_number': cdu.cdu_number})
    today = datetime.date.today()
    current_year = today.year
    current_month = today.month
    current_day = today.day
    data_info = f"{pratica.data_prot_gen.year}{pratica.data_prot_gen.month:02d}{pratica.data_prot_gen.day:02d}"
    # imposto il nome del documento in funzione del tipo_pratica_id == 7
    # Formatta la data in formato AAAAMMDD
    date_str = f"{current_year}{current_month:02d}{current_day:02d}"

    # Imposta il nome del documento in base al tipo_pratica_id
    if pratica.tipo_pratica_id == 7:
        atto = f'{cdu.cdu_number}_cdu_{date_str}.docx'
    else:
        atto = f'{cdu.cdu_number}_informativa_{data_info}.docx'

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
    footer=section.footer

    f1=footer.add_paragraph()
    f1.paragraph_format.space_after = Pt(0)
    f1.paragraph_format.space_before = Pt(0)
    f1.add_run("Settore 6 Governo del territorio - Servizio 6.1 Urbanistica e edilizia privata - U.O. 6.1.1 Pianificazione urbanistica - P.zza due giugno,1 54033 - Carrara (MS)", style = 'FooterStyle')

    # f2=footer.add_paragraph()
    # f2.paragraph_format.space_after = Pt(0)
    # f2.paragraph_format.space_before = Pt(0)
    # f2.add_run("geom. Sergio Torri - 0585 641432 - sergio.torri@comune.carrara.ms.it", style = 'FooterStyle')

    f3=footer.add_paragraph()
    f3.paragraph_format.space_after = Pt(0)
    f3.paragraph_format.space_before = Pt(0)
    f3.add_run("geom. Carlo Alberto Nicolini - 0585 641252 - carloalberto.nicolini@comune.carrara.ms.it", style = 'FooterStyle')
    
    f4=footer.add_paragraph()
    f4.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    f4.paragraph_format.space_after = Pt(0)
    f4.paragraph_format.space_before = Pt(0)
    f4.add_run(str(request.user.id), style = 'FooterStyle')
   
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
            

# #    stampo i dati del cdu
    if pratica.tipo_pratica_id == 7:
        p1 = document.add_paragraph()
        p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p1.bold=True
        p1.add_run('Certificato di Destinazione Urbanistica', style = 'CduStyle').bold = True
    else:
        p1 = document.add_paragraph()
        p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p1.bold=True
        p1.add_run('Informativa urbanistica', style = 'CduStyle').bold = True
    
    if pratica.tipo_pratica_id == 7:
        p2 = document.add_paragraph()
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p2.paragraph_format.space_after = Pt(2)
        p2.add_run(str(cdu.cdu_number) + '/CDU/'+"%s" % cdu.cdu_date.strftime('%Y'), style='NumCduStyle').bold=True
        p3 = document.add_paragraph()

        p3.paragraph_format.space_after = Pt(36)
        p3.paragraph_format.space_before = Pt(1)
        p3.alignment = WD_ALIGN_PARAGRAPH.CENTER 
        p3.add_run('(Art. 30 D.P.R. 06/06/2001 n. 380)', style='DprStyle')
    else:
        p2 = document.add_paragraph()
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p2.paragraph_format.space_after = Pt(2)
        p2.add_run(str(cdu.cdu_number) + ' INFORMATIVA '+"%s" % cdu.cdu_date.strftime('%Y%m%d'), style='NumCduStyle').bold=True
    

#   stampo "USO SUCCESSIONE" se è quello l'uso

    if cdu.uso =='Successione':
    
        p4= document.add_paragraph()
        p4.alignment = WD_ALIGN_PARAGRAPH.CENTER 
        p4.add_run('USO SUCCESSIONE', style='NormalStyle').bold=True
        
        p4_1=document.add_paragraph()
        p4_1.alignment = WD_ALIGN_PARAGRAPH.CENTER 
        p4_1.add_run('( La certificazione si riferisce alla data del ' + cdu.data_riferimento.strftime('%d/%m/%Y') +' )', style='DprStyle')
        
        vuoto = document.add_paragraph(' ')
        vuoto.add_run(' ')


    
    # ESTRAE le particelle interessate e le elenca
    particelle = Cataprat.objects.filter(pratica_id=cdu.pratica_id) 
    tot_particelle = particelle.count()
    print('tot_particelle',tot_particelle)
    pratica = Pratica.objects.get(id=cdu.pratica_id) # recupera i dati della pratica

    # recupera il primo richiedente (tipo_id=1), con fallback su qualunque soggetto
    rich = Anaprat.objects.filter(pratica_id=cdu.pratica_id, tipo_id=1).first()
    if not rich:
        rich = Anaprat.objects.filter(pratica_id=cdu.pratica_id).first()
    print('richiedenti', rich)
    if rich is None:
        raise Http404("Nessun richiedente associato a questa pratica.")
    soggetto = Soggetto.objects.get(id=rich.soggetto_id)
    print('soggetto',soggetto)
    if soggetto.comune_nascita:
        # verifico se maschio o femmina 
        sesso_cf = soggetto.codice_fiscale[9:11]

        testo = soggetto.comune_nascita.title()
        testo_pulito = testo.replace("(54033) - Ms", "")
        data_nascita_str = soggetto.data_nascita.strftime('%d/%m/%Y') if soggetto.data_nascita else ''
        if int(sesso_cf)>=40:
            nascita =' nata a ' + testo_pulito + ' il ' + data_nascita_str
        else:
            nascita =' nato a ' + testo_pulito + ' il ' + data_nascita_str
        print('sesso_cf', sesso_cf)
    else:
        nascita = ''

    prot = pratica.prot_gen
    data = pratica.data_prot_gen
    
    particelle_sorted = []
    for p in particelle:
        part = Particella.objects.get(id=p.particella_id)
        particelle_sorted.append({'cataprat': p, 'particella': part})
    particelle_sorted.sort(key=lambda x: (int(x['particella'].foglio) if x['particella'].foglio.isdigit() else x['particella'].foglio, int(x['particella'].mappale) if x['particella'].mappale.isdigit() else x['particella'].mappale))

    foglio_pre="" # imposta a blank il foglio precedente
    lista =[]
    for item in particelle_sorted:
        p = item['cataprat']
        part = item['particella']
        if foglio_pre==part.foglio:
            mappali = 'map ' + part.mappale + '; '
        else:
            mappali = 'Foglio ' + part.foglio + ' map ' + part.mappale + '; '
        foglio_pre= part.foglio
        lista.append(mappali)
    print(lista, foglio_pre, part.foglio)
    #document.add_paragraph(lista)
    
    if pratica.tipo_pratica_id == 7:

    
        par_1 = document.add_paragraph()
        # par_1.alignment = WD_ALIGN_PARAGRAPH.LEFT
        par_1.alignement = WD_ALIGN_PARAGRAPH.DISTRIBUTE
        # par_1.paragraph_format.left_indent = Inches(0.5)
        par_1.paragraph_format.first_line_indent = Inches(0.5)
        par_1.add_run('Vista la richiesta (prot. n. ')
        
        # par_1.add_run()
        par_1.add_run(prot).bold=True
        par_1.add_run(' del ' )
        par_1.add_run("%s" % data.strftime('%d/%m/%Y') ).bold=True
        par_1.add_run(') presentata da ')
        par_1.add_run(soggetto.cognome.upper() + ' ' + soggetto.nome.title())
        if soggetto.codice_fiscale:
            cod_fisc = '(c.f. ' + soggetto.codice_fiscale.upper() +')'  
        else:
            cod_fisc=''
        comune_res = soggetto.comune_residenza.title() if soggetto.comune_residenza else ''
        par_1.add_run(nascita+', '+ cod_fisc +  ' residente in ' + comune_res + ' ' )
        if  soggetto.addr != '' and soggetto.addr_sede =='':
            par_1.add_run(soggetto.addr.title() )
        if  soggetto.addr == '' and soggetto.addr_sede !='':
            par_1.add_run(soggetto.addr_sede.title() )
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
    else :
        pass

#   DEFINISCE I PIANI E DESTINAZIONI PER PARTICELLLA
    particelle = Cataprat.objects.filter(pratica_id=cdu.pratica_id) #estrae tutte le particelle presenti nella pratica
    
    particelle_list = []
    for c in particelle:
        part = Particella.objects.get(id=c.particella_id)
        particelle_list.append({'cataprat': c, 'particella': part})
    particelle_list.sort(key=lambda x: (int(x['particella'].foglio) if x['particella'].foglio.isdigit() else x['particella'].foglio, int(x['particella'].mappale) if x['particella'].mappale.isdigit() else x['particella'].mappale))
    
    print('particelle',particelle)
    for item in particelle_list:
        c = item['cataprat']
        particella_cdu = item['particella']
        print('particella_cdu.id',particella_cdu.id)

#   stampa la particella corrente
        par_01 = document.add_paragraph()
        par_01.alignment = WD_ALIGN_PARAGRAPH.LEFT
        par_01.paragraph_format.space_before = Pt(10)
        par_01.paragraph_format.space_after = Pt(10)
        runner = paragraph.add_run()
        runner.underline = WD_UNDERLINE.SINGLE
        runner = par_01.add_run('Fg. ' + particella_cdu.foglio + ' map. ' + particella_cdu.mappale, style = 'ParticellaStyle')
        
        print(c.id)
        #   estrae i piani per singola istruttoria
        particelle_istruttoria = Istruttoria.objects.filter(cataprat_id=c.id).order_by('destinazione_id')
        
        piano_ex=0
        piani_cdu=[]
        for p in particelle_istruttoria:
            print(p.id)
            pp={}
            # print('istruttoria',p.destinazione_id, p.parte)
            piano = Destinazione.objects.get(id=p.destinazione_id)
            order = Piano.objects.get(id=piano.piano_id)
            pp['id_piano'] = piano.piano_id
            
            pp['ordine'] = order.ordine
            
            piani_cdu.append(pp)
        print(piani_cdu)
        piani_cdu = sorted(piani_cdu, key=lambda x: x['ordine'])
        print('lista',piani_cdu)
        piani_raggruppati = []
        for key, group in groupby(piani_cdu, lambda x: x['id_piano']):
                piani_raggruppati.append({'id_piano': key, 'count': len(list(group))})
                # piani_raggruppati.sort(key=ordine)
        # piani_raggruppati=sorted(piani_raggruppati)
        print(piani_raggruppati)
                                # print(piano.piano_id)
                    ###########################################
                    ####    STAMPA L'ELENCO DEI PIANI       ###
                    ###########################################
        for pd in piani_raggruppati:
                        pd = Piano.objects.get(id=pd['id_piano'])
                        par_01 = document.add_paragraph(style='List Bullet')
                        par_01.paragraph_format.line_spacing = Pt(11)

                        par_01.paragraph_format.space_before = Pt(6)
                        par_01.paragraph_format.space_after = Pt(6)
                        par_01.alignment = WD_ALIGN_PARAGRAPH.LEFT
                        # par_01.paragraph_format.space_after = Pt(5)
                        # par_01.bold=True
                        runner = par_01.add_run(pd.description, style='PianoStyle').italic=True
                        # print(pd.description)
                        ######################################################################
                        ####    STAMPA L'ELENCO DELLE DESTINAZIONI PER SINGOLO PIANO       ###
                        ######################################################################
                        for p in particelle_istruttoria:
                            dest_piano=[]
                            # print('istruttoria',p.destinazione_id, p.parte)
                            dd = Destinazione.objects.filter(Q(id=p.destinazione_id) & Q(piano_id=pd.id))
                            for x in dd:
                                pp={}
                                
                                if p.parte == False:
                                    pp['descrizione']= ' - ' + x.description + ', intera particella;'
                                else:
                                    pp['descrizione']= ' - ' + x.description + ', in parte;'
                                dest_piano.append(pp)
                                for ds in dest_piano:
                                    par_101 = document.add_paragraph()
                                    paragraph_format = par_101.paragraph_format
                                    paragraph_format.left_indent = Inches(0.4)
                                    paragraph_format.line_spacing = Pt(11)
                                    paragraph_format.space_after = Pt(1)
                                    par_101.alignment = WD_ALIGN_PARAGRAPH.LEFT
                                    # par_101.font.size = Pt(9)
                                    # par_01.bold=True
                                    runner = par_101.add_run(ds['descrizione'], style ='DestinazioneStyle')
                                    # print(dest_piano)
                                    # print('destinazione')
    p001= document.add_paragraph()
    paragraph_format = p001.paragraph_format
    # paragraph_format.left_indent = Inches(0.4)
    # paragraph_format.line_spacing = Pt(11)
    paragraph_format.space_before = Pt(5)
    p001.alignment = WD_ALIGN_PARAGRAPH.LEFT 
    p001.add_run('Sono da ritenersi comunque aree tutelate per legge e sottoposte a vincolo paesaggistico, ai sensi dell\'art. 142 c.1 lett.g) del D.Lgs. n. 42/2004, ',style ='DestinazioneStyle')
    p001.add_run('le aree boscate corrispondenti alla definizione di cui alla L.R. 39/2000 ed al Reg. Forestale D.P.G.R. n. 48/R-2003 e smi.', style ='DestinazioneStyle')
    
    p001_1= document.add_paragraph()
    p001_1.alignment = WD_ALIGN_PARAGRAPH.LEFT 
    p001_1.add_run('Sono inoltre fatti salvi, su tutto il territorio comunale, eventuali vincoli relativi a fasce di rispetto della viabilità e ferroviarie, cimiteriale, di normativa sovraordinata in materia, anche laddove non espressamente specificato.',style ='DestinazioneStyle')

    if pratica.tipo_pratica_id == 7:

        p002= document.add_paragraph()
        p002.alignment = WD_ALIGN_PARAGRAPH.LEFT 
        p002.add_run('Il presente certificato non può essere prodotto agli organi della pubblica amministrazione o ai privati gestori di pubblici servizi.',style ='DestinazioneStyle').bold=True

        p003= document.add_paragraph()
        p003.alignment = WD_ALIGN_PARAGRAPH.LEFT 
        p003.add_run('Carrara, data della sottoscrizione digitale',style ='DestinazioneStyle')

        p004= document.add_paragraph()
        p004.alignment = WD_ALIGN_PARAGRAPH.RIGHT 
        p004.add_run('Il Dirigente' ,style ='DestinazioneStyle')

        p005= document.add_paragraph()
        p005.alignment = WD_ALIGN_PARAGRAPH.RIGHT 
        p005.paragraph_format.space_after = Pt(20)
        p005.add_run('Ing. Luca Amadei' ,style ='DestinazioneStyle')

        p08 = document.add_paragraph()
        p08.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        
        p08.add_run('Documento firmato digitalmente ai sensi e per gli effetti di cui agli artt.21, 23, 23bis e 23ter del D.LGS. 82 del 7 marzo 2005 e s.m.i. - \
    Codice dell\'Amministrazione Digitale', style='SottoHeaderStyle').italic=True
        
        # Stampa l'assolvimento bolli... se mancano stampa ALERT
        p09 = document.add_paragraph()
        p09.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        print(cdu.uso)
        if cdu.uso != 'Successione' and cdu.uso != 'Informativa':
            marche = Marca.objects.filter(cdu_id=cdu.id).last()
            if marche is not None :
                if marche.data_iuv:
                    p09.add_run(
                        'Imposta di bollo assolta in modo virtuale ai sensi dell\'art. 15 del D.P.R. 642 del 26/10/1972,\
come da autorizzazione n. 10023822 del 13/07/2021 dell\' Agenzia delle Entrate per il Comune di Carrara sul servizio PagoPa Bollo Virtuale I.U.V. ' + str(marche.iuv) + ' del ' + str("%s" % marche.data_iuv.strftime('%d/%m/%Y')),
                        style='SottoHeaderStyle'
                    ).italic = True
                else :
                    p09.add_run(
                        'Bollo assolto con marca n. ' + str(marche.marca) + ' del ' + str("%s" % marche.data_marca.strftime('%d/%m/%Y')),
                        style='SottoHeaderStyle'
                    ).italic = True
            else:
                    p09.add_run('NON HAI INSERITO LE MARCHE DA BOLLO....SOMARO!', style='SottoHeaderStyle')
        else:
            p09.add_run('Esente bollo come da tabella “B” del  D.P.R. 26.10.1972 n. 642', style='SottoHeaderStyle').italic=True

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






def PrintPianieDestinazioni(request):
    today = date.today()
    atto = 'elenco_piani_e_vincoli.docx'
    
    document = Document()
    # imposta A4 verticale e margini
    section = document.sections[0]
    section.page_height = Mm(210)
    section.page_width = Mm(297)
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
    footer=section.footer

    f1=footer.add_paragraph()
    f1.paragraph_format.space_after = Pt(0)
    f1.paragraph_format.space_before = Pt(0)
    f1.add_run("Settore 6 Governo del territorio - Servizio 6.1 Urbanistica e edilizia privata - U.O. 6.1.1 Pianificazione urbanistica - P.zza due giugno,1 54033 - Carrara (MS)", style = 'FooterStyle')

    # f2=footer.add_paragraph()
    # f2.paragraph_format.space_after = Pt(0)
    # f2.paragraph_format.space_before = Pt(0)
    # f2.add_run("geom. Sergio Torri - 0585 641432 - sergio.torri@comune.carrara.ms.it", style = 'FooterStyle')

    f3=footer.add_paragraph()
    f3.paragraph_format.space_after = Pt(0)
    f3.paragraph_format.space_before = Pt(0)
    f3.add_run("geom. Carlo Alberto Nicolini - 0585 641252 - carloalberto.nicolini@comune.carrara.ms.it", style = 'FooterStyle')
    
    f4=footer.add_paragraph()
    f4.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    f4.paragraph_format.space_after = Pt(0)
    f4.paragraph_format.space_before = Pt(0)
    f4.add_run(str(request.user.username), style = 'FooterStyle')
   
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

    # Definisci il percorso dell'immagine
    image_name = 'logo_decorato.png'
    image_path = os.path.join('static/img/', image_name)
    
    # Inserisci l'immagine nel documento
        
    run = paragraph.add_run()
    run.add_picture(image_path, width=Inches(1.6))
    # Posiziona centralmente l'immagine
    paragraph_format = paragraph.paragraph_format
    paragraph_format.alignment = 1 # 1 - allineato centrato 0 - allineato a sx
            

# #    stampo i dati del cdu

    p1 = document.add_paragraph()
    p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p1.bold=True
    p1.add_run('Cronologia Piani e vincoli', style = 'CduStyle').bold = True


    table1 = document.add_table(rows=1, cols=4)
                # table.style = 'Light List Accent 6'
    table1.style = 'TableGrid'
    # trova i piani
    piani = Piano.objects.all().exclude(data_atto='1900-01-01').order_by('data_atto')
    for p in piani:
        

    
                
        hdr_cells = table1.rows[0].cells
        hdr_cells[0].text = 'nome'
        hdr_cells[1].text = 'atto'
       
        hdr_cells[2].text = 'efficacia'
        hdr_cells[3].text = 'fine efficacia'

        row_cells = table1.add_row().cells
        row_cells[0].text = str(p.name)
        row_cells[1].text = str(p.tipo_provvedimento) + ' ' + str(p.atto) + ' ' + str("%s" % p.data_atto.strftime('%d/%m/%Y')) 
        
        row_cells[2].text = str("%s" % p.data_in.strftime('%d/%m/%Y'))
        if p.data_out:
            row_cells[3].text = str("%s" % p.data_out.strftime('%d/%m/%Y'))
        else:
            row_cells[3].text = str('-')
        pass


                
                
    









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
