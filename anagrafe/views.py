from django.shortcuts import render, redirect
from django.db.models import Q
from django.db.models import Count

from .forms import ResidenteEditForm
from protocollo.forms import SoggettoForm
from .models import Residenti
# from protocollo.forms import AddSoggettoAnagrafeForm

# Create your views here.

def home_residenti(request):

    if request.method == "POST":
        # assegno le variabili arrivate da POST
        cognome = request.POST["cognome"]
        nome  = request.POST["nome"]
        dug  = request.POST["dug"]
        descrizione  = request.POST["descrizione"]
        civico  = request.POST["civico"]

        residents = Residenti.objects.filter(   Q(cognome__icontains=cognome) & 
                                                Q(nome__icontains=nome) &
                                                Q(dug__icontains=dug) &
                                                Q(descrizione__icontains= descrizione) &
                                                Q(civico__icontains=civico)).order_by('nome')
        # residents = Residenti.objects.all()
        tot_res = residents.count()
        # print (residents)
        if tot_res>0:
            context={'residents':residents, 
                     'tot_res':tot_res,
                     'cognome':cognome,
                     'nome':nome,
                     }

            return render(request,'anagrafe/anagrafe_list.html', context)
        else:
            form = SoggettoForm()
            return render(request,'protocollo/add_soggetto.html',{'form':form})
    else:
        return render(request,'anagrafe/anagrafe_list.html')
    

def ResidenteEditView(request,id):
    soggetto = Residenti.objects.get(id=id)
    if request.method == 'POST':
       print('arriva a questo punto.541354f7as4fg4s')
       form = ResidenteEditForm(request.POST, instance=soggetto)
       if form.is_valid():
           # update the existing `Pratica` in the database
           form.save()
           # redirect to the detail page of the `Pratica` we just updated
           return redirect('protocollo:pratica_detail_url', id)
    else:
        form = ResidenteEditForm(instance=soggetto)

        return render(request,'anagrafe/anagrafe_edit.html',{'form': form})
