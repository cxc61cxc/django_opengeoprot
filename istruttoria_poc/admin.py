from django.contrib import admin
from .models import Istruttoria, IstrComm, IstrCons


class IstruttoriaAdminBase(admin.ModelAdmin):
    list_display = ('pratica', 'data_val', 'user', 'data_crea', 'data_mod')
    list_filter = ('user',)
    search_fields = ('pratica__prot_gen', 'pratica__oggetto', 'testo')
    date_hierarchy = 'data_crea'
    raw_id_fields = ('pratica', 'user')
    readonly_fields = ('data_crea', 'data_mod')
    list_select_related = ('pratica', 'user')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('pratica', 'user')


@admin.register(Istruttoria)
class IstruttoriaAdmin(IstruttoriaAdminBase):
    list_filter = ('data_istr_poc', 'user')
    fields = ('pratica', 'testo', 'data_istr_poc', 'user', 'data_crea', 'data_mod')


@admin.register(IstrComm)
class IstrCommAdmin(IstruttoriaAdminBase):
    list_filter = ('data_commissione', 'user')
    fields = ('pratica', 'testo', 'data_commissione', 'user', 'data_crea', 'data_mod')


@admin.register(IstrCons)
class IstrConsAdmin(IstruttoriaAdminBase):
    list_filter = ('data_consiglio', 'user')
    fields = ('pratica', 'testo', 'data_consiglio', 'user', 'data_crea', 'data_mod')
