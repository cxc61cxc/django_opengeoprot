import json
import time

import requests
from django.contrib.gis.geos import LineString
from django.db import transaction

from .models import Highway


OVERPASS_URLS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)

OVERPASS_QUERY = """
[out:json][timeout:120];
area["name"="Carrara"]["admin_level"="8"]->.searchArea;
way["highway"]["operator"!="Comune di Carrara"](area.searchArea);
out body;
>;
out skel qt;
"""


def query_overpass():
    last_error = None
    for url in OVERPASS_URLS:
        try:
            response = requests.post(
                url,
                data={"data": OVERPASS_QUERY},
                headers={
                    "User-Agent": "django-opengeoprot/1.0 (Comune di Carrara)",
                },
                timeout=180,
            )
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict) or "elements" not in data:
                raise ValueError("Risposta Overpass non valida")
            return data
        except (requests.RequestException, ValueError) as error:
            last_error = error
            if getattr(error, "response", None) is not None and error.response.status_code == 429:
                time.sleep(3)
    raise RuntimeError("Importazione Overpass fallita") from last_error


def import_highways(data):
    nodes = {}
    ways = []
    for element in data.get("elements", []):
        element_type = element.get("type")
        if element_type == "node":
            nodes[element.get("id")] = (element.get("lat"), element.get("lon"))
        elif element_type == "way":
            ways.append(element)

    count = 0
    with transaction.atomic():
        Highway.objects.all().delete()
        for way in ways:
            osm_id = way.get("id")
            coordinates = []
            for node_id in way.get("nodes", []):
                node = nodes.get(node_id)
                if node and node[0] is not None and node[1] is not None:
                    coordinates.append([node[1], node[0]])
            if osm_id is None or len(coordinates) < 2:
                continue
            try:
                geometry = LineString(coordinates, srid=4326)
            except Exception:
                continue
            tags = way.get("tags") or {}
            Highway.objects.update_or_create(
                osm_id=osm_id,
                defaults={
                    "tipo": element_type,
                    "nome": str(tags.get("name", ""))[:255],
                    "highway": str(tags.get("highway", ""))[:100],
                    "attributi": tags,
                    "geom": geometry,
                    "modificato": str(tags.get("operator", "")) == "Comune di Carrara",
                },
            )
            count += 1
    return count
