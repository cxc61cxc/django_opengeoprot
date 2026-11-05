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
from num2words import num2words








@login_required
@user_passes_test(lambda u: u.is_superuser or u.groups.filter(name__in=['editor_settore_6', 'editor_settore_1', 'user_settore_6', 'user_settore_1']).exists(), login_url='home:index')


# @user_passes_test(lambda u: u.groups.filter(name='editor_settore_6').count() == 1, login_url='home')
#   aggiunge una IDONEITA legata alla pratica 

def AddFotovoltaico(request, pratica_pk=None):
    print('777ggd555dr')
    is_editor = can_edit(request.user)

    submitted = False
    # RIPRISTINO: in passato il pk veniva letto da request.session['pk'],
    # ma quel valore non veniva mai impostato -> Pratica.DoesNotExist.
    # Ora il pk della pratica arriva dall'URL; fallback alla sessione per compatibilità.
    pk = pratica_pk or request.session.get('pk')
    richiedente=[]
    print(pk,'77d6dy',request.user)
    print('aggiunge i dati della convenzione',pk)
    # pratica = Pcar.objects.filter(pratica = pk)
    pratica = get_object_or_404(Pratica, id=pk)

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
     
    if request.method == "POST":
        form = ImpFotForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.pratica_id = pk
            obj.user = request.user
            if obj.mod1 == True or obj.mod2 == True:
                obj.allp  = False
            elif obj.allp == True:
                obj.mod1 = False
                obj.mod2 = False
            obj.pratica_id = pk
            obj.user = request.user
            try:
                obj.save()
                print('Dati salvati correttamente')
                return redirect('protocollo:pratica_detail_url', pk)
            except Exception as e:
                print('Errore nel salvataggio:', e)
                # Re-render form with error
                context = {
                    'is_editor': is_editor,
                    'form': form,
                    'pratica': pratica,
                    'pk': pk,
                    'richiedente': richiedente,
                    'error': str(e),
                }
                return render(request, 'fotovoltaico/add_fot.html', context)
        else:
            print('Il form non è valido:', form.errors)
            # Re-render form with validation errors
            context = {
                'is_editor': is_editor,
                'form': form,
                'pratica': pratica,
                'pk': pk,
                'richiedente': richiedente,
            }
            return render(request, 'fotovoltaico/add_fot.html', context)
    else:
        form = ImpFotForm()
        context = {
                'is_editor':is_editor,
                'form':form,
                'pratica':pratica,
                'pk':pk, 
                'richiedente':richiedente,
        }
                
        return render(request,'fotovoltaico/add_fot.html',context)
    

@login_required
@user_passes_test(lambda u: u.groups.filter(name__in=['editor_settore_6', 'editor_settore_1', 'user_settore_6', 'user_settore_1']).exists(), login_url='home:index')


def EditFotovoltaico(request, pk, pratica_pk=None):
    print('777ggd555dr')
    is_editor = can_edit(request.user)

    # RIPRISTINO: il pk della pratica arriva dall'URL; fallback alla sessione per compatibilità.
    pratica_id = pratica_pk or request.session.get('pk')
    richiedente = []

    print(pratica_id,'77d6dy',request.user)
    print('Modifica pratica con ID:', pratica_id)

    pratica = get_object_or_404(Pratica, id=pratica_id)
    tipo = pratica.tipo_pratica_id

    anaprat = Anaprat.objects.filter(pratica_id=pratica_id)
    for s in anaprat:
        soggetti = {}
        sogg = Soggetto.objects.get(id=s.soggetto_id)
        soggetti['id_anaprat'] = s.id
        soggetti['cognome'] = sogg.cognome
        soggetti['nome'] = sogg.nome
        richiedente.append(soggetti)

    # Carica il record esistente da modificare
    impfot_instance = ImpFot.objects.filter(pratica_id=pratica_id, pk=pk).first()
    if not impfot_instance:
        # Gestisci caso record non trovato (esempio redirect o 404)
        return redirect('some_view_name')

    if request.method == "POST":
        form = ImpFotForm(request.POST, instance=impfot_instance)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.pratica_id = pratica_id
            obj.user = request.user
            # Logica di validazione tra mod1, mod2, allp
            if obj.mod1 or obj.mod2:
                obj.allp = False
            elif obj.allp:
                obj.mod1 = False
                obj.mod2 = False
            try:
                obj.save()
                print('Dati aggiornati correttamente')
                return redirect('protocollo:pratica_detail_url', pratica_id)
            except Exception as e:
                print('Errore nel salvataggio:', e)
        else:
            print('Il form non è valido:', form.errors)
    else:
        form = ImpFotForm(instance=impfot_instance)

    context = {
        'is_editor': is_editor,
        'form': form,
        'pratica': pratica,
        'pk': pk,
        'richiedente': richiedente,
    }
    return render(request, 'fotovoltaico/add_fot.html', context)
    
