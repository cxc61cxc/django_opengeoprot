import folium

import logging

logger_user_actions = logging.getLogger('user_actions')


def log_action(request, action, obj_repr=None, extra=None):
    """Logga un'azione CRUD dell'utente su user_actions.log.

    Esempi:
        log_action(request, 'CREA', f'Pratica {obj.id}', {'prot_gen': obj.prot_gen})
        log_action(request, 'EDITA', f'Pratica {obj.id}')
        log_action(request, 'ELIMINA', f'Pratica {obj.id}')
        log_action(request, 'VISUALIZZA', f'Pratica {obj.id}')
    """
    user = request.user if request.user.is_authenticated else None
    username = user.username if user else 'Anonimo'
    message = f"Utente: {username} ha {action}"
    if obj_repr:
        message += f" {obj_repr}"
    if extra:
        extra_str = ' | '.join(f"{k}: {v}" for k, v in extra.items())
        message += f" | {extra_str}"
    logger_user_actions.info(message)


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
