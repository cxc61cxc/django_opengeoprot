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
from .models import Commissione
from protocollo.models import *

#   elenca le commissioni

def commissioni_list_view(request):
    pk = request.session.get('pk')

    commissioni = Commissione.objects.filter(pratica_id=pk).order_by('-commissione_date')
    tot_commissioni = commissioni.count()
    print('tot_commissioni',tot_commissioni, commissioni)
    context = {
        'vedi':"vedi",
        'commissioni': commissioni,
        'tot_commissioni':tot_commissioni,
    }
    return render(request,'paesaggio/commissioni_list_view.html', context)

@login_required
#@user_passes_test(lambda u: u.groups.filter(name='editor_settore_6').count() == 1, login_url='home')
#   aggiunge una commissione alla pratica ( un commissione per pratica )

def commissioni_add_view(request, pk=None):
    if pk is None:
        pk = request.session.get('pk')
    if not pk:
        return redirect('protocollo:index_pratiche_url')
    submitted = False

    # cerco i commissione per l'anno in corso
    today = datetime.date.today()
    year = today.year

#   propone il
    print('anno',year)
    #tot=#Pratica.objects.filter(tipo_pratica=obj.tipo_pratica).order_by('-code_p')[:1]
    numero = Commissione.objects.filter(commissione_date__icontains=year).count()
    # numero = Commissione.objects.filter(commissione_date__icontains=year).order_by('-commissione_number')[:1]

    if numero>0:
        nuova_commissione = numero+1
    else:
        nuova_commissione = 1
    print ('commissione',nuova_commissione) # stampa il numeroo dei commissione nell'anno

    # ora il numero di commissione proposto dovrebbe risultare 1 per il primo commissione dell'anno e proporre il nuovo numero se già presenti altri (nuova_commissione)

    print('aggiunge commissione a pratica id',pk)
    # pratica = Cerdesurb.objects.filter(pratica = pk)
    pratica= Pratica.objects.get(id=pk)
    tipo=pratica.tipo_pratica
    num_commissione=nuova_commissione
    print (tipo,'tipo_pratica',pratica.tipo_pratica)
    if str(tipo)=='paesaggistica': # esegue se la pratica è id=3 name = commissione    
        if request.method == "POST":

            print(num_commissione,'zero commissione',tipo)

            form = CommissioneForm(request.POST)
            if form.is_valid():
                    obj=form.save(commit=False)
                    obj.user = request.user
                    obj.pratica_id = pk
                    obj.save()
                    id = Commissione.objects.latest('id').id # ricava l'ID dell'ultimo soggetto
                    print('id',id)
                    return redirect('protocollo:pratica_detail_url' ,pk)
        else:
            form = CommissioneForm()
            if 'submitted' in request.GET:
                submitted = True
                print('id',id)

            return render(request,'paesaggio/commissione_add_view.html',{'form':form,'submitted':submitted, 'commissione_proposto':nuova_commissione})
    else :
        print('non arriva nessun dato')
        pass

    return redirect('protocollo:pratica_detail_url' ,pk)



def commissione_edit_view(request,id):
    pk = request.session.get('pk')
    commissione = Commissione.objects.get(id=id)
    if request.method == 'POST':
       form = CommissioneForm(request.POST, instance=commissione)
       if form.is_valid():
           obj=form.save(commit=False)
           obj.user_id = request.user.id
           # update the existing `Commissione` in the database
           obj.save()
           # redirect to the detail page of the `Commissione` we just updated
           return redirect('protocollo:pratica_detail_url', pk)
    else:
        form = CommissioneForm(instance=commissione)

    return render(request,
                'paesaggio/commissione_edit_view.html',
                {'form': form})