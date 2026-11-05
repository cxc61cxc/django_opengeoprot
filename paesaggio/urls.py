from django.urls import path, re_path
from . import views

app_name = 'paesaggio'

urlpatterns = [
    path('paesaggio/',views.commissioni_list_view, name='commissioni_list_url'),
    path('add_commissione/<int:pk>/',views.commissioni_add_view, name='commissione_add_url'),
    path('edit_commissione/<int:id>/',views.commissione_edit_view, name='commissione_edit_url'),

    ### importato da prg/urls.py ###

    # path('',views.piani_list_view, name='piani_list_url'),
    # path('add/', views.PianoAddView, name='piano_add_url'),
    # path('edit/<int:id>/', views.PianoEditView, name='piano_edit_url'),
    # path('detail/<int:id>/', views.PianoDetailView, name='piano_detail_url'),

    # path('cdu/',views.cerdesurb_list_view, name='cerdesurb_list_url'),
    # path('cdu_detail/<int:id>/', views.CduDetailView, name ='cerdesurb_detail_url'),
    # path('cdu_edit/<int:id>/', views.CduEditView, name ='cerdesurb_edit_url'),
    # path('add_cdu/',views.cerdesurb_add_view, name='cerdesurb_add_url'),

    # # path('add_istruttoria/<int:id>/', views.AddIstruttoriaView, name='add_istruttoria_url'),
    # path('add_istruttoria/<int:id>/', views.DestinazioniIstruttoriaView, name='add_istruttoria_url'),
    # path('istruttoria/<int:id>/', views.IstruttoriaDetailView, name="istruttoria_detail_url"),
    # path('delete_istruttoria/<int:id>/', views.DeleteIstruttoriaView, name='delete_istruttoria_url'),
    # path('add_destinazioni/<int:id>/', views.AddDestinazioniView, name='add_destinazioni_url'),
    # path('edit_destinazione/<int:id>/', views.DestinazioneEditView, name='edit_destinazione_url'),

    # path('pdf_particella/<int:pk>/', views.pdf_particella, name='pdf_pparticella_url'), 

    # # menu dropdown
    # # path('load_piani/', views.load_piani, name='ajax_load_piani_url'),  # <-- this one here

    # #   STAMPA DOCUMENTO
    # path('docs/<int:id>/', views.CreateDoc, name='create_doc_url')
]

