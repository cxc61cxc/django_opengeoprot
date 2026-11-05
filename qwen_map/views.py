import json
import os

from django.conf import settings
from django.core.serializers import serialize
from django.http import HttpResponse, Http404, FileResponse, JsonResponse
from django.shortcuts import render
from django.db.models import Q
from django.db import connections

from .models import Municipality


def index(request):
    return render(request, "qwen_map/index.html")


def carrara_geojson(request):
    qs = Municipality.objects.filter(name__iexact="Carrara")
    geojson = serialize("geojson", qs, geometry_field="geom")
    return HttpResponse(geojson, content_type="application/geo+json")


def search_particella(request):
    foglio = request.GET.get("foglio", "").strip()
    mappale = request.GET.get("mappale", "").strip()
    if not foglio or not mappale:
        return JsonResponse({"error": "Foglio e mappale sono obbligatori."}, status=400)

    try:
        with connections['anagrafe_civica'].cursor() as cursor:
            cursor.execute(
                """
                SELECT json_build_object(
                    'type', 'Feature',
                    'id', id,
                    'properties', json_build_object(
                        'id', id,
                        'foglio', foglio,
                        'mappale', mappale
                    ),
                    'geometry', ST_AsGeoJSON(geom)::json
                ) AS geojson
                FROM cxf_in.vw_particelle_4326
                WHERE foglio LIKE %s AND mappale ILIKE %s
                LIMIT 1
                """,
                [f"%%{foglio}", mappale],
            )
            row = cursor.fetchone()

        if not row:
            return JsonResponse({"error": "Nessuna particella trovata."}, status=404)

        geojson = json.dumps(row[0])
        return JsonResponse({"geojson": geojson})
    except Exception as e:
        return JsonResponse({"error": "Errore durante la ricerca: " + str(e)}, status=500)


def tile(request, z, x, y):
    """
    Serve le tile locali da:
    /home/cxc/django/django_opengeoprot/static/tiles/{z}/{x}/{y}.png
    """
    tile_path = os.path.abspath(
        os.path.join(
            settings.TILES_DIR,
            str(z),
            str(x),
            f"{y}.png",
        )
    )
    # AGGIUNGI QUESTA RIGA:
    print(f"🔍 DEBUG TILE: Sto cercando -> {tile_path}")
    tiles_root = os.path.abspath(settings.TILES_DIR)

    if not tile_path.startswith(tiles_root):
        raise Http404("Tile non valida")

    if not os.path.isfile(tile_path):
        # AGGIUNGI ANCHE QUESTO PER CAPIRE SE IL FILE ESISTE:
        print(f"❌ ERRORE: Il file non esiste sul disco!")
        raise Http404("Tile non trovata")

    return FileResponse(
        open(tile_path, "rb"),
        content_type="image/png",
    )