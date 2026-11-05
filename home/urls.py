from django.urls import path, re_path
from . import views
from django.conf import settings
from django.conf.urls.static import static

app_name = 'home'

urlpatterns = [
    path('', views.index, name='index'), # pagina principale
    path('help/', views.help, name='help'), # manuale utente
    ]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)