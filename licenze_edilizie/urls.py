from django.urls import path
from . import views

app_name = 'licenze_edilizie'

urlpatterns = [
    path('', views.lista_registri, name='lista'),
    path('pdf/<int:pk>/', views.download_pdf, name='download'),
]
