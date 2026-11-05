from django.shortcuts import render,redirect
from django.db.models import Q

from protocollo.models import Particella
from .views import *
from .forms import ParticellaEditForm

# Create your views here.
from catasto.models import Particelle

def home_particelle(request):

    if request.method == "POST":
        # assegno le variabili arrivate da POST
        foglio = request.POST["foglio"]
        mappale  = request.POST["mappale"]
        
        particelle = Particelle.objects.filter(   Q(foglio__endswith=foglio) & 
                                                Q(mappale__iexact=mappale) )
        # residents = Residenti.objects.all()
        tot_res = particelle.count()
        # print (particelle)
        return render(request,'catasto/particelle_list.html', {'residents':particelle, 'tot_res':tot_res})
    else:
        return render(request,'catasto/particelle_list.html')
    



def ParticellaEditView(request,id):
    particella = Particelle.objects.get(id=id)
    pk = request.session.get('pk')
    if request.method == 'POST':
       form = ParticellaEditForm(request.POST, instance=particella)
       if form.is_valid():
           # update the existing `Pratica` in the database
           form.save()
           new_map = Particella.objects.latest('id').id
           print('nuovo id',new_map)
           # redirect to the detail page of the `Pratica` we just updated
           return redirect('protocollo:pratica_detail_url', id)
    else:
        form = ParticellaEditForm(instance=particella)

    return render(request,
                'catasto/particella_edit.html',
                {'form': form})