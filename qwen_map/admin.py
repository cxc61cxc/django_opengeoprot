from django.contrib.gis import admin
from .models import Municipality

@admin.register(Municipality)
class MunicipalityAdmin(admin.GISModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)