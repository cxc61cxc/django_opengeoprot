from django.urls import path, re_path

from . import views

app_name = 'viario'

urlpatterns = [
    path('',views.CiviciListView, name='civici_list_url'),
]