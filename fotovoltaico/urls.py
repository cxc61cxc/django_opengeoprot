from django.urls import path, re_path
from . import views

app_name = 'fotovoltaico'

urlpatterns = [
    
    path('add_fotovoltaico/<int:pratica_pk>/', views.AddFotovoltaico, name='add_fot_url'),
    path('edit_fotovoltaico/<int:pk>/<int:pratica_pk>/', views.EditFotovoltaico, name='edit_fot_url'),
   
   
    ]
