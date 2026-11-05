from django.contrib import admin

from .models import Highway


@admin.register(Highway)
class HighwayAdmin(admin.ModelAdmin):
    list_display = ("osm_id", "tipo", "nome", "highway", "data_importazione")
    list_filter = ("tipo", "highway")
    search_fields = ("osm_id", "nome", "attributi")
