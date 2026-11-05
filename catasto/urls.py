from django.urls import path, re_path
from . import views
from .views import *

app_name = 'catasto'

urlpatterns = [
    path('', views.home_particelle, name='home_particelle_url'), # elenco residenti
    path('particella_edit/<int:id>/', views.ParticellaEditView, name='particella_edit_url'),

    # path('', views.ParticelleAllView, name='particelle_list_all_url'), # pagina principale
    # path('search/', views.ParticelleSearchView, name='particelle_search_url'), # pagina principale
    # path('particella_edit/<int:id>/', views.ParticellaEditView, name='particella_edit_url'),
]