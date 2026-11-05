import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.gis.geos import GEOSGeometry
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST
from functools import wraps

from .importer import import_highways, query_overpass
from .models import Highway


def is_cartografia(user):
    return (
        user.is_authenticated
        and (
            user.is_superuser
            or user.is_staff
            or user.groups.filter(name="cartografia").exists()
        )
    )


def cartografia_required(function):
    @wraps(function)
    def wrapped(request, *args, **kwargs):
        if not is_cartografia(request.user):
            if request.path.startswith("/highway/api/"):
                return JsonResponse(
                    {"ok": False, "error": "Permessi di cartografia richiesti"},
                    status=403,
                )
            messages.error(
                request,
                "Accesso riservato agli utenti abilitati alla cartografia.",
            )
            return redirect("home:index")
        return function(request, *args, **kwargs)

    return wrapped


@login_required
def mappa_highway(request):
    return render(
        request,
        "highway/mappa_highway.html",
        {"can_edit": is_cartografia(request.user)},
    )


@login_required
@require_GET
def highway_json(request):
    q = request.GET.get("q", "").strip()
    mostra_modificati = request.GET.get("mostra_modificati") == "1"
    queryset = Highway.objects.all()
    if mostra_modificati:
        queryset = queryset.filter(modificato=True)
    else:
        queryset = queryset.filter(modificato=False)
    if q:
        # Rimuovi comuni prefissi stradali per ricerca più flessibile
        q_clean = q.lower()
        for prefix in ("via ", "viale ", "corso ", "piazza ", "largo ", "borgo ", "strada "):
            if q_clean.startswith(prefix):
                q_clean = q_clean[len(prefix):]
                break
        queryset = queryset.filter(
            Q(nome__icontains=q) | Q(nome__icontains=q_clean) | Q(highway__icontains=q)
        )
    else:
        queryset = queryset.exclude(nome__exact="").exclude(nome__isnull=True)
    queryset = queryset[:1000]

    features = []
    for highway in queryset:
        features.append(
            {
                "type": "Feature",
                "id": highway.osm_id,
                "geometry": json.loads(highway.geom.geojson),
                "properties": {
                    "osm_id": highway.osm_id,
                    "tipo": highway.tipo,
                    "name": highway.nome,
                    "highway": highway.highway,
                    "attributes": highway.attributi or {},
                    "imported_at": highway.data_importazione.isoformat(),
                    "modificato": highway.modificato,
                },
            }
        )

    return JsonResponse(
        {"type": "FeatureCollection", "features": features, "count": len(features)}
    )


@login_required
@require_POST
@cartografia_required
def import_highway(request):
    if not request.user.is_superuser:
        return JsonResponse({"ok": False, "error": "Permessi di admin richiesti"}, status=403)
    try:
        data = query_overpass()
        count = import_highways(data)
    except Exception as error:
        return JsonResponse({"ok": False, "error": str(error)}, status=502)
    return JsonResponse({"ok": True, "count": count})


@login_required
@require_POST
@cartografia_required
def salva_geometria(request, osm_id):
    highway = get_object_or_404(Highway, osm_id=osm_id)
    payload = request.POST.get("geometry") or request.body.decode("utf-8")
    try:
        geometry_data = json.loads(payload)
    except (TypeError, ValueError, UnicodeDecodeError):
        return JsonResponse(
            {"ok": False, "error": "Geometria GeoJSON non valida"}, status=400
        )

    if isinstance(geometry_data, dict) and geometry_data.get("type") == "Feature":
        geometry_data = geometry_data.get("geometry")
    if not isinstance(geometry_data, dict) or geometry_data.get("type") != "LineString":
        return JsonResponse(
            {"ok": False, "error": "Sono ammesse solo geometrie LineString"},
            status=400,
        )

    try:
        geometry = GEOSGeometry(json.dumps(geometry_data), srid=4326)
    except Exception:
        return JsonResponse(
            {"ok": False, "error": "Geometria non valida"}, status=400,
        )
    if geometry.geom_type != "LineString" or len(geometry.coords) < 2:
        return JsonResponse(
            {"ok": False, "error": "La geometria deve contenere almeno due vertici"},
            status=400,
        )

    highway.geom = geometry
    if "nome" in request.POST:
        highway.nome = request.POST.get("nome", "")[:255]
    if "highway" in request.POST:
        highway.highway = request.POST.get("highway", "")[:100]
    if "attributi" in request.POST:
        try:
            attributi = json.loads(request.POST.get("attributi", "{}"))
        except (TypeError, ValueError):
            return JsonResponse(
                {"ok": False, "error": "Attributi JSON non validi"}, status=400
            )
        if not isinstance(attributi, dict):
            return JsonResponse(
                {"ok": False, "error": "Gli attributi devono essere un oggetto JSON"},
                status=400,
            )
        highway.attributi = attributi
        highway.modificato = attributi.get("operator") == "Comune di Carrara"
    highway.save()

    return JsonResponse(
        {
            "ok": True,
            "osm_id": highway.osm_id,
            "geometry": json.loads(highway.geom.geojson),
        }
    )
