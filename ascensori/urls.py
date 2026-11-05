from django.urls import path, re_path
from . import views



app_name = 'ascensori'

urlpatterns = [
   #################################################
    #           IMPIANTO
    #################################################

    path('add_impianto/<int:pk>/',views.ImpiantoAddView, name='impianto_add_url'),
    path('edit_impianto/<int:id>/',views.ImpiantoEditView, name='impianto_edit_url'),

    #################################################
    #           MATRICOLA
    #################################################
    path('matricole/',views.MatricolaListView, name='matricola_list_url'),
    path('add_matricola/<int:pk>/',views.MatricolaAddView, name='matricola_add_url'),
    path('edit_matricola/<int:id>/',views.MatricolaEditView, name='matricola_edit_url'),
    path('detail_matricola/<int:id>/',views.MatricolaDetailView, name='matricola_detail_url'),
    path('stampa_matricola/<int:id>/',views.CreateMatricolaRtf, name='create_matricola_url'),
    path('ordinanza/<int:id>/',views.CreateOrdinanzaRtf, name='create_ordinanza_url'),
    path('ordinanza_esito_negativo/<int:id>/',views.CreateOrdinanzaVerificaNegativa, name='create_ordinanza_esito_negativo_url'),
    ]
