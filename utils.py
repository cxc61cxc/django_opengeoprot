import folium

from accounts.permissions import (
    EDITOR_GROUPS,
    VIEWER_GROUPS,
    is_editor,
    is_user,
    editor_required,
    viewer_required,
)


WMS_CATASTO_URL = "https://wms.cartografia.agenziaentrate.gov.it/inspire/wms/ows01.php"


def build_base_map(lat, lng, zoom_start=15):
    """Crea una mappa folium con base OSM e layer WMS Catasto (Agenzia Entrate).

    Restituisce l'oggetto folium.Map già pronto per l'aggiunta di marker/GeoJson.
    Il boilerplate (TileLayer OSM + WmsTileLayer catasto + LayerControl) era
    duplicato in mappa_particelle, pratica_detail e pratica_edit.
    """
    mappa = folium.Map(location=[lat, lng], zoom_start=zoom_start, tiles=None)
    folium.TileLayer('openstreetmap', name='OpenStreetMap').add_to(mappa)
    folium.WmsTileLayer(
        url=WMS_CATASTO_URL,
        layers='province,comuni,fogli,particelle',
        name='Catasto (Agenzia delle Entrate)',
        fmt='image/png',
        transparent=True,
        attr='Sogei / Agenzia delle Entrate',
        overlay=False,
        control=True,
    ).add_to(mappa)
    folium.LayerControl().add_to(mappa)
    return mappa
