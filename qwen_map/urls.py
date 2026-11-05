from django.contrib import admin
from django.urls import path

from qwen_map.views import index, carrara_geojson, tile, search_particella

app_name = 'qwen_map'

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", index, name="index"),
    path("api/carrara.geojson", carrara_geojson, name="carrara-geojson"),
    path("api/search_particella/", search_particella, name="search-particella"),
    path("tiles/<int:z>/<int:x>/<int:y>.png", tile, name="tile"),
]

