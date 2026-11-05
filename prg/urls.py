from django.urls import path, re_path
from . import views

app_name = 'prg'

urlpatterns = [
    path('',views.piani_list_view, name='piani_list_url'),
    path('add/', views.PianoAddView, name='piano_add_url'),
    path('edit/<int:id>/', views.PianoEditView, name='piano_edit_url'),
    path('detail/<int:id>/', views.PianoDetailView, name='piano_detail_url'),

    path('cdu/',views.cerdesurb_list_view, name='cerdesurb_list_url'),
    path('cdu_detail/<int:id>/', views.CduDetailView, name ='cerdesurb_detail_url'),
    path('cdu_edit/<int:id>/', views.CduEditView, name ='cerdesurb_edit_url'),
    path('add_cdu/<int:pk>/',views.cerdesurb_add_view, name='cerdesurb_add_url'),
    path('cdu_list/',views.cdu_list, name='cdu_list'),

    # path('add_istruttoria/<int:id>/', views.AddIstruttoriaView, name='add_istruttoria_url'),
    path('add_istruttoria/<int:id>/', views.DestinazioniIstruttoriaView, name='add_istruttoria_url'),
    path('istruttoria/<int:id>/', views.IstruttoriaDetailView, name="istruttoria_detail_url"),
    path('delete_istruttoria/<int:id>/', views.DeleteIstruttoriaView, name='delete_istruttoria_url'),
    path('add_destinazioni/<int:id>/', views.AddDestinazioniView, name='add_destinazioni_url'),
    path('edit_destinazione/<int:id>/', views.DestinazioneEditView, name='edit_destinazione_url'),
    path('search_destinazione/', views.SearchDestinazioneView, name='search_destinazione_url'),

    
    path('add_destinazione/<int:id>/', views.DestinazioneAddView, name='add_destinazione_url'),

    path('pdf_particella/<int:pk>/', views.pdf_particella, name='pdf_pparticella_url'), 

    # menu dropdown
    # path('load_piani/', views.load_piani, name='ajax_load_piani_url'),  # <-- this one here

    #   STAMPA DOCUMENTO
    path('docs/<int:id>/', views.CreateDoc, name='create_doc_url'),
    path('elenco_piani/', views.PrintPianieDestinazioni, name='printpianiurl'),

    # marche da bollo
   
    path('cdu_detail/<int:id>/marche/', views.marca_list, name='marca_list'),
    path('cdu_detail/<int:id>/marche/create/', views.marca_create, name='marca_create'),
    path('marca/<int:pk>/update/', views.marca_update, name='marca_update'),
    path('marca/<int:pk>/delete/', views.marca_delete, name='marca_delete'),
]

