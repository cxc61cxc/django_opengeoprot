from django.urls import path

from . import views

app_name = 'osm_note'

urlpatterns = [
    path('', views.mappa_strade, name='mappa_strade'),
    path('strade.json', views.strade_json, name='strade_json'),
    path('importa/', views.importa_strade, name='importa_strade'),
    path('segna-processata/', views.segna_processata, name='segna_processata'),
]
