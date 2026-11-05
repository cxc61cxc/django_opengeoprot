import json
from pathlib import Path

import requests

from django.core.management.base import BaseCommand
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon

from qwen_map.models import Municipality


class Command(BaseCommand):
    help = "Importa il perimetro comunale di Carrara in PostGIS."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            help="Percorso di un file GeoJSON locale da importare.",
        )

    def extract_geometry(self, obj):
        """
        Accetta:
        - FeatureCollection
        - Feature
        - Geometry
        e restituisce la geometria GeoJSON.
        """
        obj_type = obj.get("type")

        if obj_type == "FeatureCollection":
            features = obj.get("features", [])
            if not features:
                raise ValueError("Il GeoJSON non contiene features.")
            return features[0].get("geometry")

        if obj_type == "Feature":
            return obj.get("geometry")

        return obj

    def handle(self, *args, **options):
        file_path = options.get("file")

        if file_path:
            raw = Path(file_path).read_text(encoding="utf-8")
            data = json.loads(raw)
            geometry_dict = self.extract_geometry(data)
        else:
            self.stdout.write("Download del perimetro da Nominatim/OpenStreetMap...")

            url = "https://nominatim.openstreetmap.org/search"

            params = {
                "q": "Carrara, Toscana, Italia",
                "format": "jsonv2",
                "polygon_geojson": "1",
                "limit": "1",
            }

            headers = {
                "User-Agent": "django-opengeoprot-carrara-demo/0.1 (local-dev)"
            }

            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()

            results = response.json()

            if not results:
                raise ValueError("Nessun risultato trovato per Carrara.")

            geometry_dict = results[0].get("geojson")

        if not geometry_dict:
            raise ValueError("Nessuna geometria trovata.")

        geometry = GEOSGeometry(json.dumps(geometry_dict), srid=4326)

        if geometry.geom_type == "Polygon":
            geometry = MultiPolygon(geometry)
        elif geometry.geom_type != "MultiPolygon":
            raise ValueError(
                f"Tipo di geometria non supportato: {geometry.geom_type}. "
                "Attesi Polygon o MultiPolygon."
            )

        municipality, created = Municipality.objects.update_or_create(
            name="Carrara",
            defaults={
                "geom": geometry,
            },
        )

        action = "creato" if created else "aggiornato"
        self.stdout.write(
            self.style.SUCCESS(
                f"Comune di Carrara {action} correttamente nel database."
            )
        )