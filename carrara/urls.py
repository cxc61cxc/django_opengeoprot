"""carrara URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import TemplateView
from django.conf import settings
from django.conf.urls.static import static

from edilizia_compat import ARCHIVIO_AVAILABLE, EDILIZIA_AVAILABLE, GEST_EDILIZIA_AVAILABLE

urlpatterns = [
    # path('home/', include('home.urls')),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')), # new (PRIMA, contiene login custom)
    path('accounts/', include('django.contrib.auth.urls')), # new
    path('', include('home.urls')),
    path('mailer/', include('mailer.urls')), # new
    path('protocollo/', include('protocollo.urls')), # new
    path('anagrafe/', include('anagrafe.urls')), # new
    path('catasto/', include('catasto.urls')), # new
    path('prg/', include('prg.urls')), # new
    path('paesaggio/', include('paesaggio.urls')), # new
    path('comunicazioni/', include('comunicazioni.urls')), # new
    path('viario/', include('viario.urls')), # new
    path("select2/", include("django_select2.urls")),
    ###################################################
    #       SUAP
    ###################################################
    path("suap/", include("suap.urls")),
     ###################################################
    #       FOTOVOLTAICO
    ###################################################
    path("fotovoltaico/", include("fotovoltaico.urls", namespace="fotovoltaico")),
    ###################################################
    #       IDONEITA' ALLOGIATIVA
    ###################################################
    path("idonall/", include("idonall.urls")),
    ###################################################
    #       PASSO CARRAIO
    ###################################################
    path("pascar/", include("pascar.urls")),
    ###################################################
    #       COOPERATIVE (diritto di superficie)
    ###################################################
    path("coop/", include("coop.urls")),
    ###################################################
    #       ASCENSORI ( matricole )
    ###################################################
    path("ascensori/", include("ascensori.urls")),
     ###################################################
    #       omissis_documents
    ###################################################
    path("omissis/", include("omissis_documents.urls", namespace="omissis_documents")),
    ###################################################
    #       GRANDI LAVORI
    ###################################################
    path("grandi_lavori/", include("grandi_lavori.urls", namespace="grandi_lavori")),
    ###################################################
    #       PICCOLI LAVORI
    ###################################################
    path("piccoli_lavori/", include("piccoli_lavori.urls", namespace="piccoli_lavori")),
    ###################################################
    #       AUTORIZZAZIONI
    ###################################################
    path("autorizzazioni/", include("autorizzazioni.urls", namespace="autorizzazioni")),
    ###################################################
    #       LICENZE EDILIZIE
    ###################################################
    path("licenze_edilizie/", include("licenze_edilizie.urls", namespace="licenze_edilizie")),
    ###################################################
    #       osm_note - Strade senza operator
    ###################################################
    path("osm_note/", include("osm_note.urls")),
    path("highway/", include("highway.urls")),
    path("struttura_ente/", include("struttura_ente.urls", namespace="struttura_ente")),

    path('istruttoria_poc/', include('istruttoria_poc.urls', namespace='istruttoria_poc')),
] +static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# ---------------------------------------------------------------
# App opzionali dell'archivio storico (non pubblicate nel repo):
# le rotte vengono registrate solo se le app sono installate.
# ---------------------------------------------------------------
if ARCHIVIO_AVAILABLE:
    urlpatterns.append(path('archivi/', include('archivi.urls')))
if EDILIZIA_AVAILABLE:
    urlpatterns.append(path('edilizia/', include('edilizia.urls')))
if GEST_EDILIZIA_AVAILABLE:
    urlpatterns.append(path('gest_edilizia/', include('gest_edilizia.urls')))
