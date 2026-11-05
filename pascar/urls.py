# urls.py

from django.urls import path, re_path
from . import views

# from .views import StreetAutocompleteView

app_name = 'pascar'


urlpatterns = [
    path('', views.passi_carrai, name='passi_carrai_url'), # lista tutte i passi carrai ( concessioni )
    path('add_pcar/',views.PcarAddView, name='pcar_add_url'),
    path('pcar_edit/<int:id>/', views.PcarEditView, name ='pcar_edit_url'),


]