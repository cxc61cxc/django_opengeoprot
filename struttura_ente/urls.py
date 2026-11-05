from django.urls import path
from . import views

app_name = 'struttura_ente'

urlpatterns = [
    path('', views.settore_list, name='settore_list'),
    path('new/', views.settore_create, name='settore_create'),
    path('<int:pk>/edit/', views.settore_edit, name='settore_edit'),
    path('<int:pk>/delete/', views.settore_delete, name='settore_delete'),
    path('<int:pk>/storico/', views.settore_storico, name='settore_storico'),
    path('<int:settore_pk>/servizi/new/', views.servizio_create, name='servizio_create'),
    path('servizi/<int:pk>/edit/', views.servizio_edit, name='servizio_edit'),
    path('servizi/<int:pk>/delete/', views.servizio_delete, name='servizio_delete'),
    path('servizi/<int:pk>/storico/', views.servizio_storico, name='servizio_storico'),
    path('servizi/<int:servizio_pk>/attivita/new/', views.attivita_create, name='attivita_create'),
    path('attivita/<int:pk>/edit/', views.attivita_edit, name='attivita_edit'),
    path('attivita/<int:pk>/delete/', views.attivita_delete, name='attivita_delete'),
    path('attivita/<int:pk>/storico/', views.attivita_storico, name='attivita_storico'),
]