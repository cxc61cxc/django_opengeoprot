"""Test della logica di ricerca per area geografica (protocollo/area_search.py).

I test sono di tipo SimpleTestCase: non richiedono alcun accesso al database
e verificano la normalizzazione del GeoJSON dell'area disegnata.
"""

import json
from unittest import mock

from django.test import SimpleTestCase

from protocollo import area_search


def poligono(lon_min, lat_min, lon_max, lat_max):
    """Costruisce un GeoJSON Polygon (coordinate in [lon, lat])."""
    return {
        "type": "Polygon",
        "coordinates": [[
            [lon_min, lat_min],
            [lon_max, lat_min],
            [lon_max, lat_max],
            [lon_min, lat_max],
            [lon_min, lat_min],
        ]],
    }


class ParseAreaGeometryTest(SimpleTestCase):

    def test_poligono_standard(self):
        geom = area_search.parse_area_geometry(json.dumps(poligono(10.0, 44.0, 10.1, 44.1)))
        self.assertIsNotNone(geom)
        self.assertEqual(geom.geom_type, 'MultiPolygon')
        self.assertEqual(geom.srid, 4326)
        minx, miny, maxx, maxy = geom.extent
        self.assertAlmostEqual(minx, 10.0, places=6)
        self.assertAlmostEqual(miny, 44.0, places=6)
        self.assertAlmostEqual(maxx, 10.1, places=6)
        self.assertAlmostEqual(maxy, 44.1, places=6)

    def test_accetta_dict_geojson(self):
        geom = area_search.parse_area_geometry(poligono(10.0, 44.0, 10.1, 44.1))
        self.assertIsNotNone(geom)
        self.assertEqual(geom.geom_type, 'MultiPolygon')

    def test_accetta_feature(self):
        feat = {"type": "Feature", "properties": {}, "geometry": poligono(10.0, 44.0, 10.1, 44.1)}
        geom = area_search.parse_area_geometry(json.dumps(feat))
        self.assertIsNotNone(geom)
        self.assertEqual(geom.geom_type, 'MultiPolygon')

    def test_accetta_feature_collection(self):
        fc = {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "properties": {}, "geometry": poligono(10.0, 44.0, 10.1, 44.05)},
                {"type": "Feature", "properties": {}, "geometry": poligono(10.0, 44.05, 10.1, 44.1)},
            ],
        }
        geom = area_search.parse_area_geometry(json.dumps(fc))
        self.assertIsNotNone(geom)
        self.assertEqual(geom.geom_type, 'MultiPolygon')
        minx, miny, maxx, maxy = geom.extent
        self.assertAlmostEqual(miny, 44.0, places=6)
        self.assertAlmostEqual(maxy, 44.1, places=6)

    def test_accetta_multipolygon(self):
        multi = {"type": "MultiPolygon", "coordinates": [poligono(10.0, 44.0, 10.1, 44.1)['coordinates']]}
        geom = area_search.parse_area_geometry(json.dumps(multi))
        self.assertIsNotNone(geom)
        self.assertEqual(geom.geom_type, 'MultiPolygon')

    def test_coordinate_invertite_vengono_corrette(self):
        # lon/lat scambiate: la geometria deve essere riallineata a Carrara
        geom = area_search.parse_area_geometry(json.dumps(poligono(44.0, 10.0, 44.1, 10.1)))
        self.assertIsNotNone(geom)
        minx, miny, maxx, maxy = geom.extent
        self.assertAlmostEqual(minx, 10.0, places=6)
        self.assertAlmostEqual(miny, 44.0, places=6)
        self.assertAlmostEqual(maxx, 10.1, places=6)
        self.assertAlmostEqual(maxy, 44.1, places=6)

    def test_geojson_non_valido(self):
        self.assertIsNone(area_search.parse_area_geometry("questa non e' un geojson"))
        self.assertIsNone(area_search.parse_area_geometry(''))
        self.assertIsNone(area_search.parse_area_geometry(None))
        self.assertIsNone(area_search.parse_area_geometry('{"type": "Polygon"}'))

    def test_wkt_como_fallback(self):
        wkt = 'POLYGON((10.0 44.0, 10.1 44.0, 10.1 44.1, 10.0 44.1, 10.0 44.0))'
        geom = area_search.parse_area_geometry(wkt)
        self.assertIsNotNone(geom)
        self.assertEqual(geom.geom_type, 'MultiPolygon')

    def test_punto_viene_trasformato_in_area(self):
        geom = area_search.parse_area_geometry(json.dumps(
            {"type": "Point", "coordinates": [10.096, 44.077]}))
        self.assertIsNotNone(geom)
        self.assertEqual(geom.geom_type, 'MultiPolygon')
        self.assertFalse(geom.empty)
        self.assertEqual(geom.srid, 4326)


class FeatureCollectionTest(SimpleTestCase):

    def test_feature_collection_vuota(self):
        fc = area_search.feature_collection([])
        self.assertEqual(fc['type'], 'FeatureCollection')
        self.assertEqual(fc['features'], [])

    def test_feature_collection_con_elementi(self):
        features = [{'type': 'Feature', 'geometry': None, 'properties': {}}]
        fc = area_search.feature_collection(features)
        self.assertEqual(len(fc['features']), 1)


class CercaPraticheInAreaTest(SimpleTestCase):
    """La ricerca per area restituisce solo OPENGEOPROT e ARCHIVIO."""

    def test_ritorna_pratiche_e_archivio(self):
        geom = area_search.parse_area_geometry(json.dumps(poligono(10.0, 44.0, 10.1, 44.1)))
        with mock.patch.object(area_search, 'cerca_opengeoprot', return_value=(['p1'], 1)), \
                mock.patch.object(area_search, 'cerca_archivio', return_value=(['p2'], 2)):
            risultati = area_search.cerca_pratiche_in_area(geom, None, None)
        self.assertEqual(risultati['pratiche'], ['p1'])
        self.assertEqual(risultati['totale'], 1)
        self.assertEqual(risultati['archivio'], ['p2'])
        self.assertEqual(risultati['totale_archivio'], 2)

    def test_non_restituisce_particelle(self):
        geom = area_search.parse_area_geometry(json.dumps(poligono(10.0, 44.0, 10.1, 44.1)))
        with mock.patch.object(area_search, 'cerca_opengeoprot', return_value=([], 0)), \
                mock.patch.object(area_search, 'cerca_archivio', return_value=([], 0)):
            risultati = area_search.cerca_pratiche_in_area(geom, None, None)
        self.assertNotIn('particelle', risultati)
        self.assertNotIn('totale_particelle', risultati)

    def test_ricerca_particelle_non_esiste_piu(self):
        self.assertFalse(hasattr(area_search, 'cerca_particelle'))
