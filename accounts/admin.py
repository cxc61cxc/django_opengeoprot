from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Profile, Commissione


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    fk_name = 'user'
    fields = ('settore', 'u_o', 'profile_picture')
    autocomplete_fields = ('settore', 'u_o')


class CommissioneInline(admin.TabularInline):
    model = Commissione
    extra = 0
    autocomplete_fields = ('tipo_commissione',)
    raw_id_fields = ('user',)
    fields = ('tipo_commissione', 'settore', 'data_inizio', 'data_fine', 'note')
    readonly_fields = ('data_inizio',)


class CustomUserAdmin(UserAdmin):
    inlines = [ProfileInline, CommissioneInline]
    list_display = UserAdmin.list_display + ('get_commissioni',)

    def get_commissioni(self, obj):
        return ', '.join(
            c.tipo_commissione.codice for c in obj.commissioni.filter(tipo_commissione__attivo=True)
        ) or '—'
    get_commissioni.short_description = 'Commissioni attive'


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'settore', 'u_o')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    autocomplete_fields = ('settore', 'u_o')
    raw_id_fields = ('user',)
