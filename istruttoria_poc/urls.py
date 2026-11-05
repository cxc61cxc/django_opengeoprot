from django.urls import path
from . import views

app_name = 'istruttoria_poc'

urlpatterns = [
    path('pratica/<int:pratica_id>/', views.istruttoria_detail, name='istruttoria_detail'),
    path('pratica/<int:pratica_id>/delete/', views.istruttoria_delete, name='istruttoria_delete'),
    path('pratica/<int:pratica_id>/comunicazione/', views.istrcomm_detail, name='istrcomm_detail'),
    path('pratica/<int:pratica_id>/comunicazione/delete/', views.istrcomm_delete, name='istrcomm_delete'),
    path('pratica/<int:pratica_id>/consulenza/', views.istrcons_detail, name='istrcons_detail'),
    path('pratica/<int:pratica_id>/consulenza/delete/', views.istrcons_delete, name='istrcons_delete'),
]