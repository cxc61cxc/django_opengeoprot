from django.urls import path

from . import views

app_name = "highway"

urlpatterns = [
    path("", views.mappa_highway, name="mappa_highway"),
    path("api/highways/", views.highway_json, name="highway_json"),
    path("api/import/", views.import_highway, name="import_highway"),
    path("api/highways/<int:osm_id>/geometry/", views.salva_geometria, name="salva_geometria"),
]
