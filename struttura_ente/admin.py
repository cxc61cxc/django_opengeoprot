from django.contrib import admin
from django.utils import timezone
from .models import (
    Settore, Servizio, AttivitaUO, TipoCommissione,
    StoricoSettore, StoricoServizio, StoricoAttivitaUO,
)
from accounts.models import Commissione


class ServizioInline(admin.TabularInline):
    model = Servizio
    extra = 1
    fields = ('codice', 'nome', 'descrizione', 'ordine', 'attivo')


class CommissioneInline(admin.TabularInline):
    model = TipoCommissione.settori.through
    extra = 0
    verbose_name = 'Commissione collegata'
    verbose_name_plural = 'Commissioni collegate'
    autocomplete_fields = ('tipocommissione',)


class IscrittiCommissioneInline(admin.TabularInline):
    """Inline per gestire le iscrizioni (accounts.Commissione) di una commissione
    direttamente dalla sua scheda in admin."""
    model = Commissione
    extra = 0
    autocomplete_fields = ('user',)
    raw_id_fields = ('user',)
    fields = ('user', 'settore', 'data_inizio', 'data_fine', 'note')
    readonly_fields = ('data_inizio',)


class AttivitaInline(admin.TabularInline):
    model = AttivitaUO
    extra = 1
    fields = ('nome', 'descrizione', 'ordine', 'attivo')


class StoricoSettoreInline(admin.TabularInline):
    model = StoricoSettore
    extra = 0
    can_delete = False
    readonly_fields = ('codice', 'nome', 'descrizione', 'ordine', 'atto_riferimento', 'data_inizio', 'data_fine')
    fields = readonly_fields
    max_num = 20


class StoricoServizioInline(admin.TabularInline):
    model = StoricoServizio
    extra = 0
    can_delete = False
    readonly_fields = ('settore_storico', 'codice', 'nome', 'descrizione', 'ordine', 'atto_riferimento', 'data_inizio', 'data_fine')
    fields = readonly_fields
    max_num = 20


class StoricoAttivitaInline(admin.TabularInline):
    model = StoricoAttivitaUO
    extra = 0
    can_delete = False
    readonly_fields = ('servizio_storico', 'nome', 'descrizione', 'ordine', 'atto_riferimento', 'data_inizio', 'data_fine')
    fields = readonly_fields
    max_num = 20


@admin.register(Settore)
class SettoreAdmin(admin.ModelAdmin):
    list_display = ('codice', 'nome', 'ordine', 'attivo', 'data_modifica')
    list_editable = ('nome', 'ordine', 'attivo')
    search_fields = ('codice', 'nome')
    inlines = [ServizioInline, StoricoSettoreInline, CommissioneInline]


@admin.register(Servizio)
class ServizioAdmin(admin.ModelAdmin):
    list_display = ('codice', 'nome', 'settore', 'ordine', 'attivo', 'data_modifica')
    list_editable = ('nome', 'ordine', 'attivo')
    list_filter = ('settore',)
    search_fields = ('codice', 'nome', 'settore__codice', 'settore__nome')
    inlines = [AttivitaInline, StoricoServizioInline]


@admin.register(AttivitaUO)
class AttivitaUOAdmin(admin.ModelAdmin):
    list_display = ('nome', 'servizio', 'ordine', 'attivo', 'data_modifica')
    list_filter = ('servizio__settore', 'servizio')
    search_fields = ('nome', 'servizio__codice', 'servizio__nome')
    inlines = [StoricoAttivitaInline]


@admin.register(StoricoSettore)
class StoricoSettoreAdmin(admin.ModelAdmin):
    list_display = ('codice', 'nome', 'data_inizio', 'data_fine', 'atto_riferimento')
    list_filter = ('codice',)
    search_fields = ('codice', 'nome', 'atto_riferimento')
    readonly_fields = ('settore', 'codice', 'nome', 'descrizione', 'ordine', 'atto_riferimento', 'data_inizio', 'data_fine')


@admin.register(StoricoServizio)
class StoricoServizioAdmin(admin.ModelAdmin):
    list_display = ('codice', 'nome', 'settore_storico', 'data_inizio', 'data_fine', 'atto_riferimento')
    list_filter = ('settore_storico__codice',)
    search_fields = ('codice', 'nome', 'atto_riferimento')
    readonly_fields = ('servizio', 'settore_storico', 'codice', 'nome', 'descrizione', 'ordine', 'atto_riferimento', 'data_inizio', 'data_fine')


@admin.register(StoricoAttivitaUO)
class StoricoAttivitaUOAdmin(admin.ModelAdmin):
    list_display = ('nome', 'servizio_storico', 'data_inizio', 'data_fine', 'atto_riferimento')
    list_filter = ('servizio_storico__settore_storico__codice',)
    search_fields = ('nome', 'servizio_storico__codice', 'atto_riferimento')
    readonly_fields = ('attivita', 'servizio_storico', 'nome', 'descrizione', 'ordine', 'atto_riferimento', 'data_inizio', 'data_fine')


@admin.register(TipoCommissione)
class TipoCommissioneAdmin(admin.ModelAdmin):
    list_display = ('codice', 'nome', 'gruppo_django', 'ordine', 'attivo', 'data_modifica', 'n_iscritti')
    list_editable = ('nome', 'gruppo_django', 'ordine', 'attivo')
    list_filter = ('attivo', 'settori')
    search_fields = ('codice', 'nome', 'gruppo_django', 'settori__codice', 'settori__nome')
    filter_horizontal = ('settori',)
    inlines = [IscrittiCommissioneInline]
    actions = ['disattiva_commissioni', 'attiva_commissioni']

    def n_iscritti(self, obj):
        return obj.iscritti.count()
    n_iscritti.short_description = 'Consiglieri iscritti'
    n_iscritti.admin_order_field = 'iscritti__count'

    @admin.action(description='Disattiva le commissioni selezionate')
    def disattiva_commissioni(self, request, queryset):
        updated = queryset.update(attivo=False)
        self.message_user(request, f'{updated} commissione/i disattivata/e.')

    @admin.action(description='Attiva le commissioni selezionate')
    def attiva_commissioni(self, request, queryset):
        updated = queryset.update(attivo=True)
        self.message_user(request, f'{updated} commissione/i attivata/e.')


@admin.register(Commissione)
class CommissioneAdmin(admin.ModelAdmin):
    list_display = ('user', 'tipo_commissione', 'settore', 'data_inizio', 'data_fine', 'attiva')
    list_filter = ('tipo_commissione', 'settore', 'data_fine')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'tipo_commissione__codice', 'tipo_commissione__nome')
    autocomplete_fields = ('user', 'tipo_commissione')
    raw_id_fields = ('user',)
    date_hierarchy = 'data_inizio'
    actions = ['termina_iscrizione', 'riapri_iscrizione']

    def attiva(self, obj):
        return obj.attiva
    attiva.boolean = True

    @admin.action(description='Termina iscrizione (imposta data_fine=oggi)')
    def termina_iscrizione(self, request, queryset):
        updated = queryset.update(data_fine=timezone.now().date())
        self.message_user(request, f'{updated} iscrizione/i terminata/e.')

    @admin.action(description='Riapri iscrizione (data_fine=None)')
    def riapri_iscrizione(self, request, queryset):
        updated = queryset.update(data_fine=None)
        self.message_user(request, f'{updated} iscrizione/i riaperta/e.')