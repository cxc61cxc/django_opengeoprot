from django.urls import path, re_path
from . import views

app_name = 'suap'

urlpatterns = [
    path('',views.PauListView, name='pau_list_url'),
    path('pau_detail/<int:id>/', views.PauDetailView, name ='pau_detail_url'),
    path('pau_edit/<int:id>/', views.PauEditView, name ='pau_edit_url'),
    path('add_pau/',views.PauAddView, name='pau_add_url'),
    path('stampa_pau/<int:id>/',views.CreatePauView, name='create_pau_url'),
    ]