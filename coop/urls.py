# urls.py

from django.urls import path, re_path
from . import views

# from .views import StreetAutocompleteView

app_name = 'coop'


urlpatterns = [
    path ('add/<int:pk>/',views.ConvAddView, name = 'add_view_url'),
    path ('edit/<int:id>/',views.ConvEditView, name ='edit_view_url'),
    path ('all_coop/<int:id>/', views.AllCoopPrint, name ='all_coop_print_url'),
    path ('comunicazione/<int:id>/', views.RispostaCoop, name ='importi_coop_print_url'),
    path ('integrazione/<int:id>/', views.RichiestaIntegrazionePeep, name ='integrazione_istanza_url'),
    path ('determina/<int:id>/', views.Determina, name ='determina_svincolo_url'),
    path ('schema/<int:id>/', views.SchemaConv, name ='schema_conv_url'),
    path ('dichiarazione_rup/<int:id>/', views.DichiarazioneRup, name ='dichiarazione_rup_url'), # dichiarazione rup per assenza conflitto di interessi
    # path ('comicazione_superficie/<int:id>/', views.RispostaCoopSuperficie, name ='importi_sup_coop_print_url'),
    # path ('detail/<int:id>/',views.ConvDetailView, name ='detail_view_url'),
    # path('', views.Coop, name='passi_carrai_url'), # lista tutte i passi carrai ( concessioni )
    # path('add_pcar/',views.PcarAddView, name='pcar_add_url'),
    # path('pcar_edit/<int:id>/', views.PcarEditView, name ='pcar_edit_url'),
    ############################################################
    #   ACCETTAZIONE
    ############################################################
    path ('add_accettazione/<int:pk>/',views.AddAccettazione, name = 'add_accettazione_view_url'),
    path ('edit_accettazione/<int:id>/',views.EditAccettazione, name = 'edit_accettazione_view_url'),

     ############################################################
    #   RATE
    ############################################################
    # path ('scadenze/<int:pk>/', views.ScadenzeList, name = 'scadenze_list_url'),
    # path ('add_rata/<int:id>/',views.AddScadenza, name = 'add_rata_view_url'),
    path('scadenze/new/<int:id>', views.scadenze_create, name='scadenze_create'),
    path('scadenze/edit/<int:id>/', views.scadenze_update, name='scadenze_update'),
    path('scadenze/delete/<int:id>/', views.scadenze_delete, name='scadenze_delete'),
    path('versamenti/', views.versamenti_report, name='versamenti_report_url'),


]