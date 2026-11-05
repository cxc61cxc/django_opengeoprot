from django.urls import path, re_path
from . import views
# from .views import home_residenti

app_name = 'anagrafe'


urlpatterns = [
    path('', views.home_residenti, name='home_residenti_url'), # elenco residenti
    path('anagrafe_edit/<int:id>/', views.ResidenteEditView, name='anagrafe_edit_url'),
    # path('residente_edit/<int:id>/',views.AddSoggettoAnagrafePraticaView,name='add_soggetto_anagrafe_pratica_url'), # cerca soggetto in anagrafe
]