from django.contrib import admin
from django.contrib.gis import admin as gis_admin

from .models import Pratica, Documento, Particella, TipoPratica
from viario.models import Civici


class PraticaAdmin(admin.ModelAdmin):
    list_display = ['id', 'prot_gen', 'data_prot_gen', 'tipo_pratica']
    list_filter = ['street']

class CiviciAdmin(admin.ModelAdmin):
    list_display = ['nome']
    list_filter = ['nome']
    search_fields=['nome']

class ParticellaAdmin(gis_admin.GISModelAdmin):
    list_display = ['foglio', 'mappale']
    search_fields = ['foglio', 'mappale']

@admin.register(TipoPratica)
class TipoPraticaAdmin(admin.ModelAdmin):
    list_display = ['name', 'settore', 'servizio', 'u_o', 'visibile_solo_uo', 'id']
    list_filter = ['settore', 'visibile_solo_uo']
    search_fields = ['name', 'settore']
    autocomplete_fields = ('servizio', 'u_o', 'uo_visibili')

admin.site.register(Pratica, PraticaAdmin)
admin.site.register(Documento)
admin.site.register(Civici)
admin.site.register(Particella, ParticellaAdmin)
