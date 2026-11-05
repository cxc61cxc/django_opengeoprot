from django.shortcuts import render

# Create your views here.
from .models import *






def CiviciListView(request):
    context={}
    civici = Civici.objects.all().order_by('street')
    print(civici)

    context={
        'civici':civici
    }

    return render(request, 'viario/list_civici.html', context)