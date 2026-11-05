# urls.py

from django.urls import path, re_path
from . import views

# from .views import StreetAutocompleteView

app_name = 'protocollo'


urlpatterns = [
    path('', views.index, name='index_pratiche_url'), # lista tutte le pratiche
    path('pratica_add/', views.pratica_add, name = 'pratica_add_url'), # aggiunge pratica
    path('mie_pratiche/', views.mie_pratiche, name='mie_pratiche_url'), # pratiche dell'utente corrente
    path('pratica_detail/<int:pk>/', views.pratica_detail, name = 'pratica_detail_url'), # dettaglio pratica
    path('pratica_detail_consigliere/<int:pk>/', views.pratica_detail_consigliere, name='pratica_detail_consigliere_url'),
    path('pratica_history/<int:pk>/', views.pratica_history, name='pratica_history_url'), # storico modifiche pratica
    path('pratica_edit/<int:pk>/', views.pratica_edit, name = 'pratica_edit_url'), # edita pratica
    path('pratica_delete/<int:pk>/', views.pratica_delete, name = 'pratica_delete_url'), # elimina pratica
    path('pdf_pratica/<int:pk>/', views.pdf_pratica, name='pdf_pratica_url'), 
    path('duplica_pratica/<int:id>/', views.Duplica, name='duplica_pratica_url'), # duplica le pratiche COOPERATIVA in nuovi SVINCOLI
    path('duplica_idonall/<int:id>/', views.DuplicaIdonall, name='duplica_idonall_url'), # duplica le pratiche IDONEITA ALLOGGIATIVE 
    path('duplica_ascensore/<int:id>/', views.DuplicaAscensore, name='duplica_ascensore_url'), # duplica le pratiche ASCENSORE 

    # path('add_nota/<int:pk>/', views.pratica_add_annotazioni, name='pratica_add_annotazioni_url'), 
    # path('duplica_idonall/<int:id>/', views.DuplicaIdonall, name='duplica_idonall_url'), 
    
    #####################################################################################################
    #   street
    #####################################################################################################
    path('street-autocomplete/', views.StreetAutocompleteView.as_view(), name='street_autocomplete'),
    #####################################################################################################
    # upload
    #####################################################################################################
    
    path('pratica_detail/<int:pk>/upload/', views.upload_file, name='upload_url'),
    path('pratica_detail/<int:pk>/ubica/', views.Ubica, name='ubica_url'),

    #####################################################################################################
    # SOGGETTI
    #####################################################################################################
    path('soggetti_pratica/<int:pk>/', views.soggetti_pratica_list, name='soggetti_pratica_list_url'), # lista tutte le pratiche
    path('soggetti_list/<int:pk>/', views.list_soggetti_view, name= 'soggetti_list_url'), # pk-aware (multi-tab)
    path('soggetto_pratica_aggiungi/<int:id>/<int:pk>/', views.aggiungi_soggetto_a_pratica_view, name='soggetto_pratica_aggiungi_url'), # pk-aware (multi-tab)
    path('aggiungi_residente_pratica/<int:id>/<int:pk>/', views.aggiungi_residente_a_pratica_view, name='aggiungi_residente_pratica_url'), # pk-aware
    path('aggiungi_residente_edit/<int:id>/<int:pk>/', views.aggiungi_residente_edit_view, name='aggiungi_residente_edit_url'), # pk-aware
    path('soggetto_pratica_detail/<int:id>/<int:pk>/', views.SoggettoPraticaDetailView, name= 'soggetto_pratica_detail_url'), # pk-aware
    path('add_soggetto_pratica/<int:pk>/', views.add_soggetto_pratica_view, name= 'add_soggetto_pratica_url'), # pk-aware
    path('soggetto_pratica_delete/<int:id>/<int:pk>/', views.soggetto_pratica_delete, name = 'soggetto_pratica_delete_url'), # pk-aware
    
    path('soggetto_pratica_sostituisci/<int:id>/', views.sostituisci_soggetto_view, name='soggetto_pratica_sostituisci_url'), # sostituisce soggetto nella pratica
    
    path('add_soggetto/<int:pk>/', views.add_soggetto_view, name='add_soggetto_url'), # pk-aware
    path('soggetto_detail/<int:id>/<int:pk>/',views.SoggettoDetailView, name='soggetto_detail_url'), # pk-aware
    path('soggetto_detail/<int:id>/',views.SoggettoDetailView, name='soggetto_detail_nopk_url'), # read-only, da ricerca professionisti
    path('soggetto_edit/<int:id>/<int:pk>/',views.SoggettoEditView, name='soggetto_edit_url'), # pk-aware
    path('_pratiche_soggetto_all/<int:id>/<int:pk>/',views.PraticheSoggettoList, name='pratiche_soggetto_all_url'), # pk-aware
    
    # path('ricerca_pratica/', views.ricerca_pratica, name='ricerca_pratica'),

    path('search/',views.SearchPratica,name='search_url'),
    path('search/particella/',views.SearchParticella,name='search_particella_url'),
    path('search/protocollo/',views.SearchProt, name='search_protocollo_url'),
    path('search/documento/',views.SearchDocProt, name='search_documento_url'),
    path('search/documento/testo/',views.cerca_documenti_testo, name='cerca_documenti_testo_url'),

    path('search/stato_pratica/',views.SearchStato, name='search_stato_url'),
    path('riepilogo-cdu/',views.riepilogo_cdu,name='riepilogo_cdu_url'),
    path('riepilogo-cdu/pdf/',views.riepilogo_cdu_pdf,name='riepilogo_cdu_pdf_url'),
    path('riepilogo-idonall/',views.riepilogo_idonall,name='riepilogo_idonall_url'),
    path('riepilogo-idonall/pdf/',views.riepilogo_idonall_pdf,name='riepilogo_idonall_pdf_url'),

    path('search/tipo_pratica/<int:id>/',views.SearchTipoPratica,name='search_pratica_tipo_url'),
    
    path('search/matricola/',views.SearchMatricola,name='search_matricola_url'),
    path('search/impianto/',views.SearchImpianto,name='search_impianto_url'),
    path('search/cdu/',views.SearchCdu,name='search_cdu_url'),
    path('search/idoneita/',views.SearchIdonall,name='search_idoneita_url'),
    path('search_rati/', views.SearchRatei, name = 'pratiche_coop_rateizzate'),

    #####################################################################################################
    # PARTICELLE 
    #####################################################################################################

    path('particelle_list/<int:pk>/', views.list_particelle_view, name ='particelle_list_url'), # pk-aware
    path('add_particella_pratica/', views.add_particella_pratica_view, name= 'add_particella_pratica_url'), # aggiunge soggetto dalla pratica
    path('particella_pratica_detail/<int:id>/<int:pk>/', views.ParticellaPraticaDetailView, name= 'particella_pratica_detail_url'), # pk-aware
    path('add_particella/<int:pk>/', views.add_particella_view, name='add_particella_url'), # pk-aware
    path('particella_pratica_delete/<int:id>/<int:pk>/', views.particella_pratica_delete, name = 'particella_pratica_delete_url'), # pk-aware
    path('particella_pratica_delete/<int:id>/', views.particella_pratica_delete, name = 'particella_pratica_delete_url'), # elimina soggetto dalla pratica
    # path('mappa/', views.mappa_particelle, name='mappa_particelle'),

    ####################################################################################################
    #   DIARIO
    ####################################################################################################
    path('add_diario/<int:pk>/', views.AddDiario, name='add_diario_url'), # pk-aware
    path('edit_diario/<int:id>/', views.EditDiario, name='edit_diario_url'), # edita voce di diario
    # path('list_diario/<int:pk>/', views.ListaDiario, name='list_diario_url'),
    path('list_diario/<int:pk>/', views.DiarioList, name='pdf_diario_url'), # pk-aware


    ####################################################################################################
    #   ACCETTAZIONE
    ####################################################################################################




    #####################################################################################################
    # TIPO DI PRATICA 
    #####################################################################################################

    path('tipopratiche_list/', views.tipopratiche_list, name ='tipopratiche_list_url'), #idem come per soggetto.... su particelleS) 
    path('add_tipopratica/', views.add_tipopratica_view, name ='add_tipopratica_view_url'), #idem come per soggetto.... su particelleS) 
    path('tipopratica_edit/<int:id>/', views.tipopratica_edit, name ='tipopratica_edit_url'), #idem come per soggetto.... su particelleS) 
    path('tipopratica_delete/<int:id>/', views.tipopratica_delete, name='tipopratica_delete_url'), # elimina tipo pratica
    path('ajax/settore/<int:settore_id>/servizi/', views.get_servizi_by_settore, name='ajax_servizi_by_settore'),
    path('ajax/servizio/<int:servizio_id>/uo/', views.get_uo_by_servizio, name='ajax_uo_by_servizio'),

    path('mappa_tipo/<int:tipo_id>/', views.mappa_tipo_pratica, name='mappa_tipo_pratica_url'),
    # path('pratica/mappa/', views.pratica_mappa, name='pratica_mappa_url'),
    path('mappa_results/', views.searchprotmap, name='mappa_results_url'),

    path('mappa_area/', views.mappa_area, name='mappa_area_url'),
    path('pratiche_lista_area/', views.pratiche_lista_area, name='pratiche_lista_area_url'),
    path('pratiche_punto_lista/', views.pratiche_punto_lista, name='pratiche_punto_lista_url'),
    path('mappa_area/sviluppo/', views.mappa_area_sviluppo, name='mappa_area_sviluppo_url'),
    path('mappa_area/sviluppo/risultati/', views.mappa_area_sviluppo_risultati, name='mappa_area_sviluppo_risultati_url'),
    path('particella/geojson/', views.particella_geojson, name='particella_geojson_url'),
    path('particella/<int:pk>/informativa/', views.particella_informativa, name='particella_informativa_url'),
    
    # path('', views.viario_autocomplete, name='viario_autocomplete'),
    
    # Relazioni a Grafo
    path('graph/data/', views.graph_relazioni_data, name='graph_relazioni_data_url'),
    path('graph/', views.graph_relazioni_view, name='graph_relazioni_url'),
    
    # API GeoJSON per particelle del catasto generale nei dintorni
    path('catasto_nearby/', views.catasto_geojson_nearby, name='catasto_geojson_nearby_url'),
    path('catasto_bbox/', views.catasto_geojson_bbox, name='catasto_geojson_bbox_url'),
    path('pratiche_nearby/', views.pratiche_geojson_bbox, name='pratiche_geojson_bbox_url'),
    path('nota_osm/salva/', views.salva_nota_osm, name='nota_osm_salva_url'),
    path('nota_osm/aggiorna/', views.aggiorna_nota_osm, name='nota_osm_aggiorna_url'),
    path('nota_osm/lista/', views.nota_osm_lista, name='nota_osm_lista_url'),
    path('nota_osm/elimina/', views.elimina_nota_osm, name='nota_osm_elimina_url'),
    path('nota/<int:pk>/modifica/', views.nota_modifica, name='nota_modifica_url'),
    path('nota/<int:pk>/elimina/', views.nota_elimina, name='nota_elimina_url'),
    path('pratiche_vicine_list/', views.pratiche_vicine_list, name='pratiche_vicine_list_url'),

    path('dashboard/', views.dashboard_riepilogo, name = 'manager_dashboard'),
    path('pratiche-chart/', views.pratiche_chart_view, name='pratiche_chart'),
    path('pratiche-chart/<int:tipo_pratica_id>/', views.pratiche_chart_view, name='pratiche_chart_by_tipo'),

    path('report/accessi/', views.accessi_report, name='accessi_report'),
    path('report/accessi/<str:username>/', views.accessi_report_user, name='accessi_report_user'),
    path('report/poc_2022/pdf/', views.report_poc_2022_pdf, name='report_poc_2022_pdf'),
    path('report/istrcomm_poc/pdf/', views.report_istrcomm_poc_pdf, name='report_istrcomm_poc_pdf'),
    path('document/<int:pk>/', views.serve_documento, name='serve_documento'),

    # professionisti
    path('soggetti/', views.professionisti_list_view, name='professionisti_list_url'),

   
]
