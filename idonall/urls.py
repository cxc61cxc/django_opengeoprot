from django.urls import path, re_path
from . import views

app_name = 'idonall'

urlpatterns = [
    
    # path('',views.IdonListView, name='idon_list_url'),
    # path('idon_detail/<int:id>/', views.IdonDetailView, name ='idon_detail_url'),
    path('edit_istruttoria/<int:id>/', views.IstruttoriaEditView, name ='istruttoria_edit_url'),
    path('add_istruttoria/<int:pk>/',views.IstruttoriaAddView, name='istruttoria_add_url'),
    path('add_certificato/<int:pk>/',views.IdonallAdd, name='certificato_add_url'),
    path('edit_certificato/<int:id>/',views.IdonEditView, name='certificato_edit_url'),
    path('print_certificato/<int:id>/',views.CreateIdonallView, name='certificato_print_url'),
    # path('stampa_idon/<int:id>/',views.CreateIdonView, name='create_idon_url'),
    ]
