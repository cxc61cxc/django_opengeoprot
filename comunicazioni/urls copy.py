from django.urls import path, re_path
from . import views

app_name = 'comunicazioni'



urlpatterns = [
    path('', views.ModelloListView.as_view(), name='all'),
    path('modello/<int:pk>/detail', views.ModelloDetailView.as_view(), name='modello_detail'),
    path('modello/create/', views.ModelloCreateView.as_view(), name='modello_create'),
    path('modello/<int:pk>/update/', views.ModelloUpdateView.as_view(), name='modello_update'),
    path('modello/<int:pk>/delete/', views.ModelloDeleteView.as_view(), name='modello_delete'),

    path('modelli/',views.List, name='List_url'),
    path('paesaggistica/parere/',views.ParerePreventivoPaesaggio, name = 'ParerePreventivoPaesaggio_url'),
    path('suap/avvio/',views.SuapAvvioProcNoSosp, name = 'SuapAvvioProcNoSosp_url'),
    path('suap/avvio_sosp/',views.SuapAvvioProcSosp, name = 'SuapAvvioProcSosp_url'),
    path('suap/parere/',views.RichiestaParere, name = 'RichiestaParere_url'),
    path('cartellina/',views.Cartellina, name = 'Cartellina_url'),
    path('pdc/avvio/',views.PdcAvvioProc, name = 'PdcAvvioProc_url'),
    path('dirsup/calcolo/',views.DirSupCalc, name = 'dir_sup_calc_url'),
    path('ascensore/',views.Risposta_vvff, name = 'Risposta_vvff_url'),
]