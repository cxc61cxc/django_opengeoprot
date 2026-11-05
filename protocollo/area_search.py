"""Logica di ricerca delle pratiche per area geografica disegnata sulla mappa.

Il modulo centralizza tre aspetti:

1. il parsing del GeoJSON dell'area disegnata (rettangolo o poligono),
   con normalizzazione in MultiPolygon SRID 4326;
2. le query spaziali che individuano le pratiche che intersecano l'area:
   - OPENGEOPROT -> protocollo.Pratica (geometria della pratica + punto);
   - ARCHIVIO    -> edilizia.Pratica, limitata alle pratiche che hanno
     almeno una particella collegata (edilizia.ParticellaUnivoca) che
     interseca l'area;
3. la costruzione del GeoJSON dei risultati, per evidenziarle sulla mappa.

I queryset di partenza vengono passati dal chiamante (protocollo/views.py) in
modo che il modulo non debba conoscere i permessi: chi chiama decide cosa è
visibile all'utente.
"""

import json
import logging

from django.contrib.gis.geos import GEOSGeometry, MultiPolygon
from django.db.models import F, Q

logger = logging.getLogger('user_actions')

# Numero massimo di risultati caricati nelle tabelle.
LIMITE_RISULTATI = 200

# Numero massimo di risultati proiettati sulla mappa.
LIMITE_MAPPA = 300

# Estensione geografica del Comune di Carrara: serve a riconoscere i GeoJSON
# inviati con longitudine/latitudine invertite (errore tipico quando la
# geometria viene costruita a mano e non da Leaflet).
LAT_MIN_RIF, LAT_MAX_RIF = 40.0, 45.5
LNG_MIN_RIF, LNG_MAX_RIF = 8.0, 12.0


def _geom_da_geojson(data):
    """Costruisce una GEOSGeometry da un dict GeoJSON (None se non valido)."""
    if not isinstance(data, dict) or not data.get('type'):
        return None
    try:
        return GEOSGeometry(json.dumps(data), srid=4326)
    except Exception:
        logger.warning('GeoJSON non valido ricevuto: %s', str(data)[:200])
        return None


def _swap_coords(coords):
    """Inverte le coppie di coordinate [lon, lat] -> [lat, lon]."""
    if isinstance(coords, (list, tuple)):
        if coords and isinstance(coords[0], (int, float)):
            return [coords[1], coords[0]]
        return [_swap_coords(c) for c in coords]
    return coords


def _coordinate_invertite(geom):
    """True se la geometria ha lon/lat scambiati (x in latitudine, y in longitudine)."""
    try:
        minx, miny, maxx, maxy = geom.extent
    except Exception:
        return False
    return (LAT_MIN_RIF <= minx <= LAT_MAX_RIF and maxx <= LAT_MAX_RIF and
            LNG_MIN_RIF <= miny <= LNG_MAX_RIF and maxy <= LNG_MAX_RIF)


def _inverti_coordinate(geom):
    """Restituisce la geometria con longitudine e latitudine scambiate."""
    try:
        gj = json.loads(geom.geojson)
        gj['coordinates'] = _swap_coords(gj['coordinates'])
        invertita = GEOSGeometry(json.dumps(gj), srid=4326)
        return invertita if invertita is not None else geom
    except Exception:
        logger.warning('Impossibile invertire le coordinate della geometria.')
        return geom


def _come_multi_polygon(geom):
    """Converte una geometria in MultiPolygon SRID 4326 (None se non valida)."""
    if geom is None or geom.empty:
        return None
    if geom.geom_type == 'Polygon':
        multi = MultiPolygon(geom)
    elif geom.geom_type == 'MultiPolygon':
        multi = geom
    else:
        return None
    # MultiPolygon() perde lo SRID: va ripristinato esplicitamente.
    multi.srid = 4326
    return multi


def _normalizza(geom):
    """Normalizza la geometria in una MultiPolygon SRID 4326 (None se unusable)."""
    if geom is None or geom.empty:
        return None
    if not geom.valid:
        try:
            geom = geom.buffer(0)
        except Exception:
            logger.warning('Geometria non valida e non riparabile.')
            return None
    if geom is None or geom.empty:
        return None

    if _coordinate_invertite(geom):
        geom = _inverti_coordinate(geom)

    multi = _come_multi_polygon(geom)
    if multi is not None:
        return multi

    # Punto o linea: non sono aree, ma per non perdere il risultato uso il
    # bounding box (con un minimo di dimensione per i punti).
    try:
        if geom.geom_type == 'Point':
            buffer = geom.buffer(0.00005)
            buffer.srid = 4326
            return _come_multi_polygon(buffer)
        env = geom.envelope
        if env.geom_type == 'Polygon':
            return _come_multi_polygon(env)
    except Exception:
        pass
    return None


def parse_area_geometry(geojson):
    """Converte il GeoJSON dell'area disegnata in una MultiPolygon SRID 4326.

    Accetta un dict GeoJSON (Polygon, MultiPolygon, Feature, FeatureCollection)
    oppure la sua serializzazione JSON; in caso di WKT viene usato come
    fallback. Restituisce None se la geometria non e' utilizzabile.
    """
    if not geojson:
        return None

    data = geojson
    if isinstance(data, (bytes, bytearray)):
        data = data.decode('utf-8', 'replace')

    if isinstance(data, str):
        testo = data.strip()
        if not testo:
            return None
        try:
            data = json.loads(testo)
        except ValueError:
            try:
                return _normalizza(GEOSGeometry(testo, srid=4326))
            except Exception:
                logger.warning('Area non valida: contenuto non JSON e non WKT.')
                return None

    if isinstance(data, dict):
        tipo = (data.get('type') or '').lower()
        if tipo == 'featurecollection':
            geometrie = []
            for feature in data.get('features') or []:
                if not isinstance(feature, dict):
                    continue
                geom = _geom_da_geojson(feature.get('geometry'))
                if geom is not None:
                    geometrie.append(geom)
            if not geometrie:
                return None
            unione = geometrie[0]
            for geom in geometrie[1:]:
                try:
                    unione = unione.union(geom)
                except Exception:
                    continue
            return _normalizza(unione)
        if tipo == 'feature':
            data = data.get('geometry') or {}
        return _normalizza(_geom_da_geojson(data))

    return None


def cerca_opengeoprot(qs_opengeoprot, geom, limite=LIMITE_RISULTATI):
    """Pratiche OPENGEOPROT che intersecano l'area.

    La ricerca considera sia la geometria della pratica (unione delle
    particelle catastali) sia il punto di posizionamento.
    """
    qs = qs_opengeoprot.filter(
        Q(mpoly_pratica__isnull=False, mpoly_pratica__intersects=geom) |
        Q(posizione__isnull=False, posizione__intersects=geom)
    ).distinct()
    totale = qs.order_by().count()
    pratiche = list(qs.order_by('-data_prot_gen', '-prot_gen')[:limite])
    return pratiche, totale


def cerca_archivio(qs_archivio, geom, limite=LIMITE_RISULTATI):
    """Pratiche ARCHIVIO (edilizia) legate a particelle che intersecano l'area.

    Il criterio e' la geometria delle particelle collegate alla pratica
    (ParticellaUnivoca): vengono cio' selezionate solo le pratiche che hanno
    almeno una particella che interseca l'area disegnata. La geometria
    denormalizzata mpoly_pratica non viene usata come filtro: contiene
    l'unione delle stesse particelle ed e' quindi ridondante (e in qualche
    caso non aggiornata).
    """
    qs = qs_archivio.prefetch_related('particelle_univoche').filter(
        particelle_univoche__mpoly__isnull=False,
        particelle_univoche__mpoly__intersects=geom,
    ).distinct()
    totale = qs.order_by().count()
    pratiche = list(
        qs.order_by(F('data_prot_gen').desc(nulls_last=True), '-id')[:limite]
    )
    return pratiche, totale


def cerca_pratiche_in_area(geom, qs_opengeoprot, qs_archivio,
                            limite=LIMITE_RISULTATI):
    """Esegue la ricerca completa per area.

    Restituisce un dict con:
      - pratiche / totale: pratiche OPENGEOPROT (lista e numero reale);
      - archivio / totale_archivio: pratiche ARCHIVIO.
    """
    pratiche, totale = cerca_opengeoprot(qs_opengeoprot, geom, limite)
    archivio, totale_archivio = cerca_archivio(qs_archivio, geom, limite)
    return {
        'pratiche': pratiche,
        'totale': totale,
        'archivio': archivio,
        'totale_archivio': totale_archivio,
    }


def _arrotonda(value, decimali=6):
    """Arrotonda i numeri di una struttura JSON (geometrie GeoJSON).

    Sei decimali corrispondono a circa 10 cm: precisione piu' che sufficiente
    per la rappresentazione a schermo e payload nettamente piu' leggero.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        return round(value, decimali)
    if isinstance(value, list):
        return [_arrotonda(v, decimali) for v in value]
    if isinstance(value, dict):
        return {k: _arrotonda(v, decimali) for k, v in value.items()}
    return value


def _geometria_pratica(pratica, fallback_posizione=False):
    """Geometria da usare per la pratica (per la mappa).

    Preferisce la geometria denormalizzata; se manca usa l'unione delle
    particelle collegate (disponibile solo se sono state prefetchate, per
    evitare una query per riga). Con fallback_posizione=True, in assenza di
    geometria viene usato il punto di posizionamento della pratica.
    """
    geom = getattr(pratica, 'mpoly_pratica', None)
    if geom is not None and not geom.empty:
        return geom

    prefetched = getattr(pratica, '_prefetched_objects_cache', None) or {}
    if 'particelle_univoche' in prefetched:
        unione = None
        for particella in prefetched['particelle_univoche']:
            g = getattr(particella, 'mpoly', None)
            if g is None or g.empty:
                continue
            try:
                unione = g if unione is None else unione.union(g)
            except Exception:
                continue
        if unione is not None:
            return unione

    if fallback_posizione:
        punto = getattr(pratica, 'posizione', None)
        if punto is not None and not punto.empty:
            return punto
    return None


def features_pratiche(pratiche, fonte, dettaglio_url, titolo=None,
                      limite=LIMITE_RISULTATI, fallback_posizione=False):
    """Costruisce le feature GeoJSON delle pratiche trovate.

    fonte: 'opengeoprot' oppure 'archivio'.
    dettaglio_url: callable che, data la pratica, restituisce l'URL di dettaglio.
    titolo: callable che, data la pratica, restituisce l'etichetta mostrata
            nel popup.
    """
    features = []
    for pratica in (pratiche or [])[:limite]:
        geom = _geometria_pratica(pratica, fallback_posizione)
        if geom is None or geom.empty:
            continue
        try:
            geometry = _arrotonda(json.loads(geom.geojson))
        except Exception:
            continue
        if not geometry:
            continue
        proprieta = {
            'id': pratica.pk,
            'fonte': fonte,
            'etichetta': (titolo(pratica) if titolo else str(pratica)),
        }
        try:
            proprieta['url'] = dettaglio_url(pratica)
        except Exception:
            proprieta['url'] = ''
        features.append({
            'type': 'Feature',
            'geometry': geometry,
            'properties': proprieta,
        })
    return features


def feature_collection(features):
    """Racchiude una lista di feature in una FeatureCollection GeoJSON."""
    return {'type': 'FeatureCollection', 'features': features or []}
