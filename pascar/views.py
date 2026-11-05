from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test


from pascar.models import Passocarraio
from protocollo.models import Pratica
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

@login_required
# @user_passes_test(lambda u: u.groups.filter(name='editor').count() == 1, login_url='home')
#   aggiunge un Pascar legato alla pratica ( un Pascar per pratica )
def passi_carrai(request):
    pc=Passocarraio.objects.all()
    return render(request,'pascar/passi_carrai_list.html')




@login_required
@user_passes_test(lambda u: u.groups.filter(name='editor').count() == 1, login_url='home:index')


# @user_passes_test(lambda u: u.groups.filter(name='editor').count() == 1, login_url='home')
#   aggiunge una IDONEITA legata alla pratica 

def PcarAddView(request):
    is_editor = can_edit(request.user)

    submitted = False
    pk = request.session.get('pk')

    # provo a impostare il numero di Passo carraio
    # cerco i pcar per l'anno in corso
    today = datetime.date.today()
    year = today.year

#   propone il
    print('anno',year)
    numero = Passocarraio.objects.filter(data_crea__icontains=year).count()
    if numero>0:
        nuovo_pcar = numero+1
    else:
        nuovo_pcar = 1
    print ('pcar',nuovo_pcar) # stampa il numeroo dei pcar nell'anno

    # ora il numero di pcar proposto dovrebbe risultare 1 per il primo pcar dell'anno e proporre il nuovo numero se già presenti altri (nuovo_pcar)

    print('aggiunge pcar a pratica id',pk)
    # pratica = Pcar.objects.filter(pratica = pk)
    pratica= Pratica.objects.get(id=pk)
    tipo=pratica.tipo_pratica_id
    num_pcar=nuovo_pcar
    print (tipo,'tipo_pratica',pratica.tipo_pratica)
    if tipo == 21: # esegue se la pratica è id=3 name = pcar    
        if request.method == "POST":

            print(num_pcar,'zero pcar',tipo)

            form = PcarForm(request.POST)
            if form.is_valid():
                    obj=form.save(commit=False)
                    obj.pratica_id = pk
                    obj.save()
                    pk = Passocarraio.objects.latest('id').id # ricava l'ID dell'ultimo soggetto
                    print('id',id)
                    return redirect('protocollo:pratica_detail_url' ,pratica.id)
                    
        else:
            form = PcarForm()
            context = {'form':form,
                       'pratica':pratica,
                       'pk':pk, 
                       'pcar_proposto':nuovo_pcar,
                       'is_editor':is_editor,
                       }
            if 'submitted' in request.GET:
                submitted = True
                print('id_add',id)

            return render(request,'pascar/pcar_add_view.html',context)
    else :
        print('non arriva nessun dato')
        pass




@login_required
def PcarEditView(request, id):
    pcar_edit=[]
    pcar = Passocarraio.objects.get(id=id)
    print('passo carraio',pcar)
    pk= pcar.pratica_id
    print('pk',pk)
    if request.method == 'POST':
       form = PcarForm(request.POST, instance=pcar)
       if form.is_valid():
           # update the existing `Pratica` in the database
           form.save()
           # redirect to the detail page of the `Pratica` we just updated
           return redirect('protocollo:pratica_detail_url', pk )
    else:
        form = PcarForm(instance=pcar)

    return render(request,'pascar/pcar_edit_view.html',{'form': form, 'pcar':pcar})