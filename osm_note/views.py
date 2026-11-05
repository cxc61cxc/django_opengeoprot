import json
import time
import urllib.request
import urllib.parse

from django.contrib.auth.decorators import login_required
from django.contrib.gis.geos import LineString
from django.db.models import Exists, OuterRef
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .models import OsmStrada, StradaProcessata

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_FALLBACK_URL = "https://overpass.kumi.systems/api/interpreter"

OVERPASS_QUERY = """
[out:json][timeout:120];
area["name"="Carrara"]["admin_level"="8"]->.searchArea;
way["highway"]["name"]["operator"!="Comune di Carrara"](area.searchArea);
out body;
>;
out skel qt;
"""


@login_required
def mappa_strade(request):
    total = OsmStrada.objects.count()
    processed = StradaProcessata.objects.count()
    ctx = {
        'total_strade': total,
        'processed_count': processed,
        'pending': total - processed,
    }
    return render(request, 'osm_note/mappa_strade.html', ctx)


@login_required
def strade_json(request):
    processed_ids = set(StradaProcessata.objects.values_list('osm_id', flat=True))

    features = []
    for s in OsmStrada.objects.all():
        coords = list(s.geom.coords)
        is_processed = s.osm_id in processed_ids
        features.append({
            'type': 'Feature',
            'id': s.osm_id,
            'geometry': {
                'type': 'LineString',
                'coordinates': coords,
            },
            'properties': {
                'osm_id': s.osm_id,
                'name': s.nome,
                'highway': s.highway,
                'operator': s.operator,
                'processed': is_processed,
            },
        })

    return JsonResponse({
        'type': 'FeatureCollection',
        'features': features,
    })


@login_required
@require_POST
def importa_strade(request):
    try:
        data = _query_overpass()
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=502)

    elements = data.get('elements', [])
    nodes = {}
    ways = []

    for el in elements:
        if el.get('type') == 'node':
            nodes[el['id']] = (el.get('lat'), el.get('lon'))
        elif el.get('type') == 'way':
            ways.append(el)

    count = 0
    for way in ways:
        osm_id = way.get('id')
        tags = way.get('tags', {})
        coords = []
        for nid in way.get('nodes', []):
            if nid in nodes:
                coords.append([nodes[nid][1], nodes[nid][0]])

        if len(coords) < 2:
            continue

        line = LineString(coords, srid=4326)
        OsmStrada.objects.update_or_create(
            osm_id=osm_id,
            defaults={
                'nome': tags.get('name', '')[:255],
                'highway': tags.get('highway', '')[:50],
                'operator': tags.get('operator', '')[:255],
                'geom': line,
            }
        )
        count += 1

    return JsonResponse({'ok': True, 'count': count})


@login_required
@require_POST
def segna_processata(request):
    osm_id = request.POST.get('osm_id')
    nome = request.POST.get('nome', '')
    operator = request.POST.get('operator', '')

    if not osm_id:
        return JsonResponse({'ok': False, 'error': 'osm_id mancante'})

    try:
        osm_id = int(osm_id)
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'osm_id non valido'})

    if operator != '1':
        return JsonResponse({'ok': False, 'error': 'Conferma operator mancante'})

    obj, created = StradaProcessata.objects.get_or_create(
        osm_id=osm_id,
        defaults={
            'nome': nome[:255],
            'utente': request.user.username,
        }
    )

    return JsonResponse({
        'ok': True,
        'osm_id': osm_id,
        'created': created,
    })


def _query_overpass():
    payload = 'data=' + urllib.parse.quote(OVERPASS_QUERY)
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'django-opengeoprot/1.0 (Comune di Carrara)',
    }
    last_err = None
    for url in (OVERPASS_URL, OVERPASS_FALLBACK_URL):
        try:
            req = urllib.request.Request(
                url, data=payload.encode('utf-8'),
                headers=headers, method='POST',
            )
            with urllib.request.urlopen(req, timeout=180) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code == 429:
                time.sleep(3)
            continue
        except Exception as e:
            last_err = e
            continue
    raise last_err
